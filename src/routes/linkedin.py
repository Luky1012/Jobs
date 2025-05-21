from flask import Blueprint, request, render_template, redirect, url_for, flash, session, jsonify
import requests
import json
import os
from datetime import datetime, timedelta
import secrets

from src.models.models import User, LinkedInProfile, db

# LinkedIn API configuration
LINKEDIN_CLIENT_ID = os.getenv('LINKEDIN_CLIENT_ID', '')
LINKEDIN_CLIENT_SECRET = os.getenv('LINKEDIN_CLIENT_SECRET', '')
LINKEDIN_REDIRECT_URI = os.getenv('LINKEDIN_REDIRECT_URI', 'http://localhost:5000/linkedin/callback')

linkedin_bp = Blueprint('linkedin', __name__, url_prefix='/linkedin')

@linkedin_bp.route('/authorize')
def authorize():
    """Redirect user to LinkedIn authorization page"""
    if 'user_id' not in session:
        flash('Please log in first', 'warning')
        return redirect(url_for('auth.login'))
    
    # Generate state parameter to prevent CSRF
    state = secrets.token_hex(16)
    session['linkedin_state'] = state
    
    # LinkedIn OAuth 2.0 authorization URL
    auth_url = f"https://www.linkedin.com/oauth/v2/authorization"
    params = {
        'response_type': 'code',
        'client_id': LINKEDIN_CLIENT_ID,
        'redirect_uri': LINKEDIN_REDIRECT_URI,
        'state': state,
        'scope': 'r_liteprofile r_emailaddress w_member_social r_fullprofile'
    }
    
    # Build the authorization URL with parameters
    auth_url += '?' + '&'.join([f"{key}={params[key]}" for key in params])
    
    return redirect(auth_url)

@linkedin_bp.route('/callback')
def callback():
    """Handle LinkedIn OAuth callback"""
    if 'user_id' not in session:
        flash('Please log in first', 'warning')
        return redirect(url_for('auth.login'))
    
    # Verify state parameter to prevent CSRF
    state = request.args.get('state')
    if state != session.get('linkedin_state'):
        flash('Invalid state parameter', 'danger')
        return redirect(url_for('dashboard.index'))
    
    # Clear state from session
    session.pop('linkedin_state', None)
    
    # Get authorization code
    code = request.args.get('code')
    if not code:
        flash('Authorization failed', 'danger')
        return redirect(url_for('dashboard.index'))
    
    # Exchange authorization code for access token
    token_url = 'https://www.linkedin.com/oauth/v2/accessToken'
    token_data = {
        'grant_type': 'authorization_code',
        'code': code,
        'redirect_uri': LINKEDIN_REDIRECT_URI,
        'client_id': LINKEDIN_CLIENT_ID,
        'client_secret': LINKEDIN_CLIENT_SECRET
    }
    
    token_response = requests.post(token_url, data=token_data)
    
    if token_response.status_code != 200:
        flash('Failed to obtain access token', 'danger')
        return redirect(url_for('dashboard.index'))
    
    token_json = token_response.json()
    access_token = token_json.get('access_token')
    expires_in = token_json.get('expires_in', 3600)  # Default to 1 hour
    refresh_token = token_json.get('refresh_token')
    
    # Get LinkedIn profile data
    profile_data = get_linkedin_profile(access_token)
    
    if not profile_data:
        flash('Failed to retrieve LinkedIn profile', 'danger')
        return redirect(url_for('dashboard.index'))
    
    # Save LinkedIn profile data to database
    user_id = session['user_id']
    linkedin_id = profile_data.get('id')
    
    # Check if LinkedIn profile already exists for this user
    linkedin_profile = LinkedInProfile.query.filter_by(user_id=user_id).first()
    
    if linkedin_profile:
        # Update existing profile
        linkedin_profile.linkedin_id = linkedin_id
        linkedin_profile.access_token = access_token
        linkedin_profile.refresh_token = refresh_token
        linkedin_profile.token_expiry = datetime.utcnow() + timedelta(seconds=expires_in)
        linkedin_profile.profile_data = json.dumps(profile_data)
        linkedin_profile.last_updated = datetime.utcnow()
    else:
        # Create new profile
        linkedin_profile = LinkedInProfile(
            user_id=user_id,
            linkedin_id=linkedin_id,
            access_token=access_token,
            refresh_token=refresh_token,
            token_expiry=datetime.utcnow() + timedelta(seconds=expires_in),
            profile_data=json.dumps(profile_data),
            last_updated=datetime.utcnow()
        )
        db.session.add(linkedin_profile)
    
    db.session.commit()
    
    flash('LinkedIn account connected successfully', 'success')
    
    # Redirect to the next step in the wizard
    return redirect(url_for('wizard.profile_analysis'))

