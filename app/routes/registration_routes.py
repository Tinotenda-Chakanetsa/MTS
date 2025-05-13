from flask import Blueprint, render_template, redirect, url_for, flash, request, jsonify
from flask_login import login_required, current_user
from app import db
from app.models.user import User, Account, UserType
from app.models.process import Person, Organization, Property, Request
from app.models.registration import Registration, IndividualRegistration, NonIndividualRegistration, SoleProprietorRegistration, PropertyRegistration
from app.services.auth_service import get_user_permissions
from datetime import datetime, timedelta
import uuid

registration_bp = Blueprint('registration', __name__, url_prefix='/registration')

# Public route: New Individual Registration
@registration_bp.route('/new-individual', methods=['GET', 'POST'])
def new_individual_registration():
    from app.models.registration import IndividualRegistration
    from app.models.user import User
    from app import db
    from flask import request, redirect, url_for, flash, render_template

    if request.method == 'POST':
        first_name = request.form.get('first_name')
        last_name = request.form.get('last_name')
        email = request.form.get('email')
        phone = request.form.get('phone')
        id_number = request.form.get('id_number')
        dob = request.form.get('dob')
        address = request.form.get('address')
        errors = []
        if not all([first_name, last_name, email, phone, id_number, dob, address]):
            errors.append('All fields are required.')
        # Check for duplicate ID or email
        existing = IndividualRegistration.query.filter((IndividualRegistration.id_number == id_number) | (IndividualRegistration.email == email)).first()
        if existing:
            errors.append('A registration with this ID or email already exists.')
        if errors:
            for e in errors:
                flash(e, 'danger')
            return render_template('registrations/new_individual.html')
        # Create registration
        reg = IndividualRegistration(
            first_name=first_name,
            last_name=last_name,
            email=email,
            phone=phone,
            id_number=id_number,
            dob=dob,
            address=address,
            status='Pending'
        )
        db.session.add(reg)
        db.session.commit()
        flash('Registration submitted successfully! You will be notified once approved.', 'success')
        return redirect(url_for('auth.login'))
    return render_template('registrations/new_individual.html')

@registration_bp.route('/')
@login_required
def index():
    # Get user permissions
    permissions = get_user_permissions(current_user)
    
    return render_template('registrations/index.html', permissions=permissions)

@registration_bp.route('/individuals')
@login_required
def individuals():
    # List system users of type Individual
    permissions = get_user_permissions(current_user)
    if not any(perm in permissions for perm in ['view_all_accounts', 'admin_access']):
        flash('You do not have permission to view users', 'danger')
        return redirect(url_for('registration.index'))
    page = request.args.get('page', 1, type=int)
    per_page = 20
    users = User.query.join(UserType).filter(UserType.name == 'Individual').order_by(User.created_at.desc()).paginate(page=page, per_page=per_page)
    return render_template('registrations/individuals.html', users=users, permissions=permissions)

@registration_bp.route('/individuals/<int:user_id>')
@login_required
def view_individual(user_id):
    # Show accounts for a user
    permissions = get_user_permissions(current_user)
    if not any(perm in permissions for perm in ['view_all_accounts', 'admin_access']):
        flash('You do not have permission to view users', 'danger')
        return redirect(url_for('registration.index'))
    user = User.query.get_or_404(user_id)
    accounts = user.accounts.all()
    return render_template('registrations/user_accounts.html', user=user, accounts=accounts, permissions=permissions)

@registration_bp.route('/non-individuals')
@login_required
def non_individuals():
    # List system users of type Non-Individual
    permissions = get_user_permissions(current_user)
    if not any(perm in permissions for perm in ['view_all_accounts', 'admin_access']):
        flash('You do not have permission to view users', 'danger')
        return redirect(url_for('registration.index'))
    page = request.args.get('page', 1, type=int)
    per_page = 20
    users = User.query.join(UserType).filter(UserType.name == 'Non-Individual').order_by(User.created_at.desc()).paginate(page=page, per_page=per_page)
    return render_template('registrations/non_individuals.html', users=users, permissions=permissions)

