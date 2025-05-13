from app import db
from datetime import datetime

class LicenseType(db.Model):
    __tablename__ = 'license_types'
    
    id = db.Column(db.Integer, primary_key=True)
    code = db.Column(db.String(20), unique=True, nullable=False)
    name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text)
    category = db.Column(db.String(50))  # General, Motor Vehicle, Driver's License
    fee = db.Column(db.Numeric(10, 2))
    validity_period = db.Column(db.Integer)  # In months
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    licenses = db.relationship('License', backref='license_type', lazy='dynamic')
    
    def __repr__(self):
        return f'<LicenseType {self.code}>'

class License(db.Model):
    __tablename__ = 'licenses'
    
    id = db.Column(db.Integer, primary_key=True)
    license_number = db.Column(db.String(50), unique=True, nullable=False)
    license_type_id = db.Column(db.Integer, db.ForeignKey('license_types.id'), nullable=False)
    account_id = db.Column(db.Integer, db.ForeignKey('accounts.id'), nullable=False)
    issue_date = db.Column(db.Date, nullable=False)
    expiry_date = db.Column(db.Date, nullable=False)
    status = db.Column(db.String(20), default='Active')  # Active, Expired, Suspended, Revoked
    fee_paid = db.Column(db.Numeric(10, 2))
    payment_reference = db.Column(db.String(50))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    account = db.relationship('Account')
    
    def __repr__(self):
        return f'<License {self.license_number}>'

class VehicleRegistration(db.Model):
    __tablename__ = 'vehicle_registrations'
    
    id = db.Column(db.Integer, primary_key=True)
    license_id = db.Column(db.Integer, db.ForeignKey('licenses.id'), nullable=False)
    vehicle_identification_number = db.Column(db.String(17), unique=True, nullable=False)
    plate_number = db.Column(db.String(20), unique=True, nullable=False)
    make = db.Column(db.String(50), nullable=False)
    model = db.Column(db.String(50), nullable=False)
    year = db.Column(db.Integer, nullable=False)
    color = db.Column(db.String(30))
    engine_number = db.Column(db.String(30))
    registered_owner = db.Column(db.String(100), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    license = db.relationship('License')
    
    def __repr__(self):
        return f'<VehicleRegistration {self.plate_number}>'

class DriversLicense(db.Model):
    __tablename__ = 'drivers_licenses'
    
    id = db.Column(db.Integer, primary_key=True)
    license_id = db.Column(db.Integer, db.ForeignKey('licenses.id'), nullable=False)
    license_class = db.Column(db.String(10), nullable=False)  # A, B, C, etc.
    holder_name = db.Column(db.String(100), nullable=False)
    date_of_birth = db.Column(db.Date, nullable=False)
    address = db.Column(db.String(200), nullable=False)
    restrictions = db.Column(db.String(100))
    endorsements = db.Column(db.String(100))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    license = db.relationship('License')
    
    def __repr__(self):
        return f'<DriversLicense {self.license.license_number}>'