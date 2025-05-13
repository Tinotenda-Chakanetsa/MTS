from flask import Blueprint, render_template, redirect, url_for, flash, request, jsonify, send_file
from flask_login import login_required, current_user
from app import db
from app.models.user import User, Account
from app.models.tax import TaxType, TaxPeriod, TaxReturn, Payment, Refund
from app.models.process import Request
from app.models.functionality import Document
from app.services.auth_service import get_user_permissions
from datetime import datetime
import uuid
import os
import io

e_services_bp = Blueprint('e_services', __name__, url_prefix='/e-services')

@e_services_bp.route('/')
@login_required
def index():
    # Get user permissions
    permissions = get_user_permissions(current_user)
    
    return render_template('e_services/index.html', permissions=permissions)

@e_services_bp.route('/account-management')
@login_required
def account_management():
    # Get user permissions
    permissions = get_user_permissions(current_user)
    
    # Get accounts accessible to the user
    if 'view_all_accounts' in permissions:
        accounts = Account.query.all()
    else:
        accounts = Account.query.filter_by(user_id=current_user.id).all()
    
    return render_template('e_services/account_management.html', 
                           accounts=accounts, 
                           permissions=permissions)

# Route to add a new taxpayer account
@e_services_bp.route('/account-management/add', methods=['GET', 'POST'])
@login_required
def add_account():
    from app.forms.e_services_forms import AddAccountForm
    form = AddAccountForm()
    if form.validate_on_submit():
        from app.models.user import Account
        existing = Account.query.filter_by(account_number=form.account_number.data).first()
        if existing:
            flash('An account with this number already exists.', 'danger')
            return render_template('e_services/add_account.html', form=form)
        account = Account(
            name=form.name.data,
            account_number=form.account_number.data,
            user_id=current_user.id
        )
        db.session.add(account)
        db.session.commit()
        flash('Account created successfully!', 'success')
        return redirect(url_for('e_services.account_management'))
    return render_template('e_services/add_account.html', form=form)

@e_services_bp.route('/account/<int:account_id>')
@login_required
def view_account(account_id):
    # Get user permissions
    permissions = get_user_permissions(current_user)
    
    # Check if user has permission to view this account
    if not 'view_all_accounts' in permissions:
        user_accounts = Account.query.filter_by(user_id=current_user.id).all()
        account_ids = [account.id for account in user_accounts]
        if account_id not in account_ids:
            flash('You do not have permission to view this account', 'danger')
            return redirect(url_for('e_services.account_management'))
    
    account = Account.query.get_or_404(account_id)
    
    # Get tax obligations for the account
    from app.models.tax import TaxObligation
    tax_obligations = TaxObligation.query.filter_by(account_id=account_id).all()
    
    # Get tax returns for the account
    tax_returns = TaxReturn.query.filter_by(account_id=account_id).order_by(TaxReturn.created_at.desc()).limit(5).all()
    
    # Get payments for the account
    payments = Payment.query.join(TaxReturn).filter(TaxReturn.account_id == account_id).order_by(Payment.payment_date.desc()).limit(5).all()
    
    return render_template('e_services/account_detail.html', 
                           account=account, 
                           tax_obligations=tax_obligations, 
                           tax_returns=tax_returns, 
                           payments=payments, 
                           permissions=permissions)

@e_services_bp.route('/two-factor')
@login_required
def two_factor_authentication():
    # Check if 2FA is already enabled
    is_enabled = current_user.two_factor_enabled
    
    return render_template('e_services/two_factor.html', is_enabled=is_enabled)

@e_services_bp.route('/security')
@login_required
def security():
    return render_template('e_services/security.html')

@e_services_bp.route('/registration')
@login_required
def registration():
    # Get user permissions
    permissions = get_user_permissions(current_user)
    
    # Get registration types based on user type
    registration_types = []
    
    if current_user.user_type.name == 'Individual' or 'view_all_accounts' in permissions:
        registration_types.append({'id': 'individual', 'name': 'Individual Registration'})
    
    if current_user.user_type.name == 'Non-Individual' or 'view_all_accounts' in permissions:
        registration_types.append({'id': 'non_individual', 'name': 'Business Registration'})
    
    if current_user.user_type.name in ['Individual', 'Non-Individual'] or 'view_all_accounts' in permissions:
        registration_types.append({'id': 'sole_proprietor', 'name': 'Sole Proprietor Registration'})
        registration_types.append({'id': 'property', 'name': 'Property Registration'})
    
    return render_template('e_services/registration.html', 
                           registration_types=registration_types, 
                           permissions=permissions)