@registration_bp.route('/non-individuals/<int:user_id>')
@login_required
def view_non_individual(user_id):
    # Show accounts for a user
    permissions = get_user_permissions(current_user)
    if not any(perm in permissions for perm in ['view_all_accounts', 'admin_access']):
        flash('You do not have permission to view users', 'danger')
        return redirect(url_for('registration.index'))
    user = User.query.get_or_404(user_id)
    accounts = user.accounts.all()
    return render_template('registrations/user_accounts.html', user=user, accounts=accounts, permissions=permissions)

@registration_bp.route('/sole-proprietors')
@login_required
def sole_proprietors():
    # List system users of type Sole Proprietor
    permissions = get_user_permissions(current_user)
    if not any(perm in permissions for perm in ['view_all_accounts', 'admin_access']):
        flash('You do not have permission to view users', 'danger')
        return redirect(url_for('registration.index'))
    page = request.args.get('page', 1, type=int)
    per_page = 20
    users = User.query.join(UserType).filter(UserType.name == 'Sole Proprietor').order_by(User.created_at.desc()).paginate(page=page, per_page=per_page)
    return render_template('registrations/sole_proprietors.html', users=users, permissions=permissions)

@registration_bp.route('/sole-proprietors/<int:user_id>')
@login_required
def view_sole_proprietor(user_id):
    # Show accounts for a user
    permissions = get_user_permissions(current_user)
    if not any(perm in permissions for perm in ['view_all_accounts', 'admin_access']):
        flash('You do not have permission to view users', 'danger')
        return redirect(url_for('registration.index'))
    user = User.query.get_or_404(user_id)
    accounts = user.accounts.all()
    return render_template('registrations/user_accounts.html', user=user, accounts=accounts, permissions=permissions)

@registration_bp.route('/properties')
@login_required
def properties():
    # Get user permissions
    permissions = get_user_permissions(current_user)
    
    # Check if user has permission to view property registrations
    if not any(perm in permissions for perm in ['view_all_accounts', 'admin_access']):
        flash('You do not have permission to view property registrations', 'danger')
        return redirect(url_for('registration.index'))
    
    page = request.args.get('page', 1, type=int)
    per_page = 20
    status = request.args.get('status', '')
    ownership_type = request.args.get('ownership_type', '')
    
    query = PropertyRegistration.query
    
    if status:
        query = query.filter(PropertyRegistration.status == status)
    
    if ownership_type:
        query = query.filter(PropertyRegistration.ownership_type == ownership_type)
    
    registrations = query.order_by(PropertyRegistration.registered_date.desc()).paginate(page=page, per_page=per_page)
    
    # Get statuses and ownership types for filters
    statuses = ['Active', 'Suspended', 'Transferred']
    ownership_types = ['Sole', 'Joint', 'Trust', 'Corporate']
    
    return render_template('registrations/properties.html', 
                           registrations=registrations, 
                           statuses=statuses, 
                           ownership_types=ownership_types, 
                           selected_status=status, 
                           selected_ownership_type=ownership_type, 
                           permissions=permissions)

from app.forms.property_forms import PropertyRegistrationForm
from app.models.process import Property
from app.models.registration import PropertyRegistration

