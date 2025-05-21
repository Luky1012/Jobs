from flask import Blueprint, request, render_template, redirect, url_for, flash, session, jsonify
from functools import wraps

from src.models.models import User, db

settings_bp = Blueprint('settings', __name__, url_prefix='/settings')

# Decorator to check if user is logged in
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            flash('Please log in first', 'warning')
            return redirect(url_for('auth.login'))
        return f(*args, **kwargs)
    return decorated_function

@settings_bp.route('/')
@login_required
def index():
    """Settings page"""
    user_id = session.get('user_id')
    
    # Get user data
    user = User.query.get(user_id)
    
    # Get LinkedIn profile
    from src.models.models import LinkedInProfile
    linkedin_profile = LinkedInProfile.query.filter_by(user_id=user_id).first()
    
    # Get job preferences
    from src.models.models import JobPreference
    job_pref = JobPreference.query.filter_by(user_id=user_id).first()
    
    # Get matching criteria
    from src.models.models import MatchingCriteria
    match_criteria = MatchingCriteria.query.filter_by(user_id=user_id).first()
    
    # Get application settings
    from src.models.models import ApplicationSetting
    app_settings = ApplicationSetting.query.filter_by(user_id=user_id).first()
    
    return render_template('settings/index.html',
                          user=user,
                          linkedin_profile=linkedin_profile,
                          job_pref=job_pref,
                          match_criteria=match_criteria,
                          app_settings=app_settings)

@settings_bp.route('/account', methods=['GET', 'POST'])
@login_required
def account():
    """Account settings page"""
    user_id = session.get('user_id')
    
    # Get user data
    user = User.query.get(user_id)
    
    if request.method == 'POST':
        # Update user data
        username = request.form.get('username')
        email = request.form.get('email')
        
        # Validate input
        if not username or not email:
            flash('Username and email are required', 'danger')
            return redirect(url_for('settings.account'))
        
        # Check if username or email already exists
        existing_user = User.query.filter(
            (User.username == username) | (User.email == email),
            User.id != user_id
        ).first()
        
        if existing_user:
            flash('Username or email already exists', 'danger')
            return redirect(url_for('settings.account'))
        
        # Update user
        user.username = username
        user.email = email
        db.session.commit()
        
        flash('Account settings updated successfully', 'success')
        return redirect(url_for('settings.account'))
    
    return render_template('settings/account.html', user=user)

@settings_bp.route('/password', methods=['GET', 'POST'])
@login_required
def password():
    """Password change page"""
    user_id = session.get('user_id')
    
    # Get user data
    user = User.query.get(user_id)
    
    if request.method == 'POST':
        # Update password
        current_password = request.form.get('current_password')
        new_password = request.form.get('new_password')
        confirm_password = request.form.get('confirm_password')
        
        # Validate input
        if not current_password or not new_password or not confirm_password:
            flash('All fields are required', 'danger')
            return redirect(url_for('settings.password'))
        
        # Check if current password is correct
        from werkzeug.security import check_password_hash
        if not check_password_hash(user.password_hash, current_password):
            flash('Current password is incorrect', 'danger')
            return redirect(url_for('settings.password'))
        
        # Check if new passwords match
        if new_password != confirm_password:
            flash('New passwords do not match', 'danger')
            return redirect(url_for('settings.password'))
        
        # Update password
        from werkzeug.security import generate_password_hash
        user.password_hash = generate_password_hash(new_password)
        db.session.commit()
        
        flash('Password updated successfully', 'success')
        return redirect(url_for('settings.password'))
    
    return render_template('settings/password.html')

@settings_bp.route('/notifications', methods=['GET', 'POST'])
@login_required
def notifications():
    """Notification settings page"""
    user_id = session.get('user_id')
    
    # Get application settings
    from src.models.models import ApplicationSetting
    app_settings = ApplicationSetting.query.filter_by(user_id=user_id).first()
    
    if not app_settings:
        app_settings = ApplicationSetting(user_id=user_id)
        db.session.add(app_settings)
        db.session.commit()
    
    if request.method == 'POST':
        # Update notification settings
        notify_on_application = 'notify_on_application' in request.form
        notify_on_response = 'notify_on_response' in request.form
        
        app_settings.notify_on_application = notify_on_application
        app_settings.notify_on_response = notify_on_response
        db.session.commit()
        
        flash('Notification settings updated successfully', 'success')
        return redirect(url_for('settings.notifications'))
    
    return render_template('settings/notifications.html', app_settings=app_settings)

