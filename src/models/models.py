from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
from src.main import db

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(256), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    is_active = db.Column(db.Boolean, default=True)
    is_verified = db.Column(db.Boolean, default=False)
    verification_token = db.Column(db.String(100), nullable=True)
    
    # Relationships
    linkedin_profile = db.relationship('LinkedInProfile', backref='user', uselist=False)
    job_preferences = db.relationship('JobPreference', backref='user', uselist=False)
    application_settings = db.relationship('ApplicationSetting', backref='user', uselist=False)
    job_applications = db.relationship('JobApplication', backref='user')
    
    def __repr__(self):
        return f'<User {self.username}>'

class LinkedInProfile(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    linkedin_id = db.Column(db.String(100), nullable=True)
    access_token = db.Column(db.String(500), nullable=True)
    refresh_token = db.Column(db.String(500), nullable=True)
    token_expiry = db.Column(db.DateTime, nullable=True)
    profile_data = db.Column(db.Text, nullable=True)  # JSON string of profile data
    skills = db.Column(db.Text, nullable=True)  # JSON string of skills
    experience = db.Column(db.Text, nullable=True)  # JSON string of experience
    education = db.Column(db.Text, nullable=True)  # JSON string of education
    last_updated = db.Column(db.DateTime, default=datetime.utcnow)
    
    def __repr__(self):
        return f'<LinkedInProfile {self.linkedin_id}>'

class JobPreference(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    location = db.Column(db.String(100), default='UAE')
    industries = db.Column(db.Text, nullable=True)  # JSON string of industries
    job_types = db.Column(db.Text, nullable=True)  # JSON string of job types
    experience_level = db.Column(db.String(50), nullable=True)
    salary_min = db.Column(db.Integer, nullable=True)
    salary_max = db.Column(db.Integer, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def __repr__(self):
        return f'<JobPreference {self.user_id}>'

class MatchingCriteria(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    min_match_threshold = db.Column(db.Integer, default=80)
    skills_weight = db.Column(db.Integer, default=40)
    experience_weight = db.Column(db.Integer, default=35)
    education_weight = db.Column(db.Integer, default=25)
    preferred_companies = db.Column(db.Text, nullable=True)  # JSON string of companies
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def __repr__(self):
        return f'<MatchingCriteria {self.user_id}>'

class ApplicationSetting(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    daily_limit = db.Column(db.Integer, default=5)
    application_time = db.Column(db.String(50), default='09:00')  # Time of day to run applications
    is_active = db.Column(db.Boolean, default=False)
    custom_message = db.Column(db.Text, nullable=True)
    notify_on_application = db.Column(db.Boolean, default=True)
    notify_on_response = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def __repr__(self):
        return f'<ApplicationSetting {self.user_id}>'

class Job(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    linkedin_job_id = db.Column(db.String(100), unique=True, nullable=False)
    title = db.Column(db.String(200), nullable=False)
    company = db.Column(db.String(200), nullable=False)
    location = db.Column(db.String(200), nullable=True)
    description = db.Column(db.Text, nullable=True)
    job_url = db.Column(db.String(500), nullable=True)
    posted_at = db.Column(db.DateTime, nullable=True)
    expires_at = db.Column(db.DateTime, nullable=True)
    job_function = db.Column(db.String(200), nullable=True)
    employment_type = db.Column(db.String(100), nullable=True)
    industries = db.Column(db.Text, nullable=True)  # JSON string of industries
    seniority_level = db.Column(db.String(100), nullable=True)
    job_data = db.Column(db.Text, nullable=True)  # JSON string of full job data
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    job_analyses = db.relationship('JobAnalysis', backref='job')
    job_matches = db.relationship('JobMatch', backref='job')
    job_applications = db.relationship('JobApplication', backref='job')
    
    def __repr__(self):
        return f'<Job {self.title} at {self.company}>'

class JobAnalysis(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    job_id = db.Column(db.Integer, db.ForeignKey('job.id'), nullable=False)
    required_skills = db.Column(db.Text, nullable=True)  # JSON string of skills
    experience_requirements = db.Column(db.Text, nullable=True)  # JSON string of experience
    education_requirements = db.Column(db.Text, nullable=True)  # JSON string of education
    analysis_data = db.Column(db.Text, nullable=True)  # JSON string of full analysis
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    def __repr__(self):
        return f'<JobAnalysis {self.job_id}>'

class JobMatch(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    job_id = db.Column(db.Integer, db.ForeignKey('job.id'), nullable=False)
    match_score = db.Column(db.Integer, nullable=False)
    skills_match = db.Column(db.Text, nullable=True)  # JSON string of matching skills
    missing_skills = db.Column(db.Text, nullable=True)  # JSON string of missing skills
    experience_match = db.Column(db.Text, nullable=True)  # JSON string of experience match
    education_match = db.Column(db.Text, nullable=True)  # JSON string of education match
    match_details = db.Column(db.Text, nullable=True)  # JSON string of full match details
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    def __repr__(self):
        return f'<JobMatch {self.user_id} - {self.job_id}: {self.match_score}%>'

class JobApplication(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    job_id = db.Column(db.Integer, db.ForeignKey('job.id'), nullable=False)
    linkedin_application_id = db.Column(db.String(100), nullable=True)
    status = db.Column(db.String(50), default='pending')  # pending, submitted, viewed, responded, rejected
    applied_at = db.Column(db.DateTime, default=datetime.utcnow)
    response_at = db.Column(db.DateTime, nullable=True)
    notes = db.Column(db.Text, nullable=True)
    
    def __repr__(self):
        return f'<JobApplication {self.user_id} - {self.job_id}>'

class DailySummary(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    date = db.Column(db.Date, nullable=False)
    jobs_analyzed = db.Column(db.Integer, default=0)
    excellent_matches = db.Column(db.Integer, default=0)
    good_matches = db.Column(db.Integer, default=0)
    fair_matches = db.Column(db.Integer, default=0)
    poor_matches = db.Column(db.Integer, default=0)
    applications_submitted = db.Column(db.Integer, default=0)
    summary_data = db.Column(db.Text, nullable=True)  # JSON string of full summary
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    def __repr__(self):
        return f'<DailySummary {self.user_id} - {self.date}>'

class ApiCallLog(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True)
    endpoint = db.Column(db.String(200), nullable=False)
    method = db.Column(db.String(10), nullable=False)
    status_code = db.Column(db.Integer, nullable=True)
    response_time = db.Column(db.Float, nullable=True)  # in seconds
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    def __repr__(self):
        return f'<ApiCallLog {self.endpoint} - {self.status_code}>'
