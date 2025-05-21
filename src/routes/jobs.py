from flask import Blueprint, request, render_template, redirect, url_for, flash, session, jsonify
from functools import wraps
import json

from src.models.models import User, Job, JobMatch, JobApplication, db

jobs_bp = Blueprint('jobs', __name__, url_prefix='/jobs')

# Decorator to check if user is logged in
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            flash('Please log in first', 'warning')
            return redirect(url_for('auth.login'))
        return f(*args, **kwargs)
    return decorated_function

@jobs_bp.route('/')
@login_required
def index():
    """Jobs listing page"""
    user_id = session.get('user_id')
    
    # Get filter parameters
    min_score = request.args.get('min_score', 0, type=int)
    max_score = request.args.get('max_score', 100, type=int)
    status = request.args.get('status', 'all')
    
    # Base query for job matches
    query = JobMatch.query.filter_by(user_id=user_id)
    
    # Apply score filter
    query = query.filter(JobMatch.match_score >= min_score, JobMatch.match_score <= max_score)
    
    # Order by match score
    query = query.order_by(JobMatch.match_score.desc())
    
    # Get job matches
    job_matches = query.all()
    
    # Get jobs and application status
    jobs = {}
    applications = {}
    
    for match in job_matches:
        job = Job.query.get(match.job_id)
        if job:
            jobs[match.job_id] = job
            
            # Check if already applied
            application = JobApplication.query.filter_by(user_id=user_id, job_id=job.id).first()
            if application:
                applications[job.id] = application
    
    # Filter by application status if needed
    if status != 'all':
        filtered_matches = []
        for match in job_matches:
            if status == 'applied' and match.job_id in applications:
                filtered_matches.append(match)
            elif status == 'not_applied' and match.job_id not in applications:
                filtered_matches.append(match)
        job_matches = filtered_matches
    
    return render_template('jobs/index.html',
                          job_matches=job_matches,
                          jobs=jobs,
                          applications=applications,
                          min_score=min_score,
                          max_score=max_score,
                          status=status)

@jobs_bp.route('/<int:job_id>')
@login_required
def view(job_id):
    """Job details page"""
    user_id = session.get('user_id')
    
    # Get job
    job = Job.query.get_or_404(job_id)
    
    # Get job match
    job_match = JobMatch.query.filter_by(user_id=user_id, job_id=job.id).first()
    
    if not job_match:
        flash('Job match not found', 'warning')
        return redirect(url_for('jobs.index'))
    
    # Get job analysis
    from src.models.models import JobAnalysis
    job_analysis = JobAnalysis.query.filter_by(job_id=job.id).first()
    
    # Check if already applied
    application = JobApplication.query.filter_by(user_id=user_id, job_id=job.id).first()
    
    # Parse JSON data
    match_details = json.loads(job_match.match_details) if job_match.match_details else {}
    skills_match = json.loads(job_match.skills_match) if job_match.skills_match else []
    missing_skills = json.loads(job_match.missing_skills) if job_match.missing_skills else []
    
    analysis_data = {}
    if job_analysis and job_analysis.analysis_data:
        analysis_data = json.loads(job_analysis.analysis_data)
    
    required_skills = []
    if job_analysis and job_analysis.required_skills:
        required_skills = json.loads(job_analysis.required_skills)
    
    return render_template('jobs/view.html',
                          job=job,
                          job_match=job_match,
                          job_analysis=job_analysis,
                          application=application,
                          match_details=match_details,
                          skills_match=skills_match,
                          missing_skills=missing_skills,
                          analysis_data=analysis_data,
                          required_skills=required_skills)

@jobs_bp.route('/apply/<int:job_id>', methods=['POST'])
@login_required
def apply(job_id):
    """Apply to job"""
    user_id = session.get('user_id')
    
    # Get job
    job = Job.query.get_or_404(job_id)
    
    # Check if already applied
    existing_application = JobApplication.query.filter_by(user_id=user_id, job_id=job.id).first()
    
    if existing_application:
        flash('You have already applied to this job', 'warning')
        return redirect(url_for('jobs.view', job_id=job.id))
    
    # Apply to job using Grok API
    from src.routes.grok import apply_job
    result = apply_job()
    
    if isinstance(result, tuple) and len(result) > 1 and isinstance(result[0], dict) and 'error' in result[0]:
        flash(result[0]['error'], 'danger')
    else:
        flash('Application submitted successfully', 'success')
    
    return redirect(url_for('jobs.view', job_id=job.id))

