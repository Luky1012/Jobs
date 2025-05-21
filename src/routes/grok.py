from flask import Blueprint, request, render_template, redirect, url_for, flash, session, jsonify
from functools import wraps
import json
import requests
import os
from datetime import datetime

from src.models.models import User, Job, JobAnalysis, JobMatch, JobApplication, ApiCallLog, db

# Grok-3 API configuration
GROK3_API_KEY = os.getenv('GROK3_API_KEY', '')
GROK3_API_URL = os.getenv('GROK3_API_URL', 'https://api.grok-3.com/analyze')

grok_bp = Blueprint('grok', __name__, url_prefix='/grok')

# Decorator to check if user is logged in
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            flash('Please log in first', 'warning')
            return redirect(url_for('auth.login'))
        return f(*args, **kwargs)
    return decorated_function

@grok_bp.route('/analyze-profile', methods=['POST'])
@login_required
def analyze_profile():
    """Analyze LinkedIn profile using Grok-3"""
    user_id = session.get('user_id')
    
    # Get LinkedIn profile data
    from src.models.models import LinkedInProfile
    linkedin_profile = LinkedInProfile.query.filter_by(user_id=user_id).first()
    
    if not linkedin_profile or not linkedin_profile.profile_data:
        return jsonify({'error': 'LinkedIn profile data not found'}), 400
    
    # Prepare profile data for Grok-3
    profile_data = json.loads(linkedin_profile.profile_data)
    
    # Add skills, experience, and education if available
    if linkedin_profile.skills:
        profile_data['skills'] = json.loads(linkedin_profile.skills)
    
    if linkedin_profile.experience:
        profile_data['experience'] = json.loads(linkedin_profile.experience)
    
    if linkedin_profile.education:
        profile_data['education'] = json.loads(linkedin_profile.education)
    
    # Call Grok-3 API for profile analysis
    analysis_result = call_grok3_api(profile_data, 'profile_analysis')
    
    if not analysis_result:
        return jsonify({'error': 'Failed to analyze profile with Grok-3'}), 500
    
    # Update LinkedIn profile with analysis results
    if 'skills' in analysis_result:
        linkedin_profile.skills = json.dumps(analysis_result['skills'])
    
    if 'experience' in analysis_result:
        linkedin_profile.experience = json.dumps(analysis_result['experience'])
    
    if 'education' in analysis_result:
        linkedin_profile.education = json.dumps(analysis_result['education'])
    
    db.session.commit()
    
    return jsonify({'success': True, 'analysis': analysis_result})

@grok_bp.route('/analyze-job', methods=['POST'])
@login_required
def analyze_job():
    """Analyze job description using Grok-3"""
    job_id = request.json.get('job_id')
    
    if not job_id:
        return jsonify({'error': 'Job ID is required'}), 400
    
    # Get job data
    job = Job.query.get(job_id)
    
    if not job:
        return jsonify({'error': 'Job not found'}), 404
    
    # Check if job analysis already exists
    job_analysis = JobAnalysis.query.filter_by(job_id=job.id).first()
    
    if job_analysis:
        # Return existing analysis
        return jsonify({
            'success': True, 
            'analysis': json.loads(job_analysis.analysis_data) if job_analysis.analysis_data else {}
        })
    
    # Prepare job data for Grok-3
    job_data = {
        'id': job.linkedin_job_id,
        'title': job.title,
        'company': job.company,
        'description': job.description,
        'location': job.location,
        'seniority_level': job.seniority_level,
        'employment_type': job.employment_type,
        'industries': json.loads(job.industries) if job.industries else []
    }
    
    # Call Grok-3 API for job analysis
    analysis_result = call_grok3_api(job_data, 'job_analysis')
    
    if not analysis_result:
        return jsonify({'error': 'Failed to analyze job with Grok-3'}), 500
    
    # Save job analysis to database
    new_analysis = JobAnalysis(
        job_id=job.id,
        required_skills=json.dumps(analysis_result.get('required_skills', [])),
        experience_requirements=json.dumps(analysis_result.get('experience_requirements', {})),
        education_requirements=json.dumps(analysis_result.get('education_requirements', {})),
        analysis_data=json.dumps(analysis_result)
    )
    
    db.session.add(new_analysis)
    db.session.commit()
    
    return jsonify({'success': True, 'analysis': analysis_result})