@settings_bp.route('/data', methods=['GET', 'POST'])
@login_required
def data():
    """Data management page"""
    user_id = session.get('user_id')
    
    if request.method == 'POST':
        action = request.form.get('action')
        
        if action == 'export':
            # Export user data
            user_data = export_user_data(user_id)
            
            # Return as JSON file
            return jsonify(user_data)
        
        elif action == 'delete_applications':
            # Delete all job applications
            from src.models.models import JobApplication
            JobApplication.query.filter_by(user_id=user_id).delete()
            db.session.commit()
            
            flash('All job applications have been deleted', 'success')
            return redirect(url_for('settings.data'))
        
        elif action == 'delete_matches':
            # Delete all job matches
            from src.models.models import JobMatch
            JobMatch.query.filter_by(user_id=user_id).delete()
            db.session.commit()
            
            flash('All job matches have been deleted', 'success')
            return redirect(url_for('settings.data'))
        
        elif action == 'delete_account':
            # Delete user account and all related data
            delete_user_account(user_id)
            
            # Clear session
            session.clear()
            
            flash('Your account has been deleted', 'success')
            return redirect(url_for('auth.login'))
    
    return render_template('settings/data.html')

def export_user_data(user_id):
    """Export all user data"""
    # Get user data
    user = User.query.get(user_id)
    
    # Get LinkedIn profile
    from src.models.models import LinkedInProfile
    linkedin_profile = LinkedInProfile.query.filter_by(user_id=user_id).first()
    
    # Get job preferences
    from src.models.models import JobPreference
    job_pref = JobPreference.query.filter_by(user_id=user_id).first()
    
    # Get matching criteria
    from src.models.models import MatchingCriteria
    match_criteria = MatchingCriteria.query.filter_by(user_id=user_id).first()
    
    # Get application settings
    from src.models.models import ApplicationSetting
    app_settings = ApplicationSetting.query.filter_by(user_id=user_id).first()
    
    # Get job applications
    from src.models.models import JobApplication
    applications = JobApplication.query.filter_by(user_id=user_id).all()
    
    # Get job matches
    from src.models.models import JobMatch
    matches = JobMatch.query.filter_by(user_id=user_id).all()
    
    # Get daily summaries
    from src.models.models import DailySummary
    summaries = DailySummary.query.filter_by(user_id=user_id).all()
    
    # Prepare data
    user_data = {
        'user': {
            'id': user.id,
            'username': user.username,
            'email': user.email,
            'created_at': user.created_at.isoformat() if user.created_at else None,
            'is_active': user.is_active,
            'is_verified': user.is_verified
        },
        'linkedin_profile': None,
        'job_preferences': None,
        'matching_criteria': None,
        'application_settings': None,
        'applications': [],
        'matches': [],
        'summaries': []
    }
    
    # Add LinkedIn profile
    if linkedin_profile:
        user_data['linkedin_profile'] = {
            'id': linkedin_profile.id,
            'linkedin_id': linkedin_profile.linkedin_id,
            'last_updated': linkedin_profile.last_updated.isoformat() if linkedin_profile.last_updated else None
        }
    
    # Add job preferences
    if job_pref:
        import json
        user_data['job_preferences'] = {
            'id': job_pref.id,
            'location': job_pref.location,
            'industries': json.loads(job_pref.industries) if job_pref.industries else [],
            'job_types': json.loads(job_pref.job_types) if job_pref.job_types else [],
            'experience_level': job_pref.experience_level,
            'salary_min': job_pref.salary_min,
            'salary_max': job_pref.salary_max,
            'created_at': job_pref.created_at.isoformat() if job_pref.created_at else None,
            'updated_at': job_pref.updated_at.isoformat() if job_pref.updated_at else None
        }
    
    # Add matching criteria
    if match_criteria:
        import json
        user_data['matching_criteria'] = {
            'id': match_criteria.id,
            'min_match_threshold': match_criteria.min_match_threshold,
            'skills_weight': match_criteria.skills_weight,
            'experience_weight': match_criteria.experience_weight,
            'education_weight': match_criteria.education_weight,
            'preferred_companies': json.loads(match_criteria.preferred_companies) if match_criteria.preferred_companies else [],
            'created_at': match_criteria.created_at.isoformat() if match_criteria.created_at else None,
            'updated_at': match_criteria.updated_at.isoformat() if match_criteria.updated_at else None
        }
    
    # Add application settings
    if app_settings:
        user_data['application_settings'] = {
            'id': app_settings.id,
            'daily_limit': app_settings.daily_limit,
            'application_time': app_settings.application_time,
            'is_active': app_settings.is_active,
            'notify_on_application': app_settings.notify_on_application,
            'notify_on_response': app_settings.notify_on_response,
            'created_at': app_settings.created_at.isoformat() if app_settings.created_at else None,
            'updated_at': app_settings.updated_at.isoformat() if app_settings.updated_at else None
        }
    
    # Add job applications
    for app in applications:
        user_data['applications'].append({
            'id': app.id,
            'job_id': app.job_id,
            'status': app.status,
            'applied_at': app.applied_at.isoformat() if app.applied_at else None,
            'response_at': app.response_at.isoformat() if app.response_at else None,
            'notes': app.notes
        })
    
    # Add job matches
    for match in matches:
        import json
        user_data['matches'].append({
            'id': match.id,
            'job_id': match.job_id,
            'match_score': match.match_score,
            'skills_match': json.loads(match.skills_match) if match.skills_match else [],
            'missing_skills': json.loads(match.missing_skills) if match.missing_skills else [],
            'created_at': match.created_at.isoformat() if match.created_at else None
        })
    
    # Add daily summaries
    for summary in summaries:
        import json
        user_data['summaries'].append({
            'id': summary.id,
            'date': summary.date.isoformat() if summary.date else None,
            'jobs_analyzed': summary.jobs_analyzed,
            'excellent_matches': summary.excellent_matches,
            'good_matches': summary.good_matches,
            'fair_matches': summary.fair_matches,
            'poor_matches': summary.poor_matches,
            'applications_submitted': summary.applications_submitted,
            'summary_data': json.loads(summary.summary_data) if summary.summary_data else {},
            'created_at': summary.created_at.isoformat() if summary.created_at else None
        })
    
    return user_data