@jobs_bp.route('/search', methods=['GET', 'POST'])
@login_required
def search():
    """Search for jobs"""
    user_id = session.get('user_id')
    
    if request.method == 'POST':
        # Get search parameters
        keywords = request.form.get('keywords', '')
        location = request.form.get('location', 'UAE')
        
        # This would be a real API call to LinkedIn in production
        # For now, we'll simulate finding jobs
        
        # Create some sample jobs
        sample_jobs = [
            {
                'linkedin_job_id': 'job123',
                'title': 'Senior Software Engineer',
                'company': 'Tech Solutions LLC',
                'location': 'Dubai, UAE',
                'description': 'We are looking for a Senior Software Engineer with experience in Python, JavaScript, and cloud technologies.',
                'job_url': 'https://linkedin.com/jobs/view/job123',
                'posted_at': '2025-05-15',
                'employment_type': 'Full-time',
                'industries': ['Technology', 'Software Development']
            },
            {
                'linkedin_job_id': 'job456',
                'title': 'Data Scientist',
                'company': 'Analytics Innovations',
                'location': 'Abu Dhabi, UAE',
                'description': 'Join our team as a Data Scientist working on cutting-edge AI and machine learning projects.',
                'job_url': 'https://linkedin.com/jobs/view/job456',
                'posted_at': '2025-05-18',
                'employment_type': 'Full-time',
                'industries': ['Technology', 'Data Science']
            },
            {
                'linkedin_job_id': 'job789',
                'title': 'Product Manager',
                'company': 'Global Tech',
                'location': 'Dubai, UAE',
                'description': 'We are seeking an experienced Product Manager to lead our product development initiatives.',
                'job_url': 'https://linkedin.com/jobs/view/job789',
                'posted_at': '2025-05-19',
                'employment_type': 'Full-time',
                'industries': ['Technology', 'Product Management']
            }
        ]
        
        # Save jobs to database
        saved_jobs = []
        
        for job_data in sample_jobs:
            # Check if job already exists
            existing_job = Job.query.filter_by(linkedin_job_id=job_data['linkedin_job_id']).first()
            
            if existing_job:
                saved_jobs.append(existing_job)
                continue
            
            # Create new job
            new_job = Job(
                linkedin_job_id=job_data['linkedin_job_id'],
                title=job_data['title'],
                company=job_data['company'],
                location=job_data['location'],
                description=job_data['description'],
                job_url=job_data['job_url'],
                posted_at=datetime.strptime(job_data['posted_at'], '%Y-%m-%d'),
                employment_type=job_data['employment_type'],
                industries=json.dumps(job_data['industries'])
            )
            
            db.session.add(new_job)
            db.session.commit()
            
            saved_jobs.append(new_job)
            
            # Analyze job and create match
            from src.routes.grok import analyze_job, match_job
            analyze_job({'job_id': new_job.id})
            match_job({'job_id': new_job.id})
        
        flash(f'Found {len(saved_jobs)} jobs matching your search', 'success')
        return redirect(url_for('jobs.index'))
    
    return render_template('jobs/search.html')

@jobs_bp.route('/refresh-matches', methods=['POST'])
@login_required
def refresh_matches():
    """Refresh job matches"""
    user_id = session.get('user_id')
    
    # Get all jobs
    jobs = Job.query.all()
    
    # Refresh matches for each job
    match_count = 0
    
    for job in jobs:
        # Check if match already exists
        existing_match = JobMatch.query.filter_by(user_id=user_id, job_id=job.id).first()
        
        if existing_match:
            # Delete existing match
            db.session.delete(existing_match)
            db.session.commit()
        
        # Create new match
        from src.routes.grok import match_job
        match_job({'job_id': job.id})
        match_count += 1
    
    flash(f'Refreshed matches for {match_count} jobs', 'success')
    return redirect(url_for('jobs.index'))
