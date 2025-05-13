from app import db, create_app
from app.models.user import User, UserType

app = create_app()

with app.app_context():
    # Find or create the admin user type (optional, if you use user types)
    admin_type = UserType.query.filter_by(name='Admin').first()
    if not admin_type:
        admin_type = UserType(name='Admin', description='Administrator')
        db.session.add(admin_type)
        db.session.commit()

    # Check if the admin user already exists (by username or email)
    admin_user = User.query.filter((User.username=='Admin') | (User.email=='admin@gmail.com')).first()
    if admin_user:
        if admin_user.username == 'Admin':
            print("A user with username 'Admin' already exists.")
        elif admin_user.email == 'admin@gmail.com':
            print("A user with email 'admin@gmail.com' already exists.")
    else:
        admin_user = User(
            username='Admin',
            email='admin@gmail.com',  # Change as needed
            user_type_id=admin_type.id,
            is_admin=True,
            is_active=True,
            first_name='System',
            last_name='Administrator'
        )
        admin_user.set_password('Password')
        db.session.add(admin_user)
        db.session.commit()
        print("Admin user created.")
