from flask import Blueprint, request, render_template, redirect, url_for, flash, session, jsonify
from functools import wraps
import json
from datetime import datetime, timedelta

from src.models.models import User, Job, JobMatch, JobApplication, DailySummary, db

dashboard_bp = Blueprint('dashboard', __name__, url_prefix='/dashboard')

# Decorator to check if user is logged in
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            flash('Please log in first', 'warning')
            return redirect(url_for('auth.login'))
        return f(*args, **kwargs)
    return decorated_function

@dashboard_bp.route('/')
@login_required
def index():
    """Dashboard home page"""
    user_id = session.get('user_id')
    
    # Get LinkedIn profile status
    from src.models.models import LinkedInProfile
    linkedin_profile = LinkedInProfile.query.filter_by(user_id=user_id).first()
    
    # Get application settings
    from src.models.models import ApplicationSetting
    app_settings = ApplicationSetting.query.filter_by(user_id=user_id).first()
    
    # Get recent job applications
    recent_applications = JobApplication.query.filter_by(user_id=user_id).order_by(
        JobApplication.applied_at.desc()
    ).limit(5).all()
    
    # Get application statistics
    total_applications = JobApplication.query.filter_by(user_id=user_id).count()
    
    # Get recent job matches
    recent_matches = JobMatch.query.filter_by(user_id=user_id).order_by(
        JobMatch.match_score.desc()
    ).limit(5).all()
    
    # Get match statistics
    excellent_matches = JobMatch.query.filter_by(user_id=user_id).filter(JobMatch.match_score >= 90).count()
    good_matches = JobMatch.query.filter_by(user_id=user_id).filter(JobMatch.match_score >= 70, JobMatch.match_score < 90).count()
    fair_matches = JobMatch.query.filter_by(user_id=user_id).filter(JobMatch.match_score >= 50, JobMatch.match_score < 70).count()
    
    # Get setup completion status
    setup_complete = False
    if linkedin_profile and app_settings:
        setup_complete = app_settings.is_active
    
    # Get jobs for recent applications
    application_jobs = {}
    for app in recent_applications:
        job = Job.query.get(app.job_id)
        if job:
            application_jobs[app.id] = job
    
    # Get jobs for recent matches
    match_jobs = {}
    for match in recent_matches:
        job = Job.query.get(match.job_id)
        if job:
            match_jobs[match.id] = job
    
    return render_template('dashboard/index.html',
                          linkedin_profile=linkedin_profile,
                          app_settings=app_settings,
                          recent_applications=recent_applications,
                          application_jobs=application_jobs,
                          total_applications=total_applications,
                          recent_matches=recent_matches,
                          match_jobs=match_jobs,
                          excellent_matches=excellent_matches,
                          good_matches=good_matches,
                          fair_matches=fair_matches,
                          setup_complete=setup_complete)

@dashboard_bp.route('/activity')
@login_required
def activity():
    """Activity timeline page"""
    user_id = session.get('user_id')
    
    # Get all job applications
    applications = JobApplication.query.filter_by(user_id=user_id).order_by(
        JobApplication.applied_at.desc()
    ).all()
    
    # Get jobs for applications
    application_jobs = {}
    for app in applications:
        job = Job.query.get(app.job_id)
        if job:
            application_jobs[app.id] = job
    
    # Get daily summaries
    summaries = DailySummary.query.filter_by(user_id=user_id).order_by(
        DailySummary.date.desc()
    ).limit(30).all()
    
    return render_template('dashboard/activity.html',
                          applications=applications,
                          application_jobs=application_jobs,
                          summaries=summaries)

@dashboard_bp.route('/stats')
@login_required
def stats():
    """Statistics and analytics page"""
    user_id = session.get('user_id')
    
    # Get application statistics
    total_applications = JobApplication.query.filter_by(user_id=user_id).count()
    
    # Get status breakdown
    status_counts = {}
    for status in ['pending', 'submitted', 'viewed', 'responded', 'rejected']:
        count = JobApplication.query.filter_by(user_id=user_id, status=status).count()
        status_counts[status] = count
    
    # Get match statistics
    excellent_matches = JobMatch.query.filter_by(user_id=user_id).filter(JobMatch.match_score >= 90).count()
    good_matches = JobMatch.query.filter_by(user_id=user_id).filter(JobMatch.match_score >= 70, JobMatch.match_score < 90).count()
    fair_matches = JobMatch.query.filter_by(user_id=user_id).filter(JobMatch.match_score >= 50, JobMatch.match_score < 70).count()
    poor_matches = JobMatch.query.filter_by(user_id=user_id).filter(JobMatch.match_score < 50).count()
    
    # Get application timeline data
    thirty_days_ago = datetime.utcnow() - timedelta(days=30)
    daily_applications = db.session.query(
        db.func.date(JobApplication.applied_at).label('date'),
        db.func.count(JobApplication.id).label('count')
    ).filter(
        JobApplication.user_id == user_id,
        JobApplication.applied_at >= thirty_days_ago
    ).group_by(
        db.func.date(JobApplication.applied_at)
    ).order_by(
        db.func.date(JobApplication.applied_at)
    ).all()
    
    # Format timeline data for charts
    timeline_dates = [str(row.date) for row in daily_applications]
    timeline_counts = [row.count for row in daily_applications]
    
    return render_template('dashboard/stats.html',
                          total_applications=total_applications,
                          status_counts=status_counts,
                          excellent_matches=excellent_matches,
                          good_matches=good_matches,
                          fair_matches=fair_matches,
                          poor_matches=poor_matches,
                          timeline_dates=json.dumps(timeline_dates),
                          timeline_counts=json.dumps(timeline_counts))

