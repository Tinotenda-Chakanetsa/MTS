from app import db
from datetime import datetime
import json

class Person(db.Model):
    __tablename__ = 'persons'
    
    id = db.Column(db.Integer, primary_key=True)
    first_name = db.Column(db.String(64), nullable=False)
    last_name = db.Column(db.String(64), nullable=False)
    middle_name = db.Column(db.String(64))
    date_of_birth = db.Column(db.Date)
    gender = db.Column(db.String(10))
    national_id = db.Column(db.String(20), unique=True)
    passport_number = db.Column(db.String(20), unique=True)
    phone = db.Column(db.String(20))
    email = db.Column(db.String(120))
    address = db.Column(db.String(200))
    city = db.Column(db.String(100))
    state = db.Column(db.String(100))
    country = db.Column(db.String(100))
    postal_code = db.Column(db.String(20))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    accounts = db.relationship('AccountHolder', backref='person', lazy='dynamic')
    
    @property
    def full_name(self):
        return f"{self.first_name} {self.middle_name or ''} {self.last_name}".strip()
    
    def __repr__(self):
        return f'<Person {self.full_name}>'

class Organization(db.Model):
    __tablename__ = 'organizations'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(200), nullable=False)
    registration_number = db.Column(db.String(50), unique=True, nullable=False)
    organization_type = db.Column(db.String(50))  # Company, Partnership, NGO, etc.
    tax_identifier = db.Column(db.String(50), unique=True)
    incorporation_date = db.Column(db.Date)
    phone = db.Column(db.String(20))
    email = db.Column(db.String(120))
    website = db.Column(db.String(200))
    address = db.Column(db.String(200))
    city = db.Column(db.String(100))
    state = db.Column(db.String(100))
    country = db.Column(db.String(100))
    postal_code = db.Column(db.String(20))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    accounts = db.relationship('AccountHolder', backref='organization', lazy='dynamic')
    
    def __repr__(self):
        return f'<Organization {self.name}>'

class AccountHolder(db.Model):
    __tablename__ = 'account_holders'
    
    id = db.Column(db.Integer, primary_key=True)
    account_id = db.Column(db.Integer, db.ForeignKey('accounts.id'), nullable=False)
    person_id = db.Column(db.Integer, db.ForeignKey('persons.id'))
    organization_id = db.Column(db.Integer, db.ForeignKey('organizations.id'))
    holder_type = db.Column(db.String(20), nullable=False)  # Primary, Secondary, Representative
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    account = db.relationship('Account')
    
    def __repr__(self):
        return f'<AccountHolder {self.id}>'

class Property(db.Model):
    __tablename__ = 'properties'
    
    id = db.Column(db.Integer, primary_key=True)
    account_id = db.Column(db.Integer, db.ForeignKey('accounts.id'), nullable=False)
    property_type = db.Column(db.String(50), nullable=False)  # Land, Building, Vehicle, Equipment, etc.
    property_identifier = db.Column(db.String(50), unique=True, nullable=False)
    owner_name = db.Column(db.String(120), nullable=False)  # Owner as entered in registration
    description = db.Column(db.Text)
    address = db.Column(db.String(200))
    city = db.Column(db.String(100))
    state = db.Column(db.String(100))
    country = db.Column(db.String(100))
    postal_code = db.Column(db.String(20))
    acquisition_date = db.Column(db.Date)
    acquisition_value = db.Column(db.Numeric(14, 2))
    current_value = db.Column(db.Numeric(14, 2))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    account = db.relationship('Account')
    
    def __repr__(self):
        return f'<Property {self.property_identifier}>'

class Request(db.Model):
    __tablename__ = 'requests'
    
    id = db.Column(db.Integer, primary_key=True)
    request_type = db.Column(db.String(50), nullable=False)  # Registration, Amendment, Certificate, etc.
    account_id = db.Column(db.Integer, db.ForeignKey('accounts.id'), nullable=False)
    submitted_by = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    status = db.Column(db.String(20), default='Pending')  # Pending, In Progress, Completed, Rejected
    submission_date = db.Column(db.DateTime, default=datetime.utcnow)
    completion_date = db.Column(db.DateTime)
    reference_number = db.Column(db.String(50), unique=True)
    details = db.Column(db.Text)
    
    # Relationships
    account = db.relationship('Account')
    user = db.relationship('User')
    
    def __repr__(self):
        return f'<Request {self.reference_number}>'

