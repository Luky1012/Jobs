from flask import Blueprint, request, render_template, redirect, url_for, flash, session, jsonify
from functools import wraps
import json

from src.models.models import User, JobPreference, MatchingCriteria, ApplicationSetting, db

wizard_bp = Blueprint('wizard', __name__, url_prefix='/wizard')

# Decorator to check if user is logged in
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            flash('Please log in first', 'warning')
            return redirect(url_for('auth.login'))
        return f(*args, **kwargs)
    return decorated_function

# Decorator to check if LinkedIn is connected
def linkedin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        user_id = session.get('user_id')
        if not user_id:
            flash('Please log in first', 'warning')
            return redirect(url_for('auth.login'))
            
        from src.models.models import LinkedInProfile
        linkedin_profile = LinkedInProfile.query.filter_by(user_id=user_id).first()
        if not linkedin_profile or not linkedin_profile.access_token:
            flash('Please connect your LinkedIn account first', 'warning')
            return redirect(url_for('wizard.linkedin_connection'))
        return f(*args, **kwargs)
    return decorated_function

@wizard_bp.route('/')
@login_required
def index():
    """Wizard start page"""
    return render_template('wizard/index.html')

@wizard_bp.route('/linkedin-connection', methods=['GET'])
@login_required
def linkedin_connection():
    """Step 1: LinkedIn Connection"""
    user_id = session.get('user_id')
    
    from src.models.models import LinkedInProfile
    linkedin_profile = LinkedInProfile.query.filter_by(user_id=user_id).first()
    
    return render_template('wizard/linkedin_connection.html', linkedin_profile=linkedin_profile)

@wizard_bp.route('/profile-analysis', methods=['GET'])
@login_required
@linkedin_required
def profile_analysis():
    """Step 2: Profile Analysis"""
    user_id = session.get('user_id')
    
    from src.models.models import LinkedInProfile
    linkedin_profile = LinkedInProfile.query.filter_by(user_id=user_id).first()
    
    profile_data = {}
    if linkedin_profile and linkedin_profile.profile_data:
        profile_data = json.loads(linkedin_profile.profile_data)
    
    return render_template('wizard/profile_analysis.html', profile_data=profile_data)

@wizard_bp.route('/job-preferences', methods=['GET', 'POST'])
@login_required
@linkedin_required
def job_preferences():
    """Step 3: Job Preferences"""
    user_id = session.get('user_id')
    
    # Get existing job preferences or create new ones
    job_pref = JobPreference.query.filter_by(user_id=user_id).first()
    if not job_pref:
        job_pref = JobPreference(user_id=user_id)
        db.session.add(job_pref)
        db.session.commit()
    
    if request.method == 'POST':
        # Update job preferences
        job_pref.location = request.form.get('location', 'UAE')
        job_pref.industries = json.dumps(request.form.getlist('industries[]'))
        job_pref.job_types = json.dumps(request.form.getlist('job_types[]'))
        job_pref.experience_level = request.form.get('experience_level')
        
        # Handle salary range
        salary_min = request.form.get('salary_min')
        salary_max = request.form.get('salary_max')
        
        if salary_min and salary_min.isdigit():
            job_pref.salary_min = int(salary_min)
        
        if salary_max and salary_max.isdigit():
            job_pref.salary_max = int(salary_max)
        
        db.session.commit()
        
        flash('Job preferences saved successfully', 'success')
        return redirect(url_for('wizard.matching_criteria'))
    
    # Prepare data for template
    industries = [
        "Technology", "Finance", "Healthcare", "Education", 
        "Retail", "Manufacturing", "Construction", "Energy",
        "Telecommunications", "Transportation", "Hospitality",
        "Media", "Entertainment", "Real Estate", "Consulting"
    ]
    
    job_types = [
        "Full-time", "Part-time", "Contract", "Temporary",
        "Internship", "Volunteer", "Remote"
    ]
    
    experience_levels = [
        "Entry level", "Associate", "Mid-Senior level",
        "Director", "Executive"
    ]
    
    # Parse JSON strings to lists
    selected_industries = json.loads(job_pref.industries) if job_pref.industries else []
    selected_job_types = json.loads(job_pref.job_types) if job_pref.job_types else []
    
    return render_template('wizard/job_preferences.html', 
                          job_pref=job_pref,
                          industries=industries,
                          job_types=job_types,
                          experience_levels=experience_levels,
                          selected_industries=selected_industries,
                          selected_job_types=selected_job_types)