@dashboard_bp.route('/pause-automation', methods=['POST'])
@login_required
def pause_automation():
    """Pause job application automation"""
    user_id = session.get('user_id')
    
    # Get application settings
    from src.models.models import ApplicationSetting
    app_settings = ApplicationSetting.query.filter_by(user_id=user_id).first()
    
    if app_settings:
        app_settings.is_active = False
        db.session.commit()
        flash('Job application automation has been paused', 'success')
    else:
        flash('Application settings not found', 'danger')
    
    return redirect(url_for('dashboard.index'))

@dashboard_bp.route('/resume-automation', methods=['POST'])
@login_required
def resume_automation():
    """Resume job application automation"""
    user_id = session.get('user_id')
    
    # Get application settings
    from src.models.models import ApplicationSetting
    app_settings = ApplicationSetting.query.filter_by(user_id=user_id).first()
    
    if app_settings:
        app_settings.is_active = True
        db.session.commit()
        flash('Job application automation has been resumed', 'success')
    else:
        flash('Application settings not found', 'danger')
    
    return redirect(url_for('dashboard.index'))

@dashboard_bp.route('/daily-summary')
@login_required
def daily_summary():
    """Generate and view daily summary"""
    user_id = session.get('user_id')
    
    # Get date parameter or use today
    date_str = request.args.get('date')
    if date_str:
        try:
            summary_date = datetime.strptime(date_str, '%Y-%m-%d').date()
        except ValueError:
            summary_date = datetime.utcnow().date()
    else:
        summary_date = datetime.utcnow().date()
    
    # Get or create daily summary
    summary = DailySummary.query.filter_by(user_id=user_id, date=summary_date).first()
    
    if not summary:
        # Calculate summary data
        jobs_analyzed = JobMatch.query.filter_by(user_id=user_id).filter(
            db.func.date(JobMatch.created_at) == summary_date
        ).count()
        
        excellent_matches = JobMatch.query.filter_by(user_id=user_id).filter(
            db.func.date(JobMatch.created_at) == summary_date,
            JobMatch.match_score >= 90
        ).count()
        
        good_matches = JobMatch.query.filter_by(user_id=user_id).filter(
            db.func.date(JobMatch.created_at) == summary_date,
            JobMatch.match_score >= 70,
            JobMatch.match_score < 90
        ).count()
        
        fair_matches = JobMatch.query.filter_by(user_id=user_id).filter(
            db.func.date(JobMatch.created_at) == summary_date,
            JobMatch.match_score >= 50,
            JobMatch.match_score < 70
        ).count()
        
        poor_matches = JobMatch.query.filter_by(user_id=user_id).filter(
            db.func.date(JobMatch.created_at) == summary_date,
            JobMatch.match_score < 50
        ).count()
        
        applications_submitted = JobApplication.query.filter_by(user_id=user_id).filter(
            db.func.date(JobApplication.applied_at) == summary_date
        ).count()
        
        # Get top matches
        top_matches = JobMatch.query.filter_by(user_id=user_id).filter(
            db.func.date(JobMatch.created_at) == summary_date
        ).order_by(
            JobMatch.match_score.desc()
        ).limit(5).all()
        
        top_match_data = []
        for match in top_matches:
            job = Job.query.get(match.job_id)
            if job:
                application = JobApplication.query.filter_by(user_id=user_id, job_id=job.id).first()
                top_match_data.append({
                    'job_title': job.title,
                    'company': job.company,
                    'match_score': match.match_score,
                    'applied': application is not None
                })
        
        # Create summary data
        summary_data = {
            'jobs_analyzed': jobs_analyzed,
            'excellent_matches': excellent_matches,
            'good_matches': good_matches,
            'fair_matches': fair_matches,
            'poor_matches': poor_matches,
            'applications_submitted': applications_submitted,
            'top_matches': top_match_data
        }
        
        # Create new summary
        summary = DailySummary(
            user_id=user_id,
            date=summary_date,
            jobs_analyzed=jobs_analyzed,
            excellent_matches=excellent_matches,
            good_matches=good_matches,
            fair_matches=fair_matches,
            poor_matches=poor_matches,
            applications_submitted=applications_submitted,
            summary_data=json.dumps(summary_data)
        )
        
        db.session.add(summary)
        db.session.commit()
    
    # Parse summary data
    summary_data = json.loads(summary.summary_data) if summary.summary_data else {}
    
    return render_template('dashboard/daily_summary.html',
                          summary=summary,
                          summary_data=summary_data,
                          summary_date=summary_date)
