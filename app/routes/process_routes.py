from flask import Blueprint, render_template, redirect, url_for, flash, request, jsonify
from flask_login import login_required, current_user
from app import db
from app.models.user import User, Account
from app.models.process import Person, Organization, Property, Request, Audit, Collection, Enforcement, Agreement
from app.models.tax import TaxReturn
from app.models.functionality import Notification
from app.services.auth_service import get_user_permissions
from datetime import datetime
import uuid

process_bp = Blueprint('process', __name__, url_prefix='/process')

@process_bp.route('/')
@login_required
def index():
    # Get user permissions
    permissions = get_user_permissions(current_user)
    
    return render_template('processes/index.html', permissions=permissions)

@process_bp.route('/persons')
@login_required
def persons():
    # Get user permissions
    permissions = get_user_permissions(current_user)
    
    # Check if user has permission to view persons
    if not any(perm in permissions for perm in ['view_all_accounts', 'admin_access']):
        flash('You do not have permission to view persons', 'danger')
        return redirect(url_for('process.index'))
    
    page = request.args.get('page', 1, type=int)
    per_page = 20
    search = request.args.get('search', '')
    
    query = Person.query
    
    if search:
        query = query.filter(
            Person.first_name.ilike(f'%{search}%') |
            Person.last_name.ilike(f'%{search}%') |
            Person.national_id.ilike(f'%{search}%') |
            Person.passport_number.ilike(f'%{search}%')
        )
    
    persons = query.order_by(Person.last_name).paginate(page=page, per_page=per_page)
    
    return render_template('processes/persons.html', 
                           persons=persons, 
                           search=search, 
                           permissions=permissions)

@process_bp.route('/persons/<int:person_id>')
@login_required
def view_person(person_id):
    # Get user permissions
    permissions = get_user_permissions(current_user)
    
    # Check if user has permission to view persons
    if not any(perm in permissions for perm in ['view_all_accounts', 'admin_access']):
        flash('You do not have permission to view persons', 'danger')
        return redirect(url_for('process.index'))
    
    person = Person.query.get_or_404(person_id)
    
    # Get accounts associated with this person
    accounts = [ah.account for ah in person.accounts]
    
    return render_template('processes/person_detail.html', 
                           person=person, 
                           accounts=accounts, 
                           permissions=permissions)

@process_bp.route('/organizations')
@login_required
def organizations():
    # Get user permissions
    permissions = get_user_permissions(current_user)
    
    # Check if user has permission to view organizations
    if not any(perm in permissions for perm in ['view_all_accounts', 'admin_access']):
        flash('You do not have permission to view organizations', 'danger')
        return redirect(url_for('process.index'))
    
    page = request.args.get('page', 1, type=int)
    per_page = 20
    search = request.args.get('search', '')
    
    query = Organization.query
    
    if search:
        query = query.filter(
            Organization.name.ilike(f'%{search}%') |
            Organization.registration_number.ilike(f'%{search}%') |
            Organization.tax_identifier.ilike(f'%{search}%')
        )
    
    organizations = query.order_by(Organization.name).paginate(page=page, per_page=per_page)
    
    return render_template('processes/organizations.html', 
                           organizations=organizations, 
                           search=search, 
                           permissions=permissions)

@process_bp.route('/organizations/<int:organization_id>')
@login_required
def view_organization(organization_id):
    # Get user permissions
    permissions = get_user_permissions(current_user)
    
    # Check if user has permission to view organizations
    if not any(perm in permissions for perm in ['view_all_accounts', 'admin_access']):
        flash('You do not have permission to view organizations', 'danger')
        return redirect(url_for('process.index'))
    
    organization = Organization.query.get_or_404(organization_id)
    
    # Get accounts associated with this organization
    accounts = [ah.account for ah in organization.accounts]
    
    return render_template('processes/organization_detail.html', 
                           organization=organization, 
                           accounts=accounts, 
                           permissions=permissions)

@process_bp.route('/properties')
@login_required
def properties():
    # Get user permissions
    permissions = get_user_permissions(current_user)
    
    # Check if user has permission to view properties
    if not any(perm in permissions for perm in ['view_all_accounts', 'admin_access']):
        flash('You do not have permission to view properties', 'danger')
        return redirect(url_for('process.index'))
    
    page = request.args.get('page', 1, type=int)
    per_page = 20
    search = request.args.get('search', '')
    property_type = request.args.get('type', '')
    
    query = Property.query
    
    if search:
        query = query.filter(
            Property.property_identifier.ilike(f'%{search}%') |
            Property.description.ilike(f'%{search}%') |
            Property.address.ilike(f'%{search}%')
        )
    
    if property_type:
        query = query.filter(Property.property_type == property_type)
    
    properties = query.order_by(Property.property_identifier).paginate(page=page, per_page=per_page)
    
    # Get property types for filter
    property_types = db.session.query(Property.property_type).distinct().all()
    property_types = [pt[0] for pt in property_types]
    
    return render_template('processes/properties.html', 
                           properties=properties, 
                           search=search, 
                           property_types=property_types, 
                           selected_type=property_type, 
                           permissions=permissions)

