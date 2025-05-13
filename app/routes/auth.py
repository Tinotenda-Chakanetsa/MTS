from flask import Blueprint, render_template, redirect, url_for, flash, request, session
from flask_login import login_user, logout_user, login_required, current_user
from app import db, bcrypt
from app.models.user import User, UserType, AuditTrail
from app.services.auth_service import generate_confirmation_token, confirm_token
from datetime import datetime
import pyotp
import qrcode
import io
import base64

auth_bp = Blueprint('auth', __name__, url_prefix='/auth')

@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard.index'))
    
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        remember = True if request.form.get('remember') else False
        
        user = User.query.filter_by(username=username).first()
        
        if user and user.check_password(password):
            if not user.is_active:
                flash('Account is deactivated. Please contact administrator.', 'danger')
                return render_template('auth/login.html')
            
            if user.two_factor_enabled:
                session['user_id'] = user.id
                return redirect(url_for('auth.two_factor_auth'))
            
            login_user(user, remember=remember)
            user.last_login = datetime.utcnow()
            db.session.commit()
            
            # Log the login activity
            audit = AuditTrail(
                user_id=user.id,
                action='Login',
                ip_address=request.remote_addr,
                details='User logged in'
            )
            db.session.add(audit)
            db.session.commit()
            
            next_page = request.args.get('next')
            return redirect(next_page or url_for('dashboard.index'))
        else:
            flash('Invalid username or password', 'danger')
    
    return render_template('auth/login.html')

@auth_bp.route('/two-factor', methods=['GET', 'POST'])
def two_factor_auth():
    if 'user_id' not in session:
        return redirect(url_for('auth.login'))
    
    user = User.query.get(session['user_id'])
    if not user:
        return redirect(url_for('auth.login'))
    
    if request.method == 'POST':
        token = request.form.get('token')
        
        if user.verify_totp(token):
            login_user(user)
            user.last_login = datetime.utcnow()
            db.session.commit()
            
            # Log the login activity
            audit = AuditTrail(
                user_id=user.id,
                action='Login with 2FA',
                ip_address=request.remote_addr,
                details='User logged in with two-factor authentication'
            )
            db.session.add(audit)
            db.session.commit()
            
            session.pop('user_id', None)
            return redirect(url_for('dashboard.index'))
        else:
            flash('Invalid authentication code', 'danger')
    
    return render_template('auth/two_factor.html')

@auth_bp.route('/logout')
@login_required
def logout():
    # Log the logout activity
    audit = AuditTrail(
        user_id=current_user.id,
        action='Logout',
        ip_address=request.remote_addr,
        details='User logged out'
    )
    db.session.add(audit)
    db.session.commit()
    
    logout_user()
    flash('You have been logged out', 'info')
    return redirect(url_for('auth.login'))

@auth_bp.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard.index'))
    
    if request.method == 'POST':
        username = request.form.get('username')
        email = request.form.get('email')
        password = request.form.get('password')
        confirm_password = request.form.get('confirm_password')
        first_name = request.form.get('first_name')
        last_name = request.form.get('last_name')
        user_type = request.form.get('user_type')
        accept_terms = request.form.get('accept_terms')
        
        # Validate form inputs
        error = None
        # Collect all error messages
        errors = []
        if not username:
            errors.append('Username is required')
        if not email:
            errors.append('Email is required')
        if not password:
            errors.append('Password is required')
        if not confirm_password:
            errors.append('Please confirm your password')
        if not first_name:
            errors.append('First name is required')
        if not last_name:
            errors.append('Last name is required')
        if not user_type:
            errors.append('User type is required')
        if password and confirm_password and password != confirm_password:
            errors.append('Passwords do not match')
        if not accept_terms:
            errors.append('You must accept the Terms and Conditions')
        user_exists = User.query.filter((User.username == username) | (User.email == email)).first()
        if user_exists:
            errors.append('Username or email already exists')
        
        if errors:
            for e in errors:
                flash(e, 'danger')
            # Return form data so user doesn't have to retype
            return render_template('auth/register.html',
                error=' '.join(errors),
                username=username,
                email=email,
                first_name=first_name,
                last_name=last_name,
                user_type=user_type
            )
        
        # Get the user type ID based on the selected value
        user_type_name = {
            'individual': 'Individual',
            'non_individual': 'Non-Individual',
            'agent': 'Agent'
        }.get(user_type)
        
        user_type_obj = UserType.query.filter_by(name=user_type_name).first()
        if not user_type_obj:
            return render_template('auth/register.html', error='Invalid user type selected')
        
        # Create and save the new user
        user = User(
            username=username,
            email=email,
            first_name=first_name,
            last_name=last_name,
            user_type_id=user_type_obj.id,
            is_active=True,
            is_admin=False
        )
        user.set_password(password)
        
        db.session.add(user)
        db.session.commit()
        
        # Log the registration activity
        audit = AuditTrail(
            user_id=user.id,
            action='Registration',
            ip_address=request.remote_addr,
            details='User registered'
        )
        db.session.add(audit)
        db.session.commit()
        
        flash('Registration successful! You can now log in.', 'success')
        return redirect(url_for('auth.login'))
    
    return render_template('auth/register.html')