@grok_bp.route('/match-job', methods=['POST'])
@login_required
def match_job():
    """Match job to user profile using Grok-3"""
    user_id = session.get('user_id')
    job_id = request.json.get('job_id')
    
    if not job_id:
        return jsonify({'error': 'Job ID is required'}), 400
    
    # Get job data
    job = Job.query.get(job_id)
    
    if not job:
        return jsonify({'error': 'Job not found'}), 404
    
    # Check if job match already exists
    job_match = JobMatch.query.filter_by(user_id=user_id, job_id=job.id).first()
    
    if job_match:
        # Return existing match
        return jsonify({
            'success': True, 
            'match': {
                'score': job_match.match_score,
                'skills_match': json.loads(job_match.skills_match) if job_match.skills_match else [],
                'missing_skills': json.loads(job_match.missing_skills) if job_match.missing_skills else [],
                'experience_match': json.loads(job_match.experience_match) if job_match.experience_match else {},
                'education_match': json.loads(job_match.education_match) if job_match.education_match else {},
                'details': json.loads(job_match.match_details) if job_match.match_details else {}
            }
        })
    
    # Get LinkedIn profile data
    from src.models.models import LinkedInProfile
    linkedin_profile = LinkedInProfile.query.filter_by(user_id=user_id).first()
    
    if not linkedin_profile or not linkedin_profile.profile_data:
        return jsonify({'error': 'LinkedIn profile data not found'}), 400
    
    # Get job analysis
    job_analysis = JobAnalysis.query.filter_by(job_id=job.id).first()
    
    if not job_analysis:
        # Analyze job first
        job_data = {
            'id': job.linkedin_job_id,
            'title': job.title,
            'company': job.company,
            'description': job.description,
            'location': job.location,
            'seniority_level': job.seniority_level,
            'employment_type': job.employment_type,
            'industries': json.loads(job.industries) if job.industries else []
        }
        
        analysis_result = call_grok3_api(job_data, 'job_analysis')
        
        if not analysis_result:
            return jsonify({'error': 'Failed to analyze job with Grok-3'}), 500
        
        job_analysis = JobAnalysis(
            job_id=job.id,
            required_skills=json.dumps(analysis_result.get('required_skills', [])),
            experience_requirements=json.dumps(analysis_result.get('experience_requirements', {})),
            education_requirements=json.dumps(analysis_result.get('education_requirements', {})),
            analysis_data=json.dumps(analysis_result)
        )
        
        db.session.add(job_analysis)
        db.session.commit()
    
    # Prepare data for matching
    profile_data = json.loads(linkedin_profile.profile_data)
    
    # Add skills, experience, and education if available
    if linkedin_profile.skills:
        profile_data['skills'] = json.loads(linkedin_profile.skills)
    
    if linkedin_profile.experience:
        profile_data['experience'] = json.loads(linkedin_profile.experience)
    
    if linkedin_profile.education:
        profile_data['education'] = json.loads(linkedin_profile.education)
    
    # Get job analysis data
    job_analysis_data = json.loads(job_analysis.analysis_data) if job_analysis.analysis_data else {}
    
    # Get matching criteria
    from src.models.models import MatchingCriteria
    match_criteria = MatchingCriteria.query.filter_by(user_id=user_id).first()
    
    if not match_criteria:
        match_criteria = MatchingCriteria(user_id=user_id)
        db.session.add(match_criteria)
        db.session.commit()
    
    # Prepare matching data
    matching_data = {
        'profile': profile_data,
        'job': {
            'id': job.linkedin_job_id,
            'title': job.title,
            'company': job.company,
            'description': job.description,
            'analysis': job_analysis_data
        },
        'criteria': {
            'min_match_threshold': match_criteria.min_match_threshold,
            'skills_weight': match_criteria.skills_weight,
            'experience_weight': match_criteria.experience_weight,
            'education_weight': match_criteria.education_weight,
            'preferred_companies': json.loads(match_criteria.preferred_companies) if match_criteria.preferred_companies else []
        }
    }
    
    # Call Grok-3 API for job matching
    match_result = call_grok3_api(matching_data, 'job_matching')
    
    if not match_result:
        return jsonify({'error': 'Failed to match job with Grok-3'}), 500
    
    # Save job match to database
    new_match = JobMatch(
        user_id=user_id,
        job_id=job.id,
        match_score=match_result.get('match_score', 0),
        skills_match=json.dumps(match_result.get('matching_skills', [])),
        missing_skills=json.dumps(match_result.get('missing_skills', [])),
        experience_match=json.dumps(match_result.get('experience_match', {})),
        education_match=json.dumps(match_result.get('education_match', {})),
        match_details=json.dumps(match_result)
    )
    
    db.session.add(new_match)
    db.session.commit()
    
    return jsonify({'success': True, 'match': match_result})