@wizard_bp.route('/matching-criteria', methods=['GET', 'POST'])
@login_required
@linkedin_required
def matching_criteria():
    """Step 4: Matching Criteria"""
    user_id = session.get('user_id')
    
    # Get existing matching criteria or create new ones
    match_criteria = MatchingCriteria.query.filter_by(user_id=user_id).first()
    if not match_criteria:
        match_criteria = MatchingCriteria(user_id=user_id)
        db.session.add(match_criteria)
        db.session.commit()
    
    if request.method == 'POST':
        # Update matching criteria
        min_threshold = request.form.get('min_match_threshold')
        skills_weight = request.form.get('skills_weight')
        experience_weight = request.form.get('experience_weight')
        education_weight = request.form.get('education_weight')
        preferred_companies = request.form.get('preferred_companies')
        
        if min_threshold and min_threshold.isdigit():
            match_criteria.min_match_threshold = int(min_threshold)
        
        if skills_weight and skills_weight.isdigit():
            match_criteria.skills_weight = int(skills_weight)
        
        if experience_weight and experience_weight.isdigit():
            match_criteria.experience_weight = int(experience_weight)
        
        if education_weight and education_weight.isdigit():
            match_criteria.education_weight = int(education_weight)
        
        # Process preferred companies as a comma-separated list
        if preferred_companies:
            companies_list = [company.strip() for company in preferred_companies.split(',')]
            match_criteria.preferred_companies = json.dumps(companies_list)
        
        db.session.commit()
        
        flash('Matching criteria saved successfully', 'success')
        return redirect(url_for('wizard.application_settings'))
    
    # Parse JSON string to list
    preferred_companies = json.loads(match_criteria.preferred_companies) if match_criteria.preferred_companies else []
    preferred_companies_str = ', '.join(preferred_companies)
    
    return render_template('wizard/matching_criteria.html', 
                          match_criteria=match_criteria,
                          preferred_companies=preferred_companies_str)

@wizard_bp.route('/application-settings', methods=['GET', 'POST'])
@login_required
@linkedin_required
def application_settings():
    """Step 5: Application Settings"""
    user_id = session.get('user_id')
    
    # Get existing application settings or create new ones
    app_settings = ApplicationSetting.query.filter_by(user_id=user_id).first()
    if not app_settings:
        app_settings = ApplicationSetting(user_id=user_id)
        db.session.add(app_settings)
        db.session.commit()
    
    if request.method == 'POST':
        # Update application settings
        daily_limit = request.form.get('daily_limit')
        application_time = request.form.get('application_time')
        custom_message = request.form.get('custom_message')
        notify_on_application = 'notify_on_application' in request.form
        notify_on_response = 'notify_on_response' in request.form
        
        if daily_limit and daily_limit.isdigit():
            app_settings.daily_limit = int(daily_limit)
        
        app_settings.application_time = application_time
        app_settings.custom_message = custom_message
        app_settings.notify_on_application = notify_on_application
        app_settings.notify_on_response = notify_on_response
        
        db.session.commit()
        
        flash('Application settings saved successfully', 'success')
        return redirect(url_for('wizard.review'))
    
    return render_template('wizard/application_settings.html', app_settings=app_settings)

@wizard_bp.route('/review', methods=['GET', 'POST'])
@login_required
@linkedin_required
def review():
    """Step 6: Review & Activate"""
    user_id = session.get('user_id')
    
    # Get all settings for review
    from src.models.models import LinkedInProfile
    linkedin_profile = LinkedInProfile.query.filter_by(user_id=user_id).first()
    job_pref = JobPreference.query.filter_by(user_id=user_id).first()
    match_criteria = MatchingCriteria.query.filter_by(user_id=user_id).first()
    app_settings = ApplicationSetting.query.filter_by(user_id=user_id).first()
    
    if request.method == 'POST':
        # Activate automation
        if app_settings:
            app_settings.is_active = True
            db.session.commit()
            
            flash('Job application automation has been activated!', 'success')
            return redirect(url_for('dashboard.index'))
    
    # Parse JSON strings for display
    industries = json.loads(job_pref.industries) if job_pref and job_pref.industries else []
    job_types = json.loads(job_pref.job_types) if job_pref and job_pref.job_types else []
    preferred_companies = json.loads(match_criteria.preferred_companies) if match_criteria and match_criteria.preferred_companies else []
    
    return render_template('wizard/review.html',
                          linkedin_profile=linkedin_profile,
                          job_pref=job_pref,
                          match_criteria=match_criteria,
                          app_settings=app_settings,
                          industries=industries,
                          job_types=job_types,
                          preferred_companies=preferred_companies)
