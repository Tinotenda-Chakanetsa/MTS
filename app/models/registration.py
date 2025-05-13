from app import db
from datetime import datetime
from app.models.process import Property

class Registration(db.Model):
    __tablename__ = 'registrations'
    
    id = db.Column(db.Integer, primary_key=True)
    registration_type = db.Column(db.String(50), nullable=False)  # Individual, Non-Individual, Sole Proprietor
    registration_number = db.Column(db.String(50), unique=True, nullable=False)
    status = db.Column(db.String(20), default='Active')  # Active, Suspended, Cancelled, Pending
    registered_date = db.Column(db.Date, nullable=False)
    expiry_date = db.Column(db.Date)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    account_id = db.Column(db.Integer, db.ForeignKey('accounts.id'), nullable=False)
    account = db.relationship('Account')
    
    # Polymorphic identity
    registration_subtype = db.Column(db.String(50))
    __mapper_args__ = {
        'polymorphic_on': registration_subtype,
        'polymorphic_identity': 'registration'
    }
    
    def __repr__(self):
        return f'<Registration {self.registration_number}>'

class IndividualRegistration(Registration):
    __tablename__ = 'individual_registrations'
    
    id = db.Column(db.Integer, db.ForeignKey('registrations.id'), primary_key=True)
    person_id = db.Column(db.Integer, db.ForeignKey('persons.id'), nullable=False)
    occupation = db.Column(db.String(100))
    employment_status = db.Column(db.String(50))  # Employed, Self-Employed, Unemployed, Retired
    tax_residency = db.Column(db.String(50))
    
    # Relationships
    person = db.relationship('Person')
    
    __mapper_args__ = {
        'polymorphic_identity': 'individual'
    }
    
    def __repr__(self):
        return f'<IndividualRegistration {self.registration_number}>'

class NonIndividualRegistration(Registration):
    __tablename__ = 'non_individual_registrations'
    
    id = db.Column(db.Integer, db.ForeignKey('registrations.id'), primary_key=True)
    organization_id = db.Column(db.Integer, db.ForeignKey('organizations.id'), nullable=False)
    business_type = db.Column(db.String(50))  # Corporation, Partnership, LLC, Trust, NGO
    industry_sector = db.Column(db.String(100))
    annual_turnover = db.Column(db.Numeric(14, 2))
    number_of_employees = db.Column(db.Integer)
    
    # Relationships
    organization = db.relationship('Organization')
    
    __mapper_args__ = {
        'polymorphic_identity': 'non_individual'
    }
    
    def __repr__(self):
        return f'<NonIndividualRegistration {self.registration_number}>'

class SoleProprietorRegistration(Registration):
    __tablename__ = 'sole_proprietor_registrations'
    
    id = db.Column(db.Integer, db.ForeignKey('registrations.id'), primary_key=True)
    person_id = db.Column(db.Integer, db.ForeignKey('persons.id'), nullable=False)
    business_name = db.Column(db.String(200), nullable=False)
    business_address = db.Column(db.String(200))
    industry_sector = db.Column(db.String(100))
    annual_turnover = db.Column(db.Numeric(14, 2))
    
    # Relationships
    person = db.relationship('Person')
    
    __mapper_args__ = {
        'polymorphic_identity': 'sole_proprietor'
    }
    
    def __repr__(self):
        return f'<SoleProprietorRegistration {self.registration_number}>'

class PropertyRegistration(db.Model):
    __tablename__ = 'property_registrations'
    
    id = db.Column(db.Integer, primary_key=True)
    property_id = db.Column(db.Integer, db.ForeignKey('properties.id'), nullable=False)
    registration_number = db.Column(db.String(50), unique=True, nullable=False)
    status = db.Column(db.String(20), default='Active')  # Active, Suspended, Transferred
    registered_date = db.Column(db.Date, nullable=False)
    ownership_type = db.Column(db.String(50))  # Sole, Joint, Trust, Corporate
    assessed_value = db.Column(db.Numeric(14, 2))
    tax_zone = db.Column(db.String(50))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # Link to the Property record
    property = db.relationship('Property', backref='registrations')

    # Relationships
    # property relationship can be defined here if needed, but ensure it matches the canonical Property model

    def __repr__(self):
        return f'<PropertyRegistration {self.registration_number}>'