@e_services_bp.route('/self-assessment')
@login_required
def self_assessment():
    # Get user permissions
    permissions = get_user_permissions(current_user)
    
    # Get accounts accessible to the user
    if 'view_all_accounts' in permissions:
        accounts = Account.query.all()
    else:
        accounts = Account.query.filter_by(user_id=current_user.id).all()
    
    # Get tax types
    tax_types = TaxType.query.all()
    
    return render_template('e_services/self_assessment.html', 
                           accounts=accounts, 
                           tax_types=tax_types, 
                           permissions=permissions)

@e_services_bp.route('/returns-filing')
@login_required
def returns_filing():
    # Get user permissions
    permissions = get_user_permissions(current_user)
    
    # Get accounts accessible to the user
    if 'view_all_accounts' in permissions:
        accounts = Account.query.all()
    else:
        accounts = Account.query.filter_by(user_id=current_user.id).all()
    
    # Get tax types
    tax_types = TaxType.query.all()
    
    # Get current tax periods
    today = datetime.utcnow().date()
    current_periods = TaxPeriod.query.filter(
        TaxPeriod.start_date <= today,
        TaxPeriod.end_date >= today,
        TaxPeriod.status == 'Open'
    ).all()
    
    return render_template('e_services/returns_filing.html', 
                           accounts=accounts, 
                           tax_types=tax_types, 
                           current_periods=current_periods, 
                           permissions=permissions)

@e_services_bp.route('/tax-payments')
@login_required
def tax_payments():
    # Get user permissions
    permissions = get_user_permissions(current_user)
    
    # Get accounts accessible to the user
    if 'view_all_accounts' in permissions:
        accounts = Account.query.all()
    else:
        accounts = Account.query.filter_by(user_id=current_user.id).all()
    
    # Get pending tax returns (not fully paid)
    pending_returns = []
    
    for account in accounts:
        returns = TaxReturn.query.filter_by(account_id=account.id).filter(TaxReturn.status != 'Finalized').all()
        for tax_return in returns:
            # Calculate remaining balance
            total_paid = db.session.query(db.func.sum(Payment.amount)).filter_by(tax_return_id=tax_return.id).scalar() or 0
            remaining = tax_return.due_amount - total_paid
            
            if remaining > 0:
                pending_returns.append({
                    'id': tax_return.id,
                    'reference': tax_return.reference_number,
                    'tax_type': tax_return.tax_type.name,
                    'due_date': tax_return.period.due_date,
                    'total_amount': tax_return.due_amount,
                    'paid_amount': total_paid,
                    'remaining': remaining,
                    'account': account.name
                })
    
    return render_template('e_services/tax_payments.html', 
                           accounts=accounts, 
                           pending_returns=pending_returns, 
                           permissions=permissions)

@e_services_bp.route('/filing-objections')
@login_required
def filing_objections():
    # Get user permissions
    permissions = get_user_permissions(current_user)
    
    # Get accounts accessible to the user
    if 'view_all_accounts' in permissions:
        accounts = Account.query.all()
    else:
        accounts = Account.query.filter_by(user_id=current_user.id).all()
    
    # Get eligible tax returns for objections
    eligible_returns = []
    
    for account in accounts:
        returns = TaxReturn.query.filter_by(account_id=account.id).filter(TaxReturn.status.in_(['Filed', 'Assessed'])).all()
        for tax_return in returns:
            # Check if there's no pending objection
            from app.models.tax import Objection
            pending_objection = Objection.query.filter_by(tax_return_id=tax_return.id).filter(Objection.status.in_(['Pending', 'In Progress'])).first()
            
            if not pending_objection:
                eligible_returns.append({
                    'id': tax_return.id,
                    'reference': tax_return.reference_number,
                    'tax_type': tax_return.tax_type.name,
                    'filing_date': tax_return.filing_date,
                    'amount': tax_return.due_amount,
                    'account': account.name
                })
    
    return render_template('e_services/filing_objections.html', 
                           accounts=accounts, 
                           eligible_returns=eligible_returns, 
                           permissions=permissions)

