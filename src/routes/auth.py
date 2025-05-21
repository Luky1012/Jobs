from flask import Blueprint, request, render_template, redirect, url_for, flash, session
from werkzeug.security import generate_password_hash, check_password_hash
import secrets
from datetime import datetime, timedelta

from src.models.models import User, db

auth_bp = Blueprint('auth', __name__, url_prefix='/auth')

@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        
        user = User.query.filter_by(email=email).first()
        
        if user and check_password_hash(user.password_hash, password):
            if not user.is_verified:
                flash('Please verify your email address before logging in.', 'warning')
                return redirect(url_for('auth.login'))
                
            session['user_id'] = user.id
            session['username'] = user.username
            
            next_page = request.args.get('next')
            if next_page:
                return redirect(next_page)
            return redirect(url_for('dashboard.index'))
        
        flash('Invalid email or password', 'danger')
    
    return render_template('auth/login.html')

@auth_bp.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form.get('username')
        email = request.form.get('email')
        password = request.form.get('password')
        confirm_password = request.form.get('confirm_password')
        
        # Validate input
        if not username or not email or not password:
            flash('All fields are required', 'danger')
            return render_template('auth/register.html')
            
        if password != confirm_password:
            flash('Passwords do not match', 'danger')
            return render_template('auth/register.html')
            
        # Check if user already exists
        existing_user = User.query.filter((User.username == username) | (User.email == email)).first()
        if existing_user:
            flash('Username or email already exists', 'danger')
            return render_template('auth/register.html')
            
        # Create new user
        verification_token = secrets.token_urlsafe(32)
        new_user = User(
            username=username,
            email=email,
            password_hash=generate_password_hash(password),
            verification_token=verification_token,
            is_verified=False
        )
        
        db.session.add(new_user)
        db.session.commit()
        
        # Send verification email (implementation would be added here)
        # send_verification_email(email, verification_token)
        
        flash('Registration successful! Please check your email to verify your account.', 'success')
        return redirect(url_for('auth.login'))
    
    return render_template('auth/register.html')

@auth_bp.route('/verify/<token>')
def verify(token):
    user = User.query.filter_by(verification_token=token).first()
    
    if not user:
        flash('Invalid or expired verification link', 'danger')
        return redirect(url_for('auth.login'))
        
    user.is_verified = True
    user.verification_token = None
    db.session.commit()
    
    flash('Your account has been verified! You can now log in.', 'success')
    return redirect(url_for('auth.login'))

@auth_bp.route('/forgot-password', methods=['GET', 'POST'])
def forgot_password():
    if request.method == 'POST':
        email = request.form.get('email')
        
        user = User.query.filter_by(email=email).first()
        if user:
            # Generate password reset token
            reset_token = secrets.token_urlsafe(32)
            user.verification_token = reset_token
            db.session.commit()
            
            # Send password reset email (implementation would be added here)
            # send_password_reset_email(email, reset_token)
            
        # Always show success message to prevent email enumeration
        flash('If your email is registered, you will receive password reset instructions.', 'info')
        return redirect(url_for('auth.login'))
    
    return render_template('auth/forgot_password.html')

@auth_bp.route('/reset-password/<token>', methods=['GET', 'POST'])
def reset_password(token):
    user = User.query.filter_by(verification_token=token).first()
    
    if not user:
        flash('Invalid or expired reset link', 'danger')
        return redirect(url_for('auth.login'))
        
    if request.method == 'POST':
        password = request.form.get('password')
        confirm_password = request.form.get('confirm_password')
        
        if password != confirm_password:
            flash('Passwords do not match', 'danger')
            return render_template('auth/reset_password.html', token=token)
            
        user.password_hash = generate_password_hash(password)
        user.verification_token = None
        db.session.commit()
        
        flash('Your password has been reset! You can now log in with your new password.', 'success')
        return redirect(url_for('auth.login'))
    
    return render_template('auth/reset_password.html', token=token)

@auth_bp.route('/logout')
def logout():
    session.pop('user_id', None)
    session.pop('username', None)
    flash('You have been logged out', 'info')
    return redirect(url_for('auth.login'))
