from itsdangerous import URLSafeTimedSerializer
from app import bcrypt
from app.config import Config
from app.models.user import User, UserType, AuditTrail
from flask import current_app
from datetime import datetime
import os

def generate_confirmation_token(email):
    """Generate a secure token for email confirmation or password reset"""
    serializer = URLSafeTimedSerializer(current_app.config['SECRET_KEY'])
    return serializer.dumps(email, salt=current_app.config.get('SECURITY_PASSWORD_SALT', 'email-confirm-salt'))

def confirm_token(token, expiration=3600):
    """Confirm a token is valid and not expired"""
    serializer = URLSafeTimedSerializer(current_app.config['SECRET_KEY'])
    try:
        email = serializer.loads(
            token,
            salt=current_app.config.get('SECURITY_PASSWORD_SALT', 'email-confirm-salt'),
            max_age=expiration
        )
        return email
    except:
        return False

def authenticate_user(username, password):
    """Authenticate a user by username and password"""
    user = User.query.filter_by(username=username).first()
    if user and user.check_password(password):
        return user
    return None

def create_user(username, email, password, first_name, last_name, user_type_id, is_admin=False):
    """Create a new user in the system"""
    user = User(
        username=username,
        email=email,
        first_name=first_name,
        last_name=last_name,
        user_type_id=user_type_id,
        is_active=True,
        is_admin=is_admin
    )
    user.set_password(password)
    return user

def change_password(user, new_password):
    """Change a user's password"""
    user.set_password(new_password)
    return user

def log_user_activity(user_id, action, ip_address, details=None, entity_type=None, entity_id=None):
    """Log user activity for audit purposes"""
    audit = AuditTrail(
        user_id=user_id,
        action=action,
        entity_type=entity_type,
        entity_id=entity_id,
        ip_address=ip_address,
        details=details
    )
    return audit

def generate_password_reset_link(user):
    """Generate a password reset link for a user"""
    token = generate_confirmation_token(user.email)
    reset_url = f"/auth/reset-password/{token}"
    return reset_url

def verify_two_factor(user, token):
    """Verify a two-factor authentication token"""
    return user.verify_totp(token)

def enable_two_factor(user):
    """Enable two-factor authentication for a user"""
    user.two_factor_enabled = True
    return user

def disable_two_factor(user):
    """Disable two-factor authentication for a user"""
    user.two_factor_enabled = False
    return user

def get_user_permissions(user):
    """Get permissions for a user based on their type and admin status"""
    permissions = []
    
    # Basic permissions for all authenticated users
    permissions.append('view_profile')
    permissions.append('edit_profile')
    
    # Admin permissions
    if user.is_admin:
        permissions.append('admin_access')
        permissions.append('manage_users')
        permissions.append('view_audit_logs')
        permissions.append('manage_system_settings')
        permissions.append('view_all_accounts')
    
    # User type specific permissions
    if user.user_type.name == 'Individual':
        permissions.append('file_individual_returns')
        permissions.append('view_individual_accounts')
    elif user.user_type.name == 'Non-Individual':
        permissions.append('file_business_returns')
        permissions.append('view_business_accounts')
    elif user.user_type.name == 'Agent':
        permissions.append('file_individual_returns')
        permissions.append('file_business_returns')
        permissions.append('view_individual_accounts')
        permissions.append('view_business_accounts')
        permissions.append('manage_client_accounts')
    elif user.user_type.name == 'Internal':
        permissions.append('process_returns')
        permissions.append('view_all_accounts')
        permissions.append('manage_tax_accounts')
        permissions.append('process_refunds')
        permissions.append('handle_objections')
    elif user.user_type.name == 'Government':
        permissions.append('view_reports')
        permissions.append('view_statistics')
    
    return permissions