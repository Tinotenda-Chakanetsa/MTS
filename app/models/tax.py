from app import db
from datetime import datetime

class TaxType(db.Model):
    __tablename__ = 'tax_types'
    
    id = db.Column(db.Integer, primary_key=True)
    code = db.Column(db.String(20), unique=True, nullable=False)
    name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text)
    is_core = db.Column(db.Boolean, default=True)  # Core or Non-core tax
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    obligations = db.relationship('TaxObligation', backref='tax_type', lazy='dynamic')
    returns = db.relationship('TaxReturn', backref='tax_type', lazy='dynamic')
    
    def __repr__(self):
        return f'<TaxType {self.code}>'

class TaxPeriod(db.Model):
    __tablename__ = 'tax_periods'
    
    id = db.Column(db.Integer, primary_key=True)
    tax_type_id = db.Column(db.Integer, db.ForeignKey('tax_types.id'), nullable=False)
    start_date = db.Column(db.Date, nullable=False)
    end_date = db.Column(db.Date, nullable=False)
    due_date = db.Column(db.Date, nullable=False)
    period_code = db.Column(db.String(20), nullable=False)
    status = db.Column(db.String(20), default='Open')  # Open, Closed, Extended
    
    # Relationships
    tax_type = db.relationship('TaxType')
    returns = db.relationship('TaxReturn', backref='period', lazy='dynamic')
    
    def __repr__(self):
        return f'<TaxPeriod {self.period_code}>'

class TaxObligation(db.Model):
    __tablename__ = 'tax_obligations'
    
    id = db.Column(db.Integer, primary_key=True)
    account_id = db.Column(db.Integer, db.ForeignKey('accounts.id'), nullable=False)
    tax_type_id = db.Column(db.Integer, db.ForeignKey('tax_types.id'), nullable=False)
    start_date = db.Column(db.Date, nullable=False)
    end_date = db.Column(db.Date)  # Null means ongoing
    status = db.Column(db.String(20), default='Active')  # Active, Inactive, Suspended
    registration_date = db.Column(db.Date, nullable=False)
    
    def __repr__(self):
        return f'<TaxObligation {self.id}>'

class TaxReturn(db.Model):
    __tablename__ = 'tax_returns'
    
    id = db.Column(db.Integer, primary_key=True)
    account_id = db.Column(db.Integer, db.ForeignKey('accounts.id'), nullable=False)
    tax_type_id = db.Column(db.Integer, db.ForeignKey('tax_types.id'), nullable=False)
    tax_period_id = db.Column(db.Integer, db.ForeignKey('tax_periods.id'), nullable=False)
    filing_date = db.Column(db.DateTime)
    due_amount = db.Column(db.Numeric(14, 2))
    status = db.Column(db.String(20), default='Not Filed')  # Not Filed, Filed, Assessed, Finalized
    assessment_date = db.Column(db.DateTime)
    assessment_type = db.Column(db.String(20))  # Self, Official, Estimated
    reference_number = db.Column(db.String(20), unique=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # --- Flagging fields ---
    is_flagged = db.Column(db.Boolean, default=False, nullable=False)
    flag_reason = db.Column(db.Text)
    # --- End flagging fields ---
    
    # Relationships
    payments = db.relationship('Payment', backref='tax_return', lazy='dynamic')
    objections = db.relationship('Objection', backref='tax_return', lazy='dynamic')
    
    def __repr__(self):
        return f'<TaxReturn {self.reference_number}>'

class Payment(db.Model):
    __tablename__ = 'payments'
    
    id = db.Column(db.Integer, primary_key=True)
    tax_return_id = db.Column(db.Integer, db.ForeignKey('tax_returns.id'), nullable=False)
    collection_id = db.Column(db.Integer, db.ForeignKey('collections.id'))
    amount = db.Column(db.Numeric(14, 2), nullable=False)
    payment_date = db.Column(db.DateTime, nullable=False)
    payment_method = db.Column(db.String(20), nullable=False)  # Bank, Cash, Online
    reference_number = db.Column(db.String(50), unique=True)
    status = db.Column(db.String(20), default='Pending')  # Pending, Completed, Failed, Refunded
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    def __repr__(self):
        return f'<Payment {self.reference_number}>'

class Refund(db.Model):
    __tablename__ = 'refunds'
    
    id = db.Column(db.Integer, primary_key=True)
    account_id = db.Column(db.Integer, db.ForeignKey('accounts.id'), nullable=False)
    amount = db.Column(db.Numeric(14, 2), nullable=False)
    request_date = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    reason = db.Column(db.Text, nullable=False)
    status = db.Column(db.String(20), default='Pending')  # Pending, Approved, Rejected, Paid
    approval_date = db.Column(db.DateTime)
    payment_date = db.Column(db.DateTime)
    reference_number = db.Column(db.String(50), unique=True)
    
    def __repr__(self):
        return f'<Refund {self.reference_number}>'

class Objection(db.Model):
    __tablename__ = 'objections'
    
    id = db.Column(db.Integer, primary_key=True)
    tax_return_id = db.Column(db.Integer, db.ForeignKey('tax_returns.id'), nullable=False)
    filing_date = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    reason = db.Column(db.Text, nullable=False)
    status = db.Column(db.String(20), default='Pending')  # Pending, In Progress, Resolved, Rejected
    decision_date = db.Column(db.DateTime)
    decision = db.Column(db.Text)
    reference_number = db.Column(db.String(50), unique=True)
    
    def __repr__(self):
        return f'<Objection {self.reference_number}>'