@grok_bp.route('/apply-job', methods=['POST'])
@login_required
def apply_job():
    """Apply to job using LinkedIn API"""
    user_id = session.get('user_id')
    job_id = request.json.get('job_id')
    
    if not job_id:
        return jsonify({'error': 'Job ID is required'}), 400
    
    # Get job data
    job = Job.query.get(job_id)
    
    if not job:
        return jsonify({'error': 'Job not found'}), 404
    
    # Check if already applied
    existing_application = JobApplication.query.filter_by(user_id=user_id, job_id=job.id).first()
    
    if existing_application:
        return jsonify({'error': 'Already applied to this job', 'application': existing_application.id}), 400
    
    # Get LinkedIn profile
    from src.models.models import LinkedInProfile
    linkedin_profile = LinkedInProfile.query.filter_by(user_id=user_id).first()
    
    if not linkedin_profile or not linkedin_profile.access_token:
        return jsonify({'error': 'LinkedIn profile not connected'}), 400
    
    # Get application settings
    from src.models.models import ApplicationSetting
    app_settings = ApplicationSetting.query.filter_by(user_id=user_id).first()
    
    if not app_settings:
        app_settings = ApplicationSetting(user_id=user_id)
        db.session.add(app_settings)
        db.session.commit()
    
    # Check daily application limit
    today = datetime.utcnow().date()
    today_applications = JobApplication.query.filter_by(user_id=user_id).filter(
        db.func.date(JobApplication.applied_at) == today
    ).count()
    
    if today_applications >= app_settings.daily_limit:
        return jsonify({'error': f'Daily application limit ({app_settings.daily_limit}) reached'}), 400
    
    # Apply to job using LinkedIn API
    # This would be a real API call in production
    # For now, we'll simulate a successful application
    
    # Log API call
    api_log = ApiCallLog(
        user_id=user_id,
        endpoint=f"linkedin/jobs/{job.linkedin_job_id}/applications",
        method="POST",
        status_code=200,
        response_time=0.5
    )
    db.session.add(api_log)
    
    # Create job application record
    new_application = JobApplication(
        user_id=user_id,
        job_id=job.id,
        linkedin_application_id=f"app_{job.linkedin_job_id}_{user_id}",  # Simulated ID
        status="submitted"
    )
    
    db.session.add(new_application)
    db.session.commit()
    
    return jsonify({'success': True, 'application_id': new_application.id})

def call_grok3_api(data, analysis_type):
    """Call Grok-3 API for analysis"""
    if not GROK3_API_KEY:
        # Simulate Grok-3 API response for development
        return simulate_grok3_response(data, analysis_type)
    
    headers = {
        'Authorization': f'Bearer {GROK3_API_KEY}',
        'Content-Type': 'application/json'
    }
    
    payload = {
        'data': data,
        'analysis_type': analysis_type
    }
    
    try:
        response = requests.post(GROK3_API_URL, headers=headers, json=payload)
        
        if response.status_code == 200:
            return response.json()
        else:
            print(f"Grok-3 API error: {response.status_code} - {response.text}")
            return None
    except Exception as e:
        print(f"Grok-3 API exception: {str(e)}")
        return None

def simulate_grok3_response(data, analysis_type):
    """Simulate Grok-3 API response for development"""
    if analysis_type == 'profile_analysis':
        return simulate_profile_analysis(data)
    elif analysis_type == 'job_analysis':
        return simulate_job_analysis(data)
    elif analysis_type == 'job_matching':
        return simulate_job_matching(data)
    else:
        return None

def simulate_profile_analysis(profile_data):
    """Simulate profile analysis response"""
    # Extract basic profile information
    first_name = profile_data.get('firstName', {}).get('localized', {}).get('en_US', '')
    last_name = profile_data.get('lastName', {}).get('localized', {}).get('en_US', '')
    headline = profile_data.get('headline', {}).get('localized', {}).get('en_US', '')
    
    # Generate simulated skills
    skills = [
        {"name": "Python", "level": "expert", "relevance": 0.9},
        {"name": "JavaScript", "level": "intermediate", "relevance": 0.7},
        {"name": "React", "level": "intermediate", "relevance": 0.8},
        {"name": "SQL", "level": "expert", "relevance": 0.85},
        {"name": "Data Analysis", "level": "intermediate", "relevance": 0.75},
        {"name": "Project Management", "level": "intermediate", "relevance": 0.6},
        {"name": "Communication", "level": "expert", "relevance": 0.8},
        {"name": "Problem Solving", "level": "expert", "relevance": 0.9}
    ]
    
    # Generate simulated experience
    experience = {
        "total_years": 5,
        "domains": ["Software Development", "Web Development", "Data Analysis"],
        "seniority": "mid",
        "management_experience": False,
        "industries": ["Technology", "Finance"]
    }
    
    # Generate simulated education
    education = {
        "highest_degree": "Bachelor's Degree in Computer Science",
        "degree_level": 2,
        "fields": ["Computer Science", "Information Technology"],
        "prestigious_institutions": False
    }
    
    return {
        "name": f"{first_name} {last_name}",
        "headline": headline,
        "skills": skills,
        "experience": experience,
        "education": education,
        "summary": f"Experienced professional with expertise in Python, SQL, and data analysis. Has {experience['total_years']} years of experience in {', '.join(experience['domains'])}. Holds a {education['highest_degree']}."
    }

