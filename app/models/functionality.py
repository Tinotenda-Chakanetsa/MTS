from app import db
from datetime import datetime
import json

class Document(db.Model):
    __tablename__ = 'documents'
    
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    document_type = db.Column(db.String(50), nullable=False)  # Template, Form, Certificate, Notice
    content = db.Column(db.Text)
    file_path = db.Column(db.String(255))
    status = db.Column(db.String(20), default='Active')  # Active, Archived, Draft
    created_by = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    last_updated = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    creator = db.relationship('User')
    
    def __repr__(self):
        return f'<Document {self.title}>'

class Correspondence(db.Model):
    __tablename__ = 'correspondences'
    
    id = db.Column(db.Integer, primary_key=True)
    account_id = db.Column(db.Integer, db.ForeignKey('accounts.id'), nullable=False)
    correspondence_type = db.Column(db.String(50), nullable=False)  # Email, Letter, SMS, Notice
    subject = db.Column(db.String(200), nullable=False)
    content = db.Column(db.Text, nullable=False)
    sent_by = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    sent_date = db.Column(db.DateTime, default=datetime.utcnow)
    status = db.Column(db.String(20), default='Sent')  # Draft, Sent, Delivered, Failed
    reference_number = db.Column(db.String(50), unique=True)
    
    # Relationships
    account = db.relationship('Account')
    sender = db.relationship('User')
    
    def __repr__(self):
        return f'<Correspondence {self.reference_number}>'

class WorkItem(db.Model):
    __tablename__ = 'work_items'
    
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text)
    item_type = db.Column(db.String(50), nullable=False)  # Task, Review, Approval, Verification
    priority = db.Column(db.String(10), default='Medium')  # Low, Medium, High
    status = db.Column(db.String(20), default='Pending')  # Pending, In Progress, Completed, Cancelled
    due_date = db.Column(db.DateTime)
    assigned_to = db.Column(db.Integer, db.ForeignKey('users.id'))
    created_by = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    completed_at = db.Column(db.DateTime)
    
    # Relationships
    assignee = db.relationship('User', foreign_keys=[assigned_to])
    creator = db.relationship('User', foreign_keys=[created_by])
    
    def __repr__(self):
        return f'<WorkItem {self.title}>'

class WorkList(db.Model):
    __tablename__ = 'work_lists'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text)
    owner_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    owner = db.relationship('User')
    work_items = db.relationship('WorkListItem', backref='work_list', lazy='dynamic')
    
    def __repr__(self):
        return f'<WorkList {self.name}>'

class WorkListItem(db.Model):
    __tablename__ = 'work_list_items'
    
    id = db.Column(db.Integer, primary_key=True)
    work_list_id = db.Column(db.Integer, db.ForeignKey('work_lists.id'), nullable=False)
    work_item_id = db.Column(db.Integer, db.ForeignKey('work_items.id'), nullable=False)
    position = db.Column(db.Integer, default=0)
    
    # Relationships
    work_item = db.relationship('WorkItem')
    
    def __repr__(self):
        return f'<WorkListItem {self.id}>'

class Notification(db.Model):
    __tablename__ = 'notifications'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    title = db.Column(db.String(200), nullable=False)
    message = db.Column(db.Text, nullable=False)
    notification_type = db.Column(db.String(50), default='System')  # System, Tax, Reminder, Alert
    priority = db.Column(db.String(10), default='Normal')  # Low, Normal, High
    is_read = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    read_at = db.Column(db.DateTime)
    
    # Relationships
    user = db.relationship('User')
    
    def __repr__(self):
        return f'<Notification {self.id}>'

class Case(db.Model):
    __tablename__ = 'cases'
    
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text)
    case_type = db.Column(db.String(50), nullable=False)  # Support, Investigation, Dispute, Compliance
    account_id = db.Column(db.Integer, db.ForeignKey('accounts.id'), nullable=False)
    assigned_to = db.Column(db.Integer, db.ForeignKey('users.id'))
    created_by = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    status = db.Column(db.String(20), default='Open')  # Open, In Progress, Resolved, Closed
    priority = db.Column(db.String(10), default='Medium')  # Low, Medium, High
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    resolved_at = db.Column(db.DateTime)
    reference_number = db.Column(db.String(50), unique=True)
    
    # Relationships
    account = db.relationship('Account')
    assignee = db.relationship('User', foreign_keys=[assigned_to])
    creator = db.relationship('User', foreign_keys=[created_by])
    case_notes = db.relationship('CaseNote', backref='case', lazy='dynamic')
    
    def __repr__(self):
        return f'<Case {self.reference_number}>'

class CaseNote(db.Model):
    __tablename__ = 'case_notes'
    
    id = db.Column(db.Integer, primary_key=True)
    case_id = db.Column(db.Integer, db.ForeignKey('cases.id'), nullable=False)
    content = db.Column(db.Text, nullable=False)
    created_by = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    creator = db.relationship('User')
    
    def __repr__(self):
        return f'<CaseNote {self.id}>'

class BalanceItem(db.Model):
    __tablename__ = 'balance_items'
    
    id = db.Column(db.Integer, primary_key=True)
    account_id = db.Column(db.Integer, db.ForeignKey('accounts.id'), nullable=False)
    tax_type_id = db.Column(db.Integer, db.ForeignKey('tax_types.id'), nullable=False)
    tax_period_id = db.Column(db.Integer, db.ForeignKey('tax_periods.id'))
    amount = db.Column(db.Numeric(14, 2), nullable=False)
    item_type = db.Column(db.String(20), nullable=False)  # Tax, Penalty, Interest, Credit, Payment
    description = db.Column(db.String(200))
    transaction_date = db.Column(db.DateTime, nullable=False)
    reference_number = db.Column(db.String(50))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    account = db.relationship('Account')
    tax_type = db.relationship('TaxType')
    tax_period = db.relationship('TaxPeriod')
    
    def __repr__(self):
        return f'<BalanceItem {self.id}>'

class Integration(db.Model):
    __tablename__ = 'integrations'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    integration_type = db.Column(db.String(50), nullable=False)  # API, Database, File, Service
    endpoint_url = db.Column(db.String(255))
    credentials = db.Column(db.Text)  # Encrypted
    status = db.Column(db.String(20), default='Active')  # Active, Inactive, Failed
    last_sync = db.Column(db.DateTime)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    def __repr__(self):
        return f'<Integration {self.name}>'

class NonFiscalPayment(db.Model):
    __tablename__ = 'non_fiscal_payments'
    
    id = db.Column(db.Integer, primary_key=True)
    payment_type = db.Column(db.String(50), nullable=False)  # Fee, Fine, Service Charge
    amount = db.Column(db.Numeric(14, 2), nullable=False)
    account_id = db.Column(db.Integer, db.ForeignKey('accounts.id'), nullable=False)
    payment_date = db.Column(db.DateTime, nullable=False)
    payment_method = db.Column(db.String(20), nullable=False)  # Bank, Cash, Online
    reference_number = db.Column(db.String(50), unique=True)
    status = db.Column(db.String(20), default='Pending')  # Pending, Completed, Failed, Refunded
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    account = db.relationship('Account')
    
    def __repr__(self):
        return f'<NonFiscalPayment {self.reference_number}>'