@process_bp.route('/properties/<int:property_id>')
@login_required
def view_property(property_id):
    # Get user permissions
    permissions = get_user_permissions(current_user)
    
    # Check if user has permission to view properties
    if not any(perm in permissions for perm in ['view_all_accounts', 'admin_access']):
        flash('You do not have permission to view properties', 'danger')
        return redirect(url_for('process.index'))
    
    property = Property.query.get_or_404(property_id)
    
    # Get property registrations
    from app.models.registration import PropertyRegistration
    registrations = PropertyRegistration.query.filter_by(property_id=property_id).all()
    
    return render_template('processes/property_detail.html', 
                           property=property, 
                           registrations=registrations, 
                           permissions=permissions)

@process_bp.route('/requests')
@login_required
def requests():
    # Get user permissions
    permissions = get_user_permissions(current_user)
    
    page = request.args.get('page', 1, type=int)
    per_page = 20
    status = request.args.get('status', '')
    request_type = request.args.get('type', '')
    
    query = Request.query
    
    # Filter by user's accounts if not admin/internal
    if not any(perm in permissions for perm in ['view_all_accounts', 'admin_access']):
        user_accounts = Account.query.filter_by(user_id=current_user.id).all()
        account_ids = [account.id for account in user_accounts]
        query = query.filter(Request.account_id.in_(account_ids))
    
    if status:
        query = query.filter(Request.status == status)
    
    if request_type:
        query = query.filter(Request.request_type == request_type)
    
    requests = query.order_by(Request.submission_date.desc()).paginate(page=page, per_page=per_page)
    
    # Get statuses and types for filters
    statuses = ['Pending', 'In Progress', 'Completed', 'Rejected']
    request_types = db.session.query(Request.request_type).distinct().all()
    request_types = [rt[0] for rt in request_types]
    
    return render_template('processes/requests.html', 
                           requests=requests, 
                           statuses=statuses, 
                           request_types=request_types, 
                           selected_status=status, 
                           selected_type=request_type, 
                           permissions=permissions)

@process_bp.route('/requests/<int:request_id>')
@login_required
def view_request(request_id):
    # Get user permissions
    permissions = get_user_permissions(current_user)
    
    request_obj = Request.query.get_or_404(request_id)
    
    # Check if user has permission to view this request
    if not any(perm in permissions for perm in ['view_all_accounts', 'admin_access']):
        user_accounts = Account.query.filter_by(user_id=current_user.id).all()
        account_ids = [account.id for account in user_accounts]
        if request_obj.account_id not in account_ids:
            flash('You do not have permission to view this request', 'danger')
            return redirect(url_for('process.requests'))
    
    return render_template('processes/request_detail.html', 
                           request=request_obj, 
                           permissions=permissions)

@process_bp.route('/audits')
@login_required
def audits():
    # Get user permissions
    permissions = get_user_permissions(current_user)
    
    # Check if user has permission to view audits
    if not any(perm in permissions for perm in ['view_all_accounts', 'admin_access']):
        flash('You do not have permission to view audits', 'danger')
        return redirect(url_for('process.index'))
    
    page = request.args.get('page', 1, type=int)
    per_page = 20
    status = request.args.get('status', '')
    audit_type = request.args.get('type', '')
    
    query = Audit.query
    
    if status:
        query = query.filter(Audit.status == status)
    
    if audit_type:
        query = query.filter(Audit.audit_type == audit_type)
    
    audits = query.order_by(Audit.start_date.desc()).paginate(page=page, per_page=per_page)
    
    # Get statuses and types for filters
    statuses = ['Planned', 'In Progress', 'Completed', 'Cancelled']
    audit_types = ['Desk', 'Field', 'Comprehensive']
    
    return render_template('processes/audits.html', 
                           audits=audits, 
                           statuses=statuses, 
                           audit_types=audit_types, 
                           selected_status=status, 
                           selected_type=audit_type, 
                           permissions=permissions)

@process_bp.route('/audits/<int:audit_id>')
@login_required
def view_audit(audit_id):
    # Get user permissions
    permissions = get_user_permissions(current_user)
    
    # Check if user has permission to view audits
    if not any(perm in permissions for perm in ['view_all_accounts', 'admin_access']):
        flash('You do not have permission to view audits', 'danger')
        return redirect(url_for('process.index'))
    
    audit = Audit.query.get_or_404(audit_id)
    
    # Get audit cases
    from app.models.registration import AuditCase
    cases = AuditCase.query.filter_by(audit_id=audit_id).all()
    
    return render_template('processes/audit_detail.html', 
                           audit=audit, 
                           cases=cases, 
                           permissions=permissions)