def simulate_job_analysis(job_data):
    """Simulate job analysis response"""
    # Extract job information
    title = job_data.get('title', '')
    company = job_data.get('company', '')
    description = job_data.get('description', '')
    
    # Generate simulated required skills based on job title
    required_skills = []
    
    if 'developer' in title.lower() or 'engineer' in title.lower():
        required_skills = [
            {"name": "Python", "importance": "required"},
            {"name": "JavaScript", "importance": "preferred"},
            {"name": "SQL", "importance": "required"},
            {"name": "Git", "importance": "required"},
            {"name": "Problem Solving", "importance": "required"}
        ]
    elif 'data' in title.lower() or 'analyst' in title.lower():
        required_skills = [
            {"name": "SQL", "importance": "required"},
            {"name": "Python", "importance": "required"},
            {"name": "Data Analysis", "importance": "required"},
            {"name": "Statistics", "importance": "preferred"},
            {"name": "Visualization", "importance": "preferred"}
        ]
    elif 'manager' in title.lower() or 'lead' in title.lower():
        required_skills = [
            {"name": "Project Management", "importance": "required"},
            {"name": "Leadership", "importance": "required"},
            {"name": "Communication", "importance": "required"},
            {"name": "Strategic Thinking", "importance": "preferred"},
            {"name": "Budgeting", "importance": "preferred"}
        ]
    else:
        required_skills = [
            {"name": "Communication", "importance": "required"},
            {"name": "Problem Solving", "importance": "required"},
            {"name": "Teamwork", "importance": "required"},
            {"name": "Time Management", "importance": "preferred"},
            {"name": "Microsoft Office", "importance": "preferred"}
        ]
    
    # Generate simulated experience requirements
    experience_requirements = {
        "years": 3,
        "seniority": "mid",
        "management": False,
        "domains": ["Technology"] if 'tech' in company.lower() else ["Business"]
    }
    
    # Generate simulated education requirements
    education_requirements = {
        "degree_level": 2,  # Bachelor's
        "fields": ["Computer Science", "Information Technology"] if 'developer' in title.lower() else ["Business", "Related Field"],
        "required": True
    }
    
    return {
        "required_skills": required_skills,
        "experience_requirements": experience_requirements,
        "education_requirements": education_requirements,
        "summary": f"This {title} position at {company} requires skills in {', '.join([skill['name'] for skill in required_skills[:3]])}. Candidates should have at least {experience_requirements['years']} years of experience and a Bachelor's degree in a relevant field."
    }

def simulate_job_matching(matching_data):
    """Simulate job matching response"""
    # Extract profile and job data
    profile = matching_data.get('profile', {})
    job = matching_data.get('job', {})
    criteria = matching_data.get('criteria', {})
    
    # Extract job title and company
    job_title = job.get('title', '')
    job_company = job.get('company', '')
    
    # Generate a match score between 50 and 95
    import random
    match_score = random.randint(50, 95)
    
    # Generate matching skills
    matching_skills = ["Python", "SQL", "Problem Solving"]
    
    # Generate missing skills
    missing_skills = ["Docker", "AWS", "React Native"]
    
    # Generate experience match
    experience_match = {
        "has_required_years": True,
        "has_required_seniority": True,
        "has_domain_experience": True
    }
    
    # Generate education match
    education_match = {
        "has_required_degree": True,
        "has_relevant_field": True
    }
    
    return {
        "match_score": match_score,
        "matching_skills": matching_skills,
        "missing_skills": missing_skills,
        "experience_match": experience_match,
        "education_match": education_match,
        "summary": f"You have a {match_score}% match with this {job_title} position at {job_company}. You match on key skills like {', '.join(matching_skills)}, but could improve in {', '.join(missing_skills)}. Your experience and education align well with the job requirements."
    }