class Audit(db.Model):
    __tablename__ = 'audits'
    
    id = db.Column(db.Integer, primary_key=True)
    account_id = db.Column(db.Integer, db.ForeignKey('accounts.id'), nullable=False)
    tax_type_id = db.Column(db.Integer, db.ForeignKey('tax_types.id'), nullable=False)
    audit_type = db.Column(db.String(50), nullable=False)  # Desk, Field, Comprehensive
    start_date = db.Column(db.Date, nullable=False)
    end_date = db.Column(db.Date)
    status = db.Column(db.String(20), default='Planned')  # Planned, In Progress, Completed, Cancelled
    auditor_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    findings = db.Column(db.Text)
    additional_assessment = db.Column(db.Numeric(14, 2), default=0)  # Total additional assessment amount
    outcome = db.Column(db.String(50))  # Audit outcome (e.g., Pass, Fail, Partial)
    reference_number = db.Column(db.String(50), unique=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    account = db.relationship('Account')
    tax_type = db.relationship('TaxType')
    auditor = db.relationship('User')
    
    def __repr__(self):
        return f'<Audit {self.reference_number}>'

class Collection(db.Model):
    __tablename__ = 'collections'
    
    id = db.Column(db.Integer, primary_key=True)
    account_id = db.Column(db.Integer, db.ForeignKey('accounts.id'), nullable=False)
    tax_return_id = db.Column(db.Integer, db.ForeignKey('tax_returns.id'))
    amount_due = db.Column(db.Numeric(14, 2), nullable=False)
    collection_type = db.Column(db.String(50), nullable=False)  # Regular, Enforcement, Installment
    start_date = db.Column(db.Date, nullable=False)
    due_date = db.Column(db.Date, nullable=False)
    status = db.Column(db.String(20), default='Pending')  # Pending, Partial, Complete, Written Off
    reference_number = db.Column(db.String(50), unique=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    account = db.relationship('Account')
    tax_return = db.relationship('TaxReturn')
    payments = db.relationship('Payment', backref='collection', lazy='dynamic',
                              primaryjoin="Collection.id==Payment.collection_id")
    
    def __repr__(self):
        return f'<Collection {self.reference_number}>'

class Enforcement(db.Model):
    __tablename__ = 'enforcements'
    
    id = db.Column(db.Integer, primary_key=True)
    collection_id = db.Column(db.Integer, db.ForeignKey('collections.id'), nullable=False)
    enforcement_type = db.Column(db.String(50), nullable=False)  # Garnishment, Lien, Seizure, etc.
    start_date = db.Column(db.Date, nullable=False)
    end_date = db.Column(db.Date)
    status = db.Column(db.String(20), default='Initiated')  # Initiated, In Progress, Completed, Cancelled
    enforcer_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    details = db.Column(db.Text)
    reference_number = db.Column(db.String(50), unique=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    collection = db.relationship('Collection')
    enforcer = db.relationship('User')
    
    def __repr__(self):
        return f'<Enforcement {self.reference_number}>'

class Agreement(db.Model):
    __tablename__ = 'agreements'
    
    id = db.Column(db.Integer, primary_key=True)
    account_id = db.Column(db.Integer, db.ForeignKey('accounts.id'), nullable=False)
    agreement_type = db.Column(db.String(50), nullable=False)  # Payment Plan, Settlement, Amnesty
    start_date = db.Column(db.Date, nullable=False)
    end_date = db.Column(db.Date, nullable=False)
    status = db.Column(db.String(20), default='Active')  # Active, Completed, Breached, Cancelled
    terms = db.Column(db.Text, nullable=False)
    approved_by = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    reference_number = db.Column(db.String(50), unique=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    account = db.relationship('Account')
    approver = db.relationship('User')
    
    def __repr__(self):
        return f'<Agreement {self.reference_number}>'

class RiskAssessment(db.Model):
    __tablename__ = 'risk_assessments'
    
    id = db.Column(db.Integer, primary_key=True)
    account_id = db.Column(db.Integer, db.ForeignKey('accounts.id'), nullable=False)
    assessment_date = db.Column(db.Date, nullable=False)
    risk_level = db.Column(db.String(10), nullable=False)  # Low, Medium, High
    risk_factors = db.Column(db.Text)
    assessor_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    next_assessment_date = db.Column(db.Date)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    account = db.relationship('Account')
    assessor = db.relationship('User')
    
    def __repr__(self):
        return f'<RiskAssessment {self.id}>'