@auth_bp.route('/profile', methods=['GET', 'POST'])
@login_required
def profile():
    if request.method == 'POST':
        current_user.first_name = request.form.get('first_name')
        current_user.last_name = request.form.get('last_name')
        current_user.email = request.form.get('email')
        
        password = request.form.get('password')
        if password:
            current_user.set_password(password)
        
        db.session.commit()
        flash('Profile updated successfully', 'success')
        return redirect(url_for('auth.profile'))
    
    return render_template('auth/profile.html', user=current_user)

@auth_bp.route('/setup-2fa', methods=['GET', 'POST'])
@login_required
def setup_2fa():
    if request.method == 'POST':
        token = request.form.get('token')
        
        if current_user.verify_totp(token):
            current_user.two_factor_enabled = True
            db.session.commit()
            flash('Two-factor authentication has been enabled', 'success')
            return redirect(url_for('auth.profile'))
        else:
            flash('Invalid authentication code', 'danger')
    
    # Generate QR code for the TOTP
    totp_uri = current_user.get_totp_uri()
    qr = qrcode.make(totp_uri)
    buffered = io.BytesIO()
    qr.save(buffered)
    qr_code = base64.b64encode(buffered.getvalue()).decode("utf-8")
    
    return render_template('auth/setup_2fa.html', qr_code=qr_code, secret=current_user.two_factor_secret)

@auth_bp.route('/disable-2fa', methods=['POST'])
@login_required
def disable_2fa():
    current_user.two_factor_enabled = False
    db.session.commit()
    flash('Two-factor authentication has been disabled', 'success')
    return redirect(url_for('auth.profile'))

@auth_bp.route('/reset-password-request', methods=['GET', 'POST'])
def reset_password_request():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard.index'))
    
    if request.method == 'POST':
        email = request.form.get('email')
        user = User.query.filter_by(email=email).first()
        
        if user:
            token = generate_confirmation_token(user.email)
            # Send email with reset link
            # This would be implemented in a real application
            flash('If your email exists in our system, you will receive a password reset link shortly.', 'info')
        else:
            # Don't reveal that the email doesn't exist
            flash('If your email exists in our system, you will receive a password reset link shortly.', 'info')
        
        return redirect(url_for('auth.login'))
    
    return render_template('auth/reset_password_request.html')

@auth_bp.route('/reset-password/<token>', methods=['GET', 'POST'])
def reset_password(token):
    if current_user.is_authenticated:
        return redirect(url_for('dashboard.index'))
    
    try:
        email = confirm_token(token)
    except:
        flash('The password reset link is invalid or has expired.', 'danger')
        return redirect(url_for('auth.reset_password_request'))
    
    user = User.query.filter_by(email=email).first()
    if not user:
        flash('The password reset link is invalid or has expired.', 'danger')
        return redirect(url_for('auth.reset_password_request'))
    
    if request.method == 'POST':
        password = request.form.get('password')
        confirm_password = request.form.get('confirm_password')
        
        if password != confirm_password:
            flash('Passwords do not match', 'danger')
            return render_template('auth/reset_password.html', token=token)
        
        user.set_password(password)
        db.session.commit()
        flash('Your password has been reset. You can now log in with your new password.', 'success')
        return redirect(url_for('auth.login'))
    
    return render_template('auth/reset_password.html', token=token)