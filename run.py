import os
from dotenv import load_dotenv
from app import create_app, db
from app.models.user import User, UserType
from app.models.tax import TaxType, TaxPeriod
from app.models.license import LicenseType
from flask_migrate import Migrate
from datetime import datetime
import calendar

# Load environment variables from .env file if it exists
load_dotenv()

# Create app with the specified configuration
app = create_app(os.getenv('FLASK_CONFIG') or 'default')
migrate = Migrate(app, db)

@app.cli.command("init-db")
def init_db():
    """Initialize the database with required initial data."""
    # Create tables
    db.create_all()
    
    # Create default user types
    user_types = [
        {'name': 'Individual', 'description': 'Individual taxpayers'},
        {'name': 'Non-Individual', 'description': 'Business entities, organizations, etc.'},
        {'name': 'Agent', 'description': 'Tax agents and representatives'},
        {'name': 'Internal', 'description': 'Tax administration employees'},
        {'name': 'Government', 'description': 'Government officials and agencies'}
    ]
    
    for ut in user_types:
        if not UserType.query.filter_by(name=ut['name']).first():
            user_type = UserType(**ut)
            db.session.add(user_type)
    
    # Create default admin user
    if not User.query.filter_by(username='Admin').first():
        admin_type = UserType.query.filter_by(name='Internal').first()
        admin = User(
            username='Admin',
            email='admin@gmail.com',
            first_name='System',
            last_name='Administrator',
            user_type_id=admin_type.id,
            is_admin=True
        )
        admin.set_password('Password')  # Change in production!
        db.session.add(admin)
    
    # Create default tax types
    tax_types = [
        {'code': 'VAT', 'name': 'Value Added Tax', 'description': 'Tax on consumption', 'is_core': True},
        {'code': 'PIT', 'name': 'Personal Income Tax', 'description': 'Tax on personal income', 'is_core': True},
        {'code': 'CIT', 'name': 'Corporate Income Tax', 'description': 'Tax on corporate profits', 'is_core': True},
        {'code': 'WT', 'name': 'Withholding Tax', 'description': 'Tax withheld at source', 'is_core': True},
        {'code': 'PT', 'name': 'Property Tax', 'description': 'Tax on property ownership', 'is_core': False},
        {'code': 'EXT', 'name': 'Excise Tax', 'description': 'Tax on specific goods', 'is_core': False}
    ]
    
    for tt in tax_types:
        if not TaxType.query.filter_by(code=tt['code']).first():
            tax_type = TaxType(**tt)
            db.session.add(tax_type)
    
    # Create license types
    license_types = [
        {'code': 'BL', 'name': 'Business License', 'description': 'General business license', 'category': 'General', 'fee': 100.00, 'validity_period': 12},
        {'code': 'MV', 'name': 'Motor Vehicle License', 'description': 'License for motor vehicles', 'category': 'Transport', 'fee': 75.00, 'validity_period': 12},
        {'code': 'AL', 'name': 'Alcohol License', 'description': 'License for selling alcohol', 'category': 'Special', 'fee': 250.00, 'validity_period': 12},
        {'code': 'IL', 'name': 'Import License', 'description': 'License for importing goods', 'category': 'Trade', 'fee': 300.00, 'validity_period': 12},
        {'code': 'EL', 'name': 'Export License', 'description': 'License for exporting goods', 'category': 'Trade', 'fee': 300.00, 'validity_period': 12}
    ]
    
    for lt in license_types:
        if not LicenseType.query.filter_by(code=lt['code']).first():
            license_type = LicenseType(**lt)
            db.session.add(license_type)
    
    # Create tax periods
    current_year = datetime.now().year
    for year in range(current_year - 2, current_year + 2):
        # Monthly periods for VAT
        for month in range(1, 13):
            period_name = f"{year}-{month:02d}"
            if not TaxPeriod.query.filter_by(name=period_name, period_type='Monthly').first():
                period = TaxPeriod(
                    name=period_name,
                    period_type='Monthly',
                    start_date=datetime(year, month, 1),
                    end_date=datetime(year, month, calendar.monthrange(year, month)[1])
                )
                db.session.add(period)
        
        # Quarterly periods
        for quarter in range(1, 5):
            start_month = (quarter - 1) * 3 + 1
            end_month = quarter * 3
            period_name = f"{year}-Q{quarter}"
            if not TaxPeriod.query.filter_by(name=period_name, period_type='Quarterly').first():
                period = TaxPeriod(
                    name=period_name,
                    period_type='Quarterly',
                    start_date=datetime(year, start_month, 1),
                    end_date=datetime(year, end_month, calendar.monthrange(year, end_month)[1])
                )
                db.session.add(period)
        
        # Annual period
        period_name = f"{year}"
        if not TaxPeriod.query.filter_by(name=period_name, period_type='Annual').first():
            period = TaxPeriod(
                name=period_name,
                period_type='Annual',
                start_date=datetime(year, 1, 1),
                end_date=datetime(year, 12, 31)
            )
            db.session.add(period)
    
    # Commit all changes
    db.session.commit()
    print("Database initialized with default data.")

# Add shell context
@app.shell_context_processor
def make_shell_context():
    return dict(app=app, db=db, User=User, UserType=UserType, TaxType=TaxType, TaxPeriod=TaxPeriod)

# Run the application
if __name__ == '__main__':
    # Check if database needs to be initialized
    with app.app_context():
        if not os.path.exists('app.db') and app.config['SQLALCHEMY_DATABASE_URI'].startswith('sqlite'):
            print("Initializing database...")
            init_db()
            print("Database initialized!")
    
    # Run the application
    app.run(debug=True, host='0.0.0.0', port=int(os.environ.get('PORT', 5000)))