class TaxpayerLedger(db.Model):
    __tablename__ = 'taxpayer_ledgers'
    
    id = db.Column(db.Integer, primary_key=True)
    account_id = db.Column(db.Integer, db.ForeignKey('accounts.id'), nullable=False)
    tax_type_id = db.Column(db.Integer, db.ForeignKey('tax_types.id'), nullable=False)
    tax_period_id = db.Column(db.Integer, db.ForeignKey('tax_periods.id'))
    transaction_date = db.Column(db.Date, nullable=False)
    transaction_type = db.Column(db.String(50), nullable=False)  # Assessment, Payment, Adjustment, Penalty
    description = db.Column(db.String(200))
    debit_amount = db.Column(db.Numeric(14, 2), default=0)
    credit_amount = db.Column(db.Numeric(14, 2), default=0)
    balance = db.Column(db.Numeric(14, 2), nullable=False)
    reference_number = db.Column(db.String(50))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    account = db.relationship('Account')
    tax_type = db.relationship('TaxType')
    tax_period = db.relationship('TaxPeriod')
    
    def __repr__(self):
        return f'<TaxpayerLedger {self.id}>'

class AuditCase(db.Model):
    __tablename__ = 'audit_cases'
    
    id = db.Column(db.Integer, primary_key=True)
    account_id = db.Column(db.Integer, db.ForeignKey('accounts.id'), nullable=False)
    audit_id = db.Column(db.Integer, db.ForeignKey('audits.id'), nullable=False)
    case_number = db.Column(db.String(50), unique=True, nullable=False)
    status = db.Column(db.String(20), default='Open')  # Open, In Progress, Closed
    open_date = db.Column(db.Date, nullable=False)
    close_date = db.Column(db.Date)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    account = db.relationship('Account')
    audit = db.relationship('Audit')
    
    def __repr__(self):
        return f'<AuditCase {self.case_number}>'

class ObjectionRegistration(db.Model):
    __tablename__ = 'objection_registrations'
    
    id = db.Column(db.Integer, primary_key=True)
    objection_id = db.Column(db.Integer, db.ForeignKey('objections.id'), nullable=False)
    registration_number = db.Column(db.String(50), unique=True, nullable=False)
    status = db.Column(db.String(20), default='Registered')  # Registered, Under Review, Decided
    registered_date = db.Column(db.Date, nullable=False)
    decision_date = db.Column(db.Date)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    objection = db.relationship('Objection')
    
    def __repr__(self):
        return f'<ObjectionRegistration {self.registration_number}>'

class PaymentRegistration(db.Model):
    __tablename__ = 'payment_registrations'
    
    id = db.Column(db.Integer, primary_key=True)
    payment_id = db.Column(db.Integer, db.ForeignKey('payments.id'), nullable=False)
    registration_number = db.Column(db.String(50), unique=True, nullable=False)
    status = db.Column(db.String(20), default='Registered')  # Registered, Verified, Rejected
    registered_date = db.Column(db.Date, nullable=False)
    verification_date = db.Column(db.Date)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    payment = db.relationship('Payment')
    
    def __repr__(self):
        return f'<PaymentRegistration {self.registration_number}>'

class RefundRegistration(db.Model):
    __tablename__ = 'refund_registrations'
    
    id = db.Column(db.Integer, primary_key=True)
    refund_id = db.Column(db.Integer, db.ForeignKey('refunds.id'), nullable=False)
    registration_number = db.Column(db.String(50), unique=True, nullable=False)
    status = db.Column(db.String(20), default='Registered')  # Registered, Processed, Rejected
    registered_date = db.Column(db.Date, nullable=False)
    processing_date = db.Column(db.Date)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    refund = db.relationship('Refund')
    
    def __repr__(self):
        return f'<RefundRegistration {self.registration_number}>'