@registration_bp.route('/new-property', methods=['GET', 'POST'])
@login_required
def new_property_registration():
    permissions = get_user_permissions(current_user)
    if not any(perm in permissions for perm in ['view_all_accounts', 'admin_access']):
        flash('You do not have permission to register properties', 'danger')
        return redirect(url_for('registration.properties'))
    
    # Build account choices
    if 'admin_access' in permissions:
        accounts = Account.query.order_by(Account.name).all()
        account_choices = [(a.id, a.name) for a in accounts]
    else:
        accounts = Account.query.filter_by(user_id=current_user.id).all()
        account_choices = [(a.id, a.name) for a in accounts]

    # Auto-create an account if none exist
    if not account_choices:
        account_number = f'ACC{uuid.uuid4().hex[:8].upper()}'
        account_name = current_user.full_name or current_user.username
        new_account = Account(user_id=current_user.id, account_number=account_number, name=account_name)
        db.session.add(new_account)
        db.session.commit()
        account_choices = [(new_account.id, new_account.name)]

    # Initialize form and set choices
    form = PropertyRegistrationForm()
    form.account_id.choices = account_choices
    
    # Auto-assign the only available account for non-admins (prevent choice validation errors)
    if len(account_choices) == 1:
        form.account_id.data = account_choices[0][0]

    if form.validate_on_submit():
        try:
            # 1. Create Property
            # Get selected account ID
            account_id = form.account_id.data
            # Generate a unique property identifier
            property_identifier = f'PROP{uuid.uuid4().hex[:8].upper()}'
            new_property = Property(
                account_id=account_id,
                property_type=form.type.data,
                property_identifier=property_identifier,
                owner_name=form.owner_name.data,
                address=form.location.data
            )
            db.session.add(new_property)
            db.session.commit()
            # 2. Create PropertyRegistration referencing the new property
            registration_number = f'PR{new_property.id:06d}'
            reg = PropertyRegistration(
                property_id=new_property.id,
                registration_number=registration_number,
                status=form.status.data,
                registered_date=datetime.utcnow()
            )
            db.session.add(reg)
            db.session.commit()
            flash('Property registered successfully!', 'success')
            return redirect(url_for('registration.properties'))
        except Exception as e:
            db.session.rollback()
            flash(f'Error registering property: {str(e)}', 'danger')
    elif request.method == 'POST':
        for field, errors in form.errors.items():
            for error in errors:
                flash(f"Error in {getattr(form, field).label.text}: {error}", 'danger')
    return render_template('registrations/new_property.html', form=form, permissions=permissions)



@registration_bp.route('/properties/<int:registration_id>')
@login_required
def view_property(registration_id):
    # Get user permissions
    permissions = get_user_permissions(current_user)
    
    # Check if user has permission to view property registrations
    if not any(perm in permissions for perm in ['view_all_accounts', 'admin_access']):
        flash('You do not have permission to view property registrations', 'danger')
        return redirect(url_for('registration.index'))
    
    registration = PropertyRegistration.query.get_or_404(registration_id)
    
    return render_template('registrations/property_detail.html', 
                           registration=registration, 
                           permissions=permissions)

@registration_bp.route('/returns-assessments')
@login_required
def returns_assessments():
    # Get user permissions
    permissions = get_user_permissions(current_user)
    
    # Check if user has permission to view returns assessments
    if not any(perm in permissions for perm in ['view_all_accounts', 'admin_access', 'process_returns']):
        flash('You do not have permission to view returns assessments', 'danger')
        return redirect(url_for('registration.index'))
    
    # Get tax returns that need assessment
    from app.models.tax import TaxReturn
    returns = TaxReturn.query.filter_by(status='Filed').order_by(TaxReturn.filing_date.desc()).limit(20).all()
    
    return render_template('registrations/returns_assessments.html', 
                           returns=returns, 
                           permissions=permissions)

@registration_bp.route('/taxpayer-ledger')
@login_required
def taxpayer_ledger():
    # Get user permissions
    permissions = get_user_permissions(current_user)
    
    # Check if user has permission to view taxpayer ledger
    if not any(perm in permissions for perm in ['view_all_accounts', 'admin_access', 'manage_tax_accounts']):
        flash('You do not have permission to view taxpayer ledger', 'danger')
        return redirect(url_for('registration.index'))
    
    account_id = request.args.get('account_id', type=int)
    tax_type_id = request.args.get('tax_type_id', type=int)
    start_date = request.args.get('start_date')
    end_date = request.args.get('end_date')
    
    # Convert string dates to datetime objects if provided
    if start_date:
        try:
            start_date = datetime.strptime(start_date, '%Y-%m-%d').date()
        except ValueError:
            start_date = None
    
    if end_date:
        try:
            end_date = datetime.strptime(end_date, '%Y-%m-%d').date()
        except ValueError:
            end_date = None
    
    # Default to last 30 days if no dates provided
    if not start_date:
        start_date = datetime.utcnow().date() - timedelta(days=30)
    
    if not end_date:
        end_date = datetime.utcnow().date()
    
    # Get accounts for filter
    accounts = Account.query.all()
    
    # Get tax types for filter
    from app.models.tax import TaxType
    tax_types = TaxType.query.all()
    
    # Get ledger entries if account is selected
    ledger_entries = []
    if account_id:
        from app.models.registration import TaxpayerLedger
        query = TaxpayerLedger.query.filter_by(account_id=account_id)
        
        if tax_type_id:
            query = query.filter_by(tax_type_id=tax_type_id)
        
        query = query.filter(
            TaxpayerLedger.transaction_date >= start_date,
            TaxpayerLedger.transaction_date <= end_date
        )
        
        ledger_entries = query.order_by(TaxpayerLedger.transaction_date.desc()).all()
    
    return render_template('registrations/taxpayer_ledger.html', 
                           accounts=accounts, 
                           tax_types=tax_types, 
                           ledger_entries=ledger_entries, 
                           selected_account_id=account_id, 
                           selected_tax_type_id=tax_type_id, 
                           start_date=start_date.strftime('%Y-%m-%d') if start_date else '', 
                           end_date=end_date.strftime('%Y-%m-%d') if end_date else '', 
                           permissions=permissions)

