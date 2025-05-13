from app import db, login_manager, bcrypt
from flask_login import UserMixin
from datetime import datetime
import pyotp
import os

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

class UserType(db.Model):
    __tablename__ = 'user_types'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), unique=True, nullable=False)
    description = db.Column(db.String(200))
    
    # Relationships
    users = db.relationship('User', backref='user_type', lazy='dynamic')
    
    def __repr__(self):
        return f'<UserType {self.name}>'

class User(UserMixin, db.Model):
    __tablename__ = 'users'
    
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(64), unique=True, nullable=False, index=True)
    email = db.Column(db.String(120), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(128), nullable=False)
    first_name = db.Column(db.String(64))
    last_name = db.Column(db.String(64))
    user_type_id = db.Column(db.Integer, db.ForeignKey('user_types.id'), nullable=False)
    is_active = db.Column(db.Boolean, default=True)
    is_admin = db.Column(db.Boolean, default=False)
    two_factor_secret = db.Column(db.String(32))
    two_factor_enabled = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    last_login = db.Column(db.DateTime)
    
    # Relationships
    accounts = db.relationship('Account', backref='owner', lazy='dynamic')
    audit_trails = db.relationship('AuditTrail', backref='user', lazy='dynamic')
    
    def __init__(self, **kwargs):
        super(User, self).__init__(**kwargs)
        if self.two_factor_secret is None:
            self.two_factor_secret = pyotp.random_base32()
    
    def set_password(self, password):
        self.password_hash = bcrypt.generate_password_hash(password).decode('utf-8')
    
    def check_password(self, password):
        return bcrypt.check_password_hash(self.password_hash, password)
    
    def get_totp_uri(self):
        return pyotp.totp.TOTP(self.two_factor_secret).provisioning_uri(
            name=self.email,
            issuer_name="MTS Tax System"
        )
    
    def verify_totp(self, token):
        totp = pyotp.TOTP(self.two_factor_secret)
        return totp.verify(token)
    
    @property
    def full_name(self):
        return f"{self.first_name} {self.last_name}" if self.first_name and self.last_name else self.username
    
    def __repr__(self):
        return f'<User {self.username}>'

class Account(db.Model):
    __tablename__ = 'accounts'
    
    id = db.Column(db.Integer, primary_key=True)
    account_number = db.Column(db.String(20), unique=True, nullable=False)
    name = db.Column(db.String(100), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    tax_obligations = db.relationship('TaxObligation', backref='account', lazy='dynamic')
    tax_returns = db.relationship('TaxReturn', backref='account', lazy='dynamic')
    
    def __repr__(self):
        return f'<Account {self.account_number}>'

class AuditTrail(db.Model):
    __tablename__ = 'audit_trails'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    action = db.Column(db.String(100), nullable=False)
    entity_type = db.Column(db.String(50))
    entity_id = db.Column(db.Integer)
    action_timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    ip_address = db.Column(db.String(50))
    details = db.Column(db.Text)
    
    def __repr__(self):
        return f'<AuditTrail {self.id} by {self.user_id}>'