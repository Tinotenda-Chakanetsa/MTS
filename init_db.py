from app import create_app, db
from app.models.user import User, UserType
from app.models.tax import TaxType
import os

app = create_app(os.getenv('FLASK_CONFIG') or 'default')

with app.app_context():
    # Create all tables
    db.create_all()
    
    # Check if user types already exist
    if UserType.query.count() == 0:
        # Create user types
        user_types = [
            UserType(name='Individual', description='Individual taxpayer'),
            UserType(name='Non-Individual', description='Business or organization'),
            UserType(name='Agent', description='Tax agent or representative'),
            UserType(name='Administrator', description='System administrator')
        ]
        db.session.add_all(user_types)
        db.session.commit()
        print("Created user types")
    
    # Check if admin user exists
    if User.query.filter_by(username='admin').count() == 0:
        # Create admin user
        admin_type = UserType.query.filter_by(name='Administrator').first()
        admin = User(
            username='Admin',
            email='admin@gmail.com',
            first_name='System',
            last_name='Adminstrator',
            is_admin=True,
            is_active=True,
            user_type_id=admin_type.id if admin_type else None
        )
        admin.set_password('Password')
        db.session.add(admin)
        db.session.commit()
        print("Created admin user")
    
    # Check if tax types exist
    if TaxType.query.count() == 0:
        # Create tax types
        tax_types = [
            TaxType(code='VAT', name='Value Added Tax', description='Tax on goods and services'),
            TaxType(code='PIT', name='Personal Income Tax', description='Tax on individual income'),
            TaxType(code='CIT', name='Corporate Income Tax', description='Tax on corporate profits'),
            TaxType(code='WHT', name='Withholding Tax', description='Tax withheld at source')
        ]
        db.session.add_all(tax_types)
        db.session.commit()
        print("Created tax types")
    
    print("Database initialization complete")