@e_services_bp.route('/request-refunds')
@login_required
def request_refunds():
    # Get user permissions
    permissions = get_user_permissions(current_user)
    
    # Get accounts accessible to the user
    if 'view_all_accounts' in permissions:
        accounts = Account.query.all()
    else:
        accounts = Account.query.filter_by(user_id=current_user.id).all()
    
    # Get refund history
    refund_history = []
    
    for account in accounts:
        refunds = Refund.query.filter_by(account_id=account.id).order_by(Refund.request_date.desc()).all()
        for refund in refunds:
            refund_history.append({
                'id': refund.id,
                'reference': refund.reference_number,
                'amount': refund.amount,
                'request_date': refund.request_date,
                'status': refund.status,
                'account': account.name
            })
    
    return render_template('e_services/request_refunds.html', 
                           accounts=accounts, 
                           refund_history=refund_history, 
                           permissions=permissions)

@e_services_bp.route('/tracking')
@login_required
def tracking():
    # Get user permissions
    permissions = get_user_permissions(current_user)
    
    # Get reference number from query parameter
    reference = request.args.get('reference')
    result = None
    
    if reference:
        # Check tax returns
        tax_return = TaxReturn.query.filter_by(reference_number=reference).first()
        if tax_return:
            result = {
                'type': 'Tax Return',
                'reference': tax_return.reference_number,
                'status': tax_return.status,
                'date': tax_return.filing_date,
                'details': f'{tax_return.tax_type.name} for period {tax_return.period.period_code}',
                'amount': tax_return.due_amount
            }
        
        # Check payments
        if not result:
            payment = Payment.query.filter_by(reference_number=reference).first()
            if payment:
                result = {
                    'type': 'Payment',
                    'reference': payment.reference_number,
                    'status': payment.status,
                    'date': payment.payment_date,
                    'details': f'Payment for {payment.tax_return.reference_number}',
                    'amount': payment.amount
                }
        
        # Check refunds
        if not result:
            refund = Refund.query.filter_by(reference_number=reference).first()
            if refund:
                result = {
                    'type': 'Refund',
                    'reference': refund.reference_number,
                    'status': refund.status,
                    'date': refund.request_date,
                    'details': f'Refund for account {refund.account.account_number}',
                    'amount': refund.amount
                }
        
        # Check requests
        if not result:
            request_obj = Request.query.filter_by(reference_number=reference).first()
            if request_obj:
                result = {
                    'type': 'Request',
                    'reference': request_obj.reference_number,
                    'status': request_obj.status,
                    'date': request_obj.submission_date,
                    'details': f'{request_obj.request_type} for account {request_obj.account.account_number}',
                    'amount': None
                }
    
    return render_template('e_services/tracking.html', 
                           reference=reference, 
                           result=result, 
                           permissions=permissions)

@e_services_bp.route('/deregistration')
@login_required
def deregistration():
    # Get user permissions
    permissions = get_user_permissions(current_user)
    
    # Get accounts accessible to the user
    if 'view_all_accounts' in permissions:
        accounts = Account.query.all()
    else:
        accounts = Account.query.filter_by(user_id=current_user.id).all()
    
    return render_template('e_services/deregistration.html', 
                           accounts=accounts, 
                           permissions=permissions)

@e_services_bp.route('/e-forms')
@login_required
def e_forms():
    # Get available forms/documents
    forms = Document.query.filter_by(document_type='Form', status='Active').all()
    
    return render_template('e_services/e_forms.html', forms=forms)

@e_services_bp.route('/download-form/<int:form_id>')
@login_required
def download_form(form_id):
    form = Document.query.get_or_404(form_id)
    
    # In a real application, this would serve the actual file
    # For this implementation, we'll create a simple text file
    content = f"This is the content of {form.title}\n\nForm ID: {form.id}\nType: {form.document_type}\n\n{form.content or 'No content available'}"
    
    buffer = io.BytesIO()
    buffer.write(content.encode('utf-8'))
    buffer.seek(0)
    
    return send_file(
        buffer,
        as_attachment=True,
        download_name=f"{form.title.replace(' ', '_')}.txt",
        mimetype='text/plain'
    )

# Documents listing
@e_services_bp.route('/documents')
@login_required
def documents():
    # Get user permissions
    permissions = get_user_permissions(current_user)
    
    # Get available documents
    documents = Document.query.filter_by(status='Active').all()
    
    return render_template('e_services/documents.html', 
                           documents=documents, 
                           permissions=permissions)