@linkedin_bp.route('/disconnect')
def disconnect():
    """Disconnect LinkedIn account"""
    if 'user_id' not in session:
        flash('Please log in first', 'warning')
        return redirect(url_for('auth.login'))
    
    user_id = session['user_id']
    linkedin_profile = LinkedInProfile.query.filter_by(user_id=user_id).first()
    
    if linkedin_profile:
        db.session.delete(linkedin_profile)
        db.session.commit()
        flash('LinkedIn account disconnected', 'success')
    else:
        flash('No LinkedIn account connected', 'info')
    
    return redirect(url_for('settings.index'))

def get_linkedin_profile(access_token):
    """Get LinkedIn profile data using access token"""
    headers = {
        'Authorization': f'Bearer {access_token}',
        'X-Restli-Protocol-Version': '2.0.0'
    }
    
    # Get basic profile data
    profile_url = 'https://api.linkedin.com/v2/me'
    profile_response = requests.get(profile_url, headers=headers)
    
    if profile_response.status_code != 200:
        return None
    
    profile_data = profile_response.json()
    
    # Get email address
    email_url = 'https://api.linkedin.com/v2/emailAddress?q=members&projection=(elements*(handle~))'
    email_response = requests.get(email_url, headers=headers)
    
    if email_response.status_code == 200:
        email_data = email_response.json()
        if 'elements' in email_data and len(email_data['elements']) > 0:
            email = email_data['elements'][0].get('handle~', {}).get('emailAddress')
            profile_data['email'] = email
    
    return profile_data

def refresh_linkedin_token(refresh_token):
    """Refresh LinkedIn access token"""
    token_url = 'https://www.linkedin.com/oauth/v2/accessToken'
    token_data = {
        'grant_type': 'refresh_token',
        'refresh_token': refresh_token,
        'client_id': LINKEDIN_CLIENT_ID,
        'client_secret': LINKEDIN_CLIENT_SECRET
    }
    
    token_response = requests.post(token_url, data=token_data)
    
    if token_response.status_code != 200:
        return None
    
    return token_response.json()

def get_linkedin_skills(access_token, linkedin_id):
    """Get LinkedIn skills data"""
    headers = {
        'Authorization': f'Bearer {access_token}',
        'X-Restli-Protocol-Version': '2.0.0'
    }
    
    skills_url = f'https://api.linkedin.com/v2/skillsV2?q=members&members=List({linkedin_id})'
    skills_response = requests.get(skills_url, headers=headers)
    
    if skills_response.status_code != 200:
        return None
    
    return skills_response.json()

def get_linkedin_experience(access_token, linkedin_id):
    """Get LinkedIn experience data"""
    headers = {
        'Authorization': f'Bearer {access_token}',
        'X-Restli-Protocol-Version': '2.0.0'
    }
    
    experience_url = f'https://api.linkedin.com/v2/positions?q=members&members=List({linkedin_id})'
    experience_response = requests.get(experience_url, headers=headers)
    
    if experience_response.status_code != 200:
        return None
    
    return experience_response.json()

def get_linkedin_education(access_token, linkedin_id):
    """Get LinkedIn education data"""
    headers = {
        'Authorization': f'Bearer {access_token}',
        'X-Restli-Protocol-Version': '2.0.0'
    }
    
    education_url = f'https://api.linkedin.com/v2/educations?q=members&members=List({linkedin_id})'
    education_response = requests.get(education_url, headers=headers)
    
    if education_response.status_code != 200:
        return None
    
    return education_response.json()