@registration_bp.route('/audit-collection')
@login_required
def audit_collection():
    # Get user permissions
    permissions = get_user_permissions(current_user)
    
    # Check if user has permission to view audit and collection cases
    if not any(perm in permissions for perm in ['view_all_accounts', 'admin_access']):
        flash('You do not have permission to view audit and collection cases', 'danger')
        return redirect(url_for('registration.index'))
    
    # Get recent audit cases
    from app.models.registration import AuditCase
    audit_cases = AuditCase.query.order_by(AuditCase.open_date.desc()).limit(10).all()
    
    # Get recent collection cases
    from app.models.process import Collection
    collections = Collection.query.order_by(Collection.start_date.desc()).limit(10).all()
    
    return render_template('registrations/audit_collection.html', 
                           audit_cases=audit_cases, 
                           collections=collections, 
                           permissions=permissions)

@registration_bp.route('/objections-appeals')
@login_required
def objections_appeals():
    # Get user permissions
    permissions = get_user_permissions(current_user)
    
    # Check if user has permission to view objections and appeals
    if not any(perm in permissions for perm in ['view_all_accounts', 'admin_access', 'handle_objections']):
        flash('You do not have permission to view objections and appeals', 'danger')
        return redirect(url_for('registration.index'))
    
    # Get recent objections
    from app.models.tax import Objection
    objections = Objection.query.filter_by(status='Pending').order_by(Objection.filing_date.desc()).limit(10).all()
    
    # Get objection registrations
    from app.models.registration import ObjectionRegistration
    objection_registrations = ObjectionRegistration.query.order_by(ObjectionRegistration.registered_date.desc()).limit(10).all()
    
    return render_template('registrations/objections_appeals.html', 
                           objections=objections, 
                           objection_registrations=objection_registrations, 
                           permissions=permissions)

@registration_bp.route('/payment-refund')
@login_required
def payment_refund():
    # Get user permissions
    permissions = get_user_permissions(current_user)
    
    # Check if user has permission to view payments and refunds
    if not any(perm in permissions for perm in ['view_all_accounts', 'admin_access', 'process_refunds']):
        flash('You do not have permission to view payments and refunds', 'danger')
        return redirect(url_for('registration.index'))
    
    # Get recent payment registrations
    from app.models.registration import PaymentRegistration
    payment_registrations = PaymentRegistration.query.order_by(PaymentRegistration.registered_date.desc()).limit(10).all()
    
    # Get recent refund registrations
    from app.models.registration import RefundRegistration
    refund_registrations = RefundRegistration.query.order_by(RefundRegistration.registered_date.desc()).limit(10).all()
    
    # Get pending refunds
    from app.models.tax import Refund
    pending_refunds = Refund.query.filter_by(status='Pending').order_by(Refund.request_date.desc()).limit(10).all()
    
    return render_template('registrations/payment_refund.html', 
                           payment_registrations=payment_registrations, 
                           refund_registrations=refund_registrations, 
                           pending_refunds=pending_refunds, 
                           permissions=permissions)