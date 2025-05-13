from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_login import LoginManager
from flask_bcrypt import Bcrypt
from flask_mail import Mail
from flask_wtf.csrf import CSRFProtect
from .config import config

# Initialize extensions
db = SQLAlchemy()
migrate = Migrate()
login_manager = LoginManager()
login_manager.login_view = 'auth.login'
login_manager.login_message_category = 'info'
bcrypt = Bcrypt()
mail = Mail()
csrf = CSRFProtect()

def create_app(config_name='default'):
    """Create the Flask application instance"""
    app = Flask(__name__)
    app.config.from_object(config[config_name])
    
    # Initialize extensions with app
    db.init_app(app)
    migrate.init_app(app, db)
    login_manager.init_app(app)
    bcrypt.init_app(app)
    mail.init_app(app)
    csrf.init_app(app)
    
    # Register blueprints
    from .routes.main import main_bp
    from .routes.auth import auth_bp
    from .routes.dashboard import dashboard_bp
    from .routes.tax_routes import tax_bp
    from .routes.e_services import e_services_bp
    from .routes.process_routes import process_bp
    from .routes.registration_routes import registration_bp
    from .routes.reporting import reporting_bp
    
    app.register_blueprint(main_bp)
    app.register_blueprint(auth_bp)
    app.register_blueprint(dashboard_bp)
    app.register_blueprint(tax_bp)
    app.register_blueprint(e_services_bp)
    app.register_blueprint(process_bp)
    app.register_blueprint(registration_bp)
    app.register_blueprint(reporting_bp)
    
    # Error handlers
    from .routes.errors import errors_bp
    app.register_blueprint(errors_bp)
    
    # Shell context
    @app.shell_context_processor
    def make_shell_context():
        return {'db': db, 'app': app}
    
    def initialize_database(app):
        from app.models.user import User, UserType
        from app.models.tax import TaxType, TaxPeriod
        from datetime import date
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
                    username='admin',
                    email='admin@example.com',
                    first_name='Admin',
                    last_name='User',
                    is_admin=True,
                    is_active=True,
                    user_type_id=admin_type.id if admin_type else None
                )
                admin.set_password('admin')
                db.session.add(admin)
                db.session.commit()
                print("Created admin user")
            
            # Check if tax types exist
            if TaxType.query.count() == 0:
                # Create tax types
                tax_types = [
                    TaxType(code='VAT', name='Value Added Tax', description='Tax on goods and services', is_core=True),
                    TaxType(code='PIT', name='Personal Income Tax', description='Tax on individual income', is_core=True),
                    TaxType(code='CIT', name='Corporate Income Tax', description='Tax on corporate profits', is_core=True),
                    TaxType(code='WHT', name='Withholding Tax', description='Tax withheld at source', is_core=True)
                ]
                db.session.add_all(tax_types)
                db.session.commit()
                print("Created tax types")
            
            # Now seed quarterly periods
            year = 2025
            quarters = [
                (f'{year}-Q1', date(year, 1, 1), date(year, 3, 31)),
                (f'{year}-Q2', date(year, 4, 1), date(year, 6, 30)),
                (f'{year}-Q3', date(year, 7, 1), date(year, 9, 30)),
                (f'{year}-Q4', date(year, 10, 1), date(year, 12, 31)),
            ]
            tax_types = TaxType.query.all()
            for tax_type in tax_types:
                for code, start, end in quarters:
                    exists = TaxPeriod.query.filter_by(period_code=code, tax_type_id=tax_type.id).first()
                    if not exists:
                        period = TaxPeriod(
                            period_code=code,
                            start_date=start,
                            end_date=end,
                            due_date=end,  # Set due_date to end_date to satisfy NOT NULL
                            tax_type_id=tax_type.id,
                            status='Open'  # Explicitly set status
                        )
                        db.session.add(period)
            db.session.commit()
            print("Seeded quarterly periods")
    
    initialize_database(app)
    return app