from flask import Flask, render_template, request, redirect, url_for, flash, jsonify, session
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
import os
import sys
import json
import requests
from datetime import datetime, timedelta
import secrets

# Add the parent directory to sys.path
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

# Initialize Flask app
app = Flask(__name__)
app.config['SECRET_KEY'] = secrets.token_hex(16)

# Configure database
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///linkedin_jobs.db'

app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Initialize database
db = SQLAlchemy(app)

# Import routes after app initialization to avoid circular imports
from src.routes.auth import auth_bp
from src.routes.dashboard import dashboard_bp
from src.routes.wizard import wizard_bp
from src.routes.jobs import jobs_bp
from src.routes.settings import settings_bp

# Register blueprints
app.register_blueprint(auth_bp)
app.register_blueprint(dashboard_bp)
app.register_blueprint(wizard_bp)
app.register_blueprint(jobs_bp)
app.register_blueprint(settings_bp)

# LinkedIn API configuration
LINKEDIN_CLIENT_ID = os.getenv('LINKEDIN_CLIENT_ID', '')
LINKEDIN_CLIENT_SECRET = os.getenv('LINKEDIN_CLIENT_SECRET', '')
LINKEDIN_REDIRECT_URI = os.getenv('LINKEDIN_REDIRECT_URI', 'http://localhost:5000/linkedin/callback')

# Grok-3 API configuration
GROK3_API_KEY = os.getenv('GROK3_API_KEY', '')

# Default route
@app.route('/')
def index():
    if 'user_id' in session:
        return redirect(url_for('dashboard.index'))
    return redirect(url_for('auth.login'))

# Error handlers
@app.errorhandler(404)
def page_not_found(e):
    return render_template('404.html'), 404

@app.errorhandler(500)
def internal_server_error(e):
    return render_template('500.html'), 500

# Context processor for template variables
@app.context_processor
def utility_processor():
    def is_active(route):
        return request.path.startswith(route)
    
    return dict(is_active=is_active)

# Initialize database tables
with app.app_context():
    db.create_all()

if __name__ == '__main__':
    app.run(host='0.0.0.0', debug=True)