@process_bp.route('/audits/<int:audit_id>/update-status', methods=['POST'])
@login_required
def update_audit_status(audit_id):
    # Get user permissions
    permissions = get_user_permissions(current_user)
    
    # Check if user has admin access
    if 'admin_access' not in permissions:
        flash('You do not have permission to update audit status', 'danger')
        return redirect(url_for('process.view_audit', audit_id=audit_id))
    
    audit = Audit.query.get_or_404(audit_id)
    new_status = request.form.get('status')
    
    if not new_status:
        flash('No status provided', 'warning')
        return redirect(url_for('process.view_audit', audit_id=audit_id))
    
    valid_statuses = ['Planned', 'In Progress', 'Under Review', 'Completed', 'Cancelled']
    if new_status not in valid_statuses:
        flash('Invalid status provided', 'warning')
        return redirect(url_for('process.view_audit', audit_id=audit_id))
    
    # Update the audit status
    audit.status = new_status
    
    # If status is completed and no end date is set, set it to current date
    if new_status == 'Completed' and not audit.end_date:
        from datetime import date
        audit.end_date = date.today()
    
    # Save changes to database
    try:
        db.session.commit()
        
        # Send notification to the account owner about the status change
        account = Account.query.get(audit.account_id)
        if account and account.owner:
            # Customize message based on status
            if new_status == 'In Progress':
                message = f"Your tax audit ({audit.reference_number}) has begun. An auditor will be reviewing your tax return."
                notification_type = 'Warning'
            elif new_status == 'Under Review':
                message = f"Your tax audit ({audit.reference_number}) is now under final review."
                notification_type = 'Info'
            elif new_status == 'Completed':
                message = f"Your tax audit ({audit.reference_number}) has been completed. Please check your messages for any findings."
                notification_type = 'Success'
            elif new_status == 'Cancelled':
                message = f"Your tax audit ({audit.reference_number}) has been cancelled."
                notification_type = 'Info'
            else:
                message = f"Your tax audit ({audit.reference_number}) status has been updated to: {new_status}."
                notification_type = 'Alert'
                
            notification = Notification(
                user_id=account.owner.id,
                title=f"Audit {new_status}",
                message=message,
                notification_type=notification_type
            )
            db.session.add(notification)
            db.session.commit()
            
        flash(f'Audit status updated to {new_status}', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Error updating audit status: {str(e)}', 'danger')
    
    return redirect(url_for('process.view_audit', audit_id=audit_id))

@process_bp.route('/audits/<int:audit_id>/create-case', methods=['POST'])
@login_required
def create_audit_case(audit_id):
    # Get user permissions
    permissions = get_user_permissions(current_user)
    
    # Check if user has admin access
    if 'admin_access' not in permissions:
        flash('You do not have permission to create audit cases', 'danger')
        return redirect(url_for('process.view_audit', audit_id=audit_id))
    
    audit = Audit.query.get_or_404(audit_id)
    
    # Get form data
    tax_period = request.form.get('tax_period')
    description = request.form.get('description')
    
    if not tax_period or not description:
        flash('All fields are required', 'warning')
        return redirect(url_for('process.view_audit', audit_id=audit_id))
    
    # Import necessary models
    from app.models.registration import AuditCase
    from datetime import date
    import uuid
    
    # Generate a unique case number
    case_number = f'AC-{uuid.uuid4().hex[:8].upper()}'
    
    # Create a description that includes the tax period since we don't have separate fields
    case_description = f"Tax Period: {tax_period}\n\nDescription: {description}"
    
    # Update the audit findings field to include this case
    if audit.findings:
        audit.findings += f"\n\nCase {case_number} - {case_description}"
    else:
        audit.findings = f"Case {case_number} - {case_description}"
    
    # Create new audit case
    new_case = AuditCase(
        account_id=audit.account_id,
        audit_id=audit_id,
        case_number=case_number,
        status='Open',
        open_date=date.today()
    )
    
    # Save to database
    try:
        db.session.add(new_case)
        db.session.commit()
        flash(f'New audit case {case_number} created successfully', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Error creating audit case: {str(e)}', 'danger')
    
    return redirect(url_for('process.view_audit', audit_id=audit_id))

@process_bp.route('/collections')
@login_required
def collections():
    # Get user permissions
    permissions = get_user_permissions(current_user)
    
    # Check if user has permission to view collections
    if not any(perm in permissions for perm in ['view_all_accounts', 'admin_access']):
        flash('You do not have permission to view collections', 'danger')
        return redirect(url_for('process.index'))
    
    page = request.args.get('page', 1, type=int)
    per_page = 20
    status = request.args.get('status', '')
    collection_type = request.args.get('type', '')
    
    query = Collection.query
    
    if status:
        query = query.filter(Collection.status == status)
    
    if collection_type:
        query = query.filter(Collection.collection_type == collection_type)
    
    collections = query.order_by(Collection.start_date.desc()).paginate(page=page, per_page=per_page)
    
    # Get statuses and types for filters
    statuses = ['Pending', 'Partial', 'Complete', 'Written Off']
    collection_types = ['Regular', 'Enforcement', 'Installment']
    
    return render_template('processes/collections.html', 
                           collections=collections, 
                           statuses=statuses, 
                           collection_types=collection_types, 
                           selected_status=status, 
                           selected_type=collection_type, 
                           permissions=permissions)

@process_bp.route('/collections/<int:collection_id>')
@login_required
def view_collection(collection_id):
    # Get user permissions
    permissions = get_user_permissions(current_user)
    
    # Check if user has permission to view collections
    if not any(perm in permissions for perm in ['view_all_accounts', 'admin_access']):
        flash('You do not have permission to view collections', 'danger')
        return redirect(url_for('process.index'))
    
    collection = Collection.query.get_or_404(collection_id)
    
    # Get payments for this collection
    payments = collection.payments
    
    # Get enforcements for this collection
    enforcements = Enforcement.query.filter_by(collection_id=collection_id).all()
    
    return render_template('processes/collection_detail.html', 
                           collection=collection, 
                           payments=payments, 
                           enforcements=enforcements, 
                           permissions=permissions)

@process_bp.route('/enforcements')
@login_required
def enforcements():
    # Get user permissions
    permissions = get_user_permissions(current_user)
    
    # Check if user has permission to view enforcements
    if not any(perm in permissions for perm in ['view_all_accounts', 'admin_access']):
        flash('You do not have permission to view enforcements', 'danger')
        return redirect(url_for('process.index'))
    
    page = request.args.get('page', 1, type=int)
    per_page = 20
    status = request.args.get('status', '')
    enforcement_type = request.args.get('type', '')
    
    query = Enforcement.query
    
    if status:
        query = query.filter(Enforcement.status == status)
    
    if enforcement_type:
        query = query.filter(Enforcement.enforcement_type == enforcement_type)
    
    enforcements = query.order_by(Enforcement.start_date.desc()).paginate(page=page, per_page=per_page)
    
    # Get statuses and types for filters
    statuses = ['Initiated', 'In Progress', 'Completed', 'Cancelled']
    enforcement_types = ['Garnishment', 'Lien', 'Seizure']
    
    return render_template('processes/enforcements.html', 
                           enforcements=enforcements, 
                           statuses=statuses, 
                           enforcement_types=enforcement_types, 
                           selected_status=status, 
                           selected_type=enforcement_type, 
                           permissions=permissions)

@process_bp.route('/agreements')
@login_required
def agreements():
    # Get user permissions
    permissions = get_user_permissions(current_user)
    
    page = request.args.get('page', 1, type=int)
    per_page = 20
    status = request.args.get('status', '')
    agreement_type = request.args.get('type', '')
    
    query = Agreement.query
    
    # Filter by user's accounts if not admin/internal
    if not any(perm in permissions for perm in ['view_all_accounts', 'admin_access']):
        user_accounts = Account.query.filter_by(user_id=current_user.id).all()
        account_ids = [account.id for account in user_accounts]
        query = query.filter(Agreement.account_id.in_(account_ids))
    
    if status:
        query = query.filter(Agreement.status == status)
    
    if agreement_type:
        query = query.filter(Agreement.agreement_type == agreement_type)
    
    agreements = query.order_by(Agreement.start_date.desc()).paginate(page=page, per_page=per_page)
    
    # Get statuses and types for filters
    statuses = ['Active', 'Completed', 'Breached', 'Cancelled']
    agreement_types = ['Payment Plan', 'Settlement', 'Amnesty']
    
    return render_template('processes/agreements.html', 
                           agreements=agreements, 
                           statuses=statuses, 
                           agreement_types=agreement_types, 
                           selected_status=status, 
                           selected_type=agreement_type, 
                           permissions=permissions)

@process_bp.route('/agreements/<int:agreement_id>')
@login_required
def view_agreement(agreement_id):
    # Get user permissions
    permissions = get_user_permissions(current_user)
    
    agreement = Agreement.query.get_or_404(agreement_id)
    
    # Check if user has permission to view this agreement
    if not any(perm in permissions for perm in ['view_all_accounts', 'admin_access']):
        user_accounts = Account.query.filter_by(user_id=current_user.id).all()
        account_ids = [account.id for account in user_accounts]
        if agreement.account_id not in account_ids:
            flash('You do not have permission to view this agreement', 'danger')
            return redirect(url_for('process.agreements'))
    
    return render_template('processes/agreement_detail.html', 
                           agreement=agreement, 
                           permissions=permissions)