def delete_user_account(user_id):
    """Delete user account and all related data"""
    # Delete LinkedIn profile
    from src.models.models import LinkedInProfile
    LinkedInProfile.query.filter_by(user_id=user_id).delete()
    
    # Delete job preferences
    from src.models.models import JobPreference
    JobPreference.query.filter_by(user_id=user_id).delete()
    
    # Delete matching criteria
    from src.models.models import MatchingCriteria
    MatchingCriteria.query.filter_by(user_id=user_id).delete()
    
    # Delete application settings
    from src.models.models import ApplicationSetting
    ApplicationSetting.query.filter_by(user_id=user_id).delete()
    
    # Delete job applications
    from src.models.models import JobApplication
    JobApplication.query.filter_by(user_id=user_id).delete()
    
    # Delete job matches
    from src.models.models import JobMatch
    JobMatch.query.filter_by(user_id=user_id).delete()
    
    # Delete daily summaries
    from src.models.models import DailySummary
    DailySummary.query.filter_by(user_id=user_id).delete()
    
    # Delete API call logs
    from src.models.models import ApiCallLog
    ApiCallLog.query.filter_by(user_id=user_id).delete()
    
    # Delete user
    user = User.query.get(user_id)
    if user:
        db.session.delete(user)
    
    db.session.commit()
