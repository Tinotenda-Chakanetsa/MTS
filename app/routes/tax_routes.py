from flask import Blueprint, render_template, redirect, url_for, flash, request, jsonify
from flask_login import login_required, current_user
from app import db
from datetime import datetime
from app.models.user import User, Account
from app.models.tax import TaxType, TaxPeriod, TaxReturn, Payment, Refund, Objection
from app.models.process import Person, Organization, Property, Request, Audit, Collection
from app.models.registration import TaxpayerLedger
from app.models.functionality import Notification
from app.services.auth_service import get_user_permissions
from app.services.tax_service import generate_reference_number
from datetime import datetime, timedelta
import uuid
from app.models.functionality import Notification
from decimal import Decimal
from sqlalchemy import or_

tax_bp = Blueprint('tax', __name__, url_prefix='/tax')

@tax_bp.route('/')
@login_required
def index():
    # Get user permissions
    permissions = get_user_permissions(current_user)
    
    # Get accounts accessible to the user
    if 'view_all_accounts' in permissions:
        accounts = Account.query.all()
    else:
        accounts = Account.query.filter_by(user_id=current_user.id).all()
    
    # Get tax types
    tax_types = TaxType.query.all()
    # Build periods with a visible label for dropdown
    periods = []
    for p in TaxPeriod.query.order_by(TaxPeriod.start_date.desc()).all():
        label = f"{p.period_code} (" \
                f"{p.start_date.strftime('%d %b')} - {p.end_date.strftime('%d %b')})"
        periods.append(type('Period', (), {
            'id': p.id,
            'label': label
        }))
    
    return render_template('tax/index.html', 
                           accounts=accounts, 
                           tax_types=tax_types, 
                           permissions=permissions)

@tax_bp.route('/types')
@login_required
def tax_types():
    # Get tax types
    core_taxes = TaxType.query.filter_by(is_core=True).all()
    non_core_taxes = TaxType.query.filter_by(is_core=False).all()
    
    return render_template('tax/tax_types.html', 
                           core_taxes=core_taxes, 
                           non_core_taxes=non_core_taxes)

@tax_bp.route('/periods')
@login_required
def tax_periods():
    tax_type_id = request.args.get('tax_type_id', type=int)
    
    query = TaxPeriod.query
    if tax_type_id:
        query = query.filter_by(tax_type_id=tax_type_id)
    
    tax_periods = query.order_by(TaxPeriod.start_date.desc()).all()
    tax_types = TaxType.query.all()
    # Build periods with a visible label for dropdown
    periods = []
    for p in TaxPeriod.query.order_by(TaxPeriod.start_date.desc()).all():
        label = f"{p.period_code} (" \
                f"{p.start_date.strftime('%d %b')} - {p.end_date.strftime('%d %b')})"
        periods.append(type('Period', (), {
            'id': p.id,
            'label': label
        }))
    
    return render_template('tax/tax_periods.html', 
                           tax_periods=tax_periods, 
                           tax_types=tax_types, 
                           selected_tax_type_id=tax_type_id)

@tax_bp.route('/returns')
@login_required
def tax_returns():
    permissions = get_user_permissions(current_user)
    account_id = request.args.get('account_id', type=int)
    tax_type_id = request.args.get('tax_type_id', type=int)
    status = request.args.get('status')
    page = request.args.get('page', 1, type=int)
    per_page = 20
    
    # Build query based on filters and permissions
    query = TaxReturn.query
    
    if account_id:
        query = query.filter_by(account_id=account_id)
    elif not 'view_all_accounts' in permissions:
        # If not admin/internal, only show returns for user's accounts
        user_accounts = Account.query.filter_by(user_id=current_user.id).all()
        account_ids = [account.id for account in user_accounts]
        # Include returns under audit assigned to the current user
        audited_return_ids = [a.tax_return_id for a in Audit.query.filter_by(auditor_id=current_user.id).all()]
        query = query.filter(or_(TaxReturn.account_id.in_(account_ids),
                                 TaxReturn.id.in_(audited_return_ids)))
    
    if tax_type_id:
        query = query.filter_by(tax_type_id=tax_type_id)
    
    if status:
        query = query.filter_by(status=status)
    
    # Get paginated results
    tax_returns = query.order_by(TaxReturn.created_at.desc()).paginate(page=page, per_page=per_page)
    
    # Display the due amount from tax return directly
    # The due amount has already been updated during payments
    for tr in tax_returns.items:
        # Just use the existing due_amount field directly
        tr.remaining_amount = tr.due_amount
    
    # Simpler approach to mark tax returns under audit
        # Get active audits
    active_audits = Audit.query.filter(Audit.status != 'Completed').all()
    
    # Create a dictionary to store tax returns that are actually under audit
    # Map from account_id -> set of tax_return_ids under audit
    # We'll query for tax returns that have the same reference number as the ones
    # mentioned in audit notifications
    account_tax_returns_under_audit = {}
    
    # Get notifications about tax returns under audit to identify specific returns
    from app.models.functionality import Notification
    audit_notifications = Notification.query.filter(
        Notification.title == "Tax Return Under Audit"
    ).all()
    
    # Extract tax return reference numbers from the notifications
    tax_return_refs_under_audit = set()
    for notification in audit_notifications:
        # Parse the notification message to extract the tax return reference
        # Example message: "Your tax return REF-12345 for Personal Income Tax type..."
        message = notification.message
        if "Your tax return " in message and " for " in message:
            ref = message.split("Your tax return ")[1].split(" for ")[0].strip()
            tax_return_refs_under_audit.add(ref)
    
    # Get all tax returns that match these references
    if tax_return_refs_under_audit:
        specific_returns_under_audit = TaxReturn.query.filter(
            TaxReturn.reference_number.in_(list(tax_return_refs_under_audit))
        ).all()
        
        # Group by account_id
        for tr in specific_returns_under_audit:
            if tr.account_id not in account_tax_returns_under_audit:
                account_tax_returns_under_audit[tr.account_id] = set()
            account_tax_returns_under_audit[tr.account_id].add(tr.id)
    
    # Mark tax returns as under audit if they are specifically targeted
    for tr in tax_returns.items:
        if tr.account_id in account_tax_returns_under_audit and tr.id in account_tax_returns_under_audit[tr.account_id]:
            tr.is_under_audit = True
        else:
            tr.is_under_audit = False
    
    # Get filter options
    if 'view_all_accounts' in permissions:
        accounts = Account.query.all()
    else:
        accounts = Account.query.filter_by(user_id=current_user.id).all()
    
    tax_types = TaxType.query.all()
    # Build periods with a visible label for dropdown
    periods = []
    for p in TaxPeriod.query.order_by(TaxPeriod.start_date.desc()).all():
        label = f"{p.period_code} (" \
                f"{p.start_date.strftime('%d %b')} - {p.end_date.strftime('%d %b')})"
        periods.append(type('Period', (), {
            'id': p.id,
            'label': label
        }))
    statuses = ['Not Filed', 'Filed', 'Assessed', 'Finalized']
    
    return render_template('tax/tax_returns.html', 
                           tax_returns=tax_returns, 
                           accounts=accounts, 
                           tax_types=tax_types, 
                           statuses=statuses, 
                           selected_account_id=account_id, 
                           selected_tax_type_id=tax_type_id, 
                           selected_status=status,
                           permissions=permissions)

@tax_bp.route('/returns/<int:return_id>')
@login_required
def view_tax_return(return_id):
    tax_return = TaxReturn.query.get_or_404(return_id)
    permissions = get_user_permissions(current_user)
    
    # Check if user has permission to view this return
    if not 'view_all_accounts' in permissions:
        user_accounts = Account.query.filter_by(user_id=current_user.id).all()
        account_ids = [account.id for account in user_accounts]
        if tax_return.account_id not in account_ids:
            flash('You do not have permission to view this tax return', 'danger')
            return redirect(url_for('tax.tax_returns'))
    
    # Get related payments
    payments = Payment.query.filter_by(tax_return_id=tax_return.id).all()
    
    # Get related objections
    objections = Objection.query.filter_by(tax_return_id=tax_return.id).all()
    # Compute remaining due amount for display
    total_paid = db.session.query(db.func.sum(Payment.amount)).filter_by(tax_return_id=tax_return.id).scalar() or Decimal('0')
    tax_return.remaining_amount = tax_return.due_amount - total_paid
    
    return render_template('tax/tax_return_detail.html', 
                           tax_return=tax_return, 
                           payments=payments, 
                           objections=objections,
                           permissions=permissions)

@tax_bp.route('/returns/file', methods=['GET', 'POST'])
@login_required
def file_tax_return():
    permissions = get_user_permissions(current_user)
    
    # Check if user has permission to file returns
    if not any(perm in permissions for perm in ['file_individual_returns', 'file_business_returns']):
        flash('You do not have permission to file tax returns', 'danger')
        return redirect(url_for('tax.tax_returns'))
    
    # Get user's accounts or all accounts for admin/internal users
    if 'view_all_accounts' in permissions:
        accounts = Account.query.all()
    else:
        accounts = Account.query.filter_by(user_id=current_user.id).all()
    
    # Get tax types
    tax_types = TaxType.query.all()
    # Build periods with a visible label for dropdown, one per quarter
    periods = []
    unique_codes = set()
    for p in TaxPeriod.query.order_by(TaxPeriod.start_date.desc()).all():
        if p.period_code in unique_codes:
            continue
        unique_codes.add(p.period_code)
        label = f"{p.period_code} (" \
                f"{p.start_date.strftime('%d %b')} - {p.end_date.strftime('%d %b')})"
        periods.append(type('Period', (), {
            'id': p.id,
            'label': label
        }))
    
    if request.method == 'POST':
        account_id = request.form.get('account_id', type=int)
        tax_type_id = request.form.get('tax_type_id', type=int)
        tax_period_id = request.form.get('period_id', type=int)
        # Parse amount as Decimal to avoid float/Decimal arithmetic errors
        amount = Decimal(str(request.form.get('amount', type=float)))
        
        # Validate inputs
        if not all([account_id, tax_type_id, tax_period_id, amount is not None]):
            flash('All fields are required', 'danger')
            return render_template('tax/file_return.html', 
                                   accounts=accounts, 
                                   tax_types=tax_types, 
                                   periods=periods,
                                   permissions=permissions)
        
        # Use entered amount as due amount
        due_amount = amount
        
        # Generate reference number
        reference_number = generate_reference_number()
        
        # Create tax return
        tax_return = TaxReturn(
            account_id=account_id,
            tax_type_id=tax_type_id,
            tax_period_id=tax_period_id,
            filing_date=datetime.utcnow(),
            due_amount=due_amount,
            status='Filed',
            assessment_type='Self',
            reference_number=reference_number
        )

        # Auto-flag suspicious returns
        from app.services.tax_service import auto_flag_return
        auto_flag_return(tax_return)
        
        db.session.add(tax_return)
        db.session.commit()
        
        # Create ledger entry
        ledger_entry = TaxpayerLedger(
            account_id=account_id,
            tax_type_id=tax_type_id,
            tax_period_id=tax_period_id,
            transaction_date=datetime.utcnow().date(),
            transaction_type='Assessment',
            description=f'Self-assessment for {tax_return.tax_type.name}',
            debit_amount=due_amount,
            credit_amount=0,
            balance=due_amount,
            reference_number=reference_number
        )
        
        db.session.add(ledger_entry)
        db.session.commit()
        
        # Get account and tax type details for the notification
        account = Account.query.get(account_id)
        tax_type = TaxType.query.get(tax_type_id)
        period = TaxPeriod.query.get(tax_period_id)
        
        # Create notification for the user
        user_notification = Notification(
            user_id=current_user.id,
            title="Tax Return Filed",
            message=f"Your {tax_type.name} tax return ({reference_number}) for {period.period_code} has been filed. Amount due: ${due_amount}.",
            notification_type='Tax'
        )
        db.session.add(user_notification)
        
        # Create notifications for all admin users
        admin_users = User.query.filter_by(is_admin=True).all()
        for admin in admin_users:
            admin_notification = Notification(
                user_id=admin.id,
                title="New Tax Return Filed",
                message=f"A new {tax_type.name} tax return ({reference_number}) has been filed by {current_user.username} for account {account.account_number}. Amount: ${due_amount}.",
                notification_type='Alert'
            )
            db.session.add(admin_notification)
        
        db.session.commit()
        
        flash('Tax return filed successfully', 'success')
        return redirect(url_for('tax.view_tax_return', return_id=tax_return.id))
    
    return render_template('tax/file_return.html', 
                           accounts=accounts, 
                           tax_types=tax_types, 
                           periods=periods,
                           permissions=permissions)

@tax_bp.route('/payments')
@login_required
def payments():
    permissions = get_user_permissions(current_user)
    account_id = request.args.get('account_id', type=int)
    status = request.args.get('status')
    page = request.args.get('page', 1, type=int)
    per_page = 20
    
    # Build query based on filters and permissions
    query = Payment.query
    
    if account_id:
        query = query.join(TaxReturn).filter(TaxReturn.account_id == account_id)
    elif not 'view_all_accounts' in permissions:
        # If not admin/internal, only show payments for user's accounts
        user_accounts = Account.query.filter_by(user_id=current_user.id).all()
        account_ids = [account.id for account in user_accounts]
        query = query.join(TaxReturn).filter(TaxReturn.account_id.in_(account_ids))
    
    if status:
        query = query.filter_by(status=status)
    
    # Get paginated results
    payments = query.order_by(Payment.payment_date.desc()).paginate(page=page, per_page=per_page)
    
    # Get filter options
    if 'view_all_accounts' in permissions:
        accounts = Account.query.all()
    else:
        accounts = Account.query.filter_by(user_id=current_user.id).all()
    
    statuses = ['Pending', 'Completed', 'Failed', 'Refunded']
    
    return render_template('tax/make_payment_list.html', 
                           payments=payments, 
                           accounts=accounts, 
                           statuses=statuses, 
                           selected_account_id=account_id, 
                           selected_status=status,
                           permissions=permissions)

@tax_bp.route('/payments/make', methods=['GET', 'POST'])
@login_required
def make_payment():
    permissions = get_user_permissions(current_user)
    tax_return_id = request.args.get('tax_return_id', type=int)
    
    if tax_return_id:
        tax_return = TaxReturn.query.get_or_404(tax_return_id)
        
        # Check if user has permission to pay for this return
        if not 'view_all_accounts' in permissions:
            user_accounts = Account.query.filter_by(user_id=current_user.id).all()
            account_ids = [account.id for account in user_accounts]
            if tax_return.account_id not in account_ids:
                flash('You do not have permission to make payments for this tax return', 'danger')
                return redirect(url_for('tax.tax_returns'))
    else:
        tax_return = None
    
    # Get user's tax returns or all returns for admin/internal users
    if 'view_all_accounts' in permissions:
        if not tax_return:
            tax_returns = TaxReturn.query.filter(TaxReturn.status != 'Finalized').all()
        else:
            tax_returns = [tax_return]
    else:
        user_accounts = Account.query.filter_by(user_id=current_user.id).all()
        account_ids = [account.id for account in user_accounts]
        if not tax_return:
            tax_returns = TaxReturn.query.filter(TaxReturn.account_id.in_(account_ids), TaxReturn.status != 'Finalized').all()
        elif tax_return.account_id in account_ids:
            tax_returns = [tax_return]
        else:
            tax_returns = []
    
    if request.method == 'POST':
        tax_return_id = request.form.get('tax_return_id', type=int)
        # Parse amount as Decimal to avoid float/Decimal arithmetic errors
        amount = Decimal(str(request.form.get('amount', type=float)))
        payment_method = request.form.get('payment_method')
        
        # Validate inputs
        if not all([tax_return_id, amount, payment_method]):
            flash('All fields are required', 'danger')
            return render_template('tax/make_payment.html', 
                                   tax_returns=tax_returns, 
                                   selected_tax_return=tax_return, 
                                   permissions=permissions)
        
        tax_return = TaxReturn.query.get_or_404(tax_return_id)
        
        # Generate reference number
        reference_number = f"PMT-{uuid.uuid4().hex[:8].upper()}"
        
        # Create payment
        payment = Payment(
            tax_return_id=tax_return_id,
            amount=amount,
            payment_date=datetime.utcnow(),
            payment_method=payment_method,
            reference_number=reference_number,
            status='Completed'
        )
        
        db.session.add(payment)
        
        # Create ledger entry
        ledger_entry = TaxpayerLedger(
            account_id=tax_return.account_id,
            tax_type_id=tax_return.tax_type_id,
            tax_period_id=tax_return.tax_period_id,
            transaction_date=datetime.utcnow().date(),
            transaction_type='Payment',
            description=f'Payment for {tax_return.reference_number}',
            debit_amount=0,
            credit_amount=amount,
            # Ensure both sides are Decimal to avoid type errors
            balance=tax_return.due_amount - Decimal(str(amount)),  # This is simplified, should consider previous payments
            reference_number=reference_number
        )
        
        db.session.add(ledger_entry)
        
        # Get total amount already paid for this tax return
        already_paid = db.session.query(db.func.sum(Payment.amount)).filter_by(tax_return_id=tax_return_id).scalar() or 0
        
        # Convert payment amount to Decimal to ensure precise calculation
        payment_amount = Decimal(str(amount))
        
        # Check if this payment results in an overpayment
        if payment_amount > tax_return.due_amount:
            # Calculate the overpayment amount
            overpayment_amount = payment_amount - tax_return.due_amount
            
            # Create a credit note for the account
            credit_reference = f"CR-{uuid.uuid4().hex[:8].upper()}"
            credit_note = TaxpayerLedger(
                account_id=tax_return.account_id,
                tax_type_id=tax_return.tax_type_id,
                tax_period_id=tax_return.tax_period_id,
                transaction_date=datetime.utcnow().date(),
                transaction_type='Credit',
                description=f'Credit from overpayment on {tax_return.reference_number}',
                debit_amount=0,
                credit_amount=overpayment_amount,
                balance=Decimal('0'),
                reference_number=credit_reference
            )
            db.session.add(credit_note)
            
            # Create notification about the overpayment
            notification = Notification(
                user_id=current_user.id,
                title='Overpayment Detected',
                message=f'You have overpaid tax return {tax_return.reference_number} by ${overpayment_amount:.2f}. This amount has been credited to your account.',
                notification_type='Alert'
            )
            db.session.add(notification)
            
            # Set the tax return to finalized with zero due amount
            tax_return.due_amount = Decimal('0')
            tax_return.status = 'Finalized'
            
            # Add an extra message to the flash notification
            flash(f'Overpayment of ${overpayment_amount:.2f} detected and credited to your account', 'info')
        else:
            # Normal payment processing (no overpayment)
            # Calculate new due amount after this payment
            new_due_amount = max(Decimal('0'), tax_return.due_amount - payment_amount)
            
            # Update the tax return's due amount
            tax_return.due_amount = new_due_amount
            
            # Only change status to 'Finalized' if due amount is exactly zero
            if new_due_amount == Decimal('0'):
                tax_return.status = 'Finalized'
            else:
                # Ensure status remains 'Filed' if not zero
                if tax_return.status not in ['Filed', 'Assessed']:
                    tax_return.status = 'Filed'
        
        db.session.commit()
        
        flash('Payment processed successfully', 'success')
        return redirect(url_for('tax.view_tax_return', return_id=tax_return_id))
    
    return render_template('tax/make_payment.html', 
                           tax_returns=tax_returns, 
                           selected_tax_return=tax_return, 
                           permissions=permissions)

@tax_bp.route('/payments/<int:payment_id>', methods=['GET', 'POST'])
@login_required
def payment_detail(payment_id):
    permissions = get_user_permissions(current_user)
    payment = Payment.query.get_or_404(payment_id)
    # Permission check
    if 'view_all_accounts' not in permissions:
        if payment.tax_return.account.user_id != current_user.id:
            flash('You do not have permission to view this payment', 'danger')
            return redirect(url_for('tax.payments'))
    if request.method == 'POST':
        action = request.form.get('action')
        if action == 'approve':
            payment.status = 'Completed'
            # update due amount
            tr = payment.tax_return
            
            # Check if this payment results in an overpayment
            if payment.amount > tr.due_amount:
                # Calculate the overpayment amount
                overpayment_amount = payment.amount - tr.due_amount
                
                # Create a credit note for the account
                credit_reference = f"CR-{uuid.uuid4().hex[:8].upper()}"
                credit_note = TaxpayerLedger(
                    account_id=tr.account_id,
                    tax_type_id=tr.tax_type_id,
                    tax_period_id=tr.tax_period_id,
                    transaction_date=datetime.utcnow().date(),
                    transaction_type='Credit',
                    description=f'Credit from overpayment on {tr.reference_number}',
                    debit_amount=0,
                    credit_amount=overpayment_amount,
                    balance=Decimal('0'),
                    reference_number=credit_reference
                )
                db.session.add(credit_note)
                
                # Create notification for the account owner
                user_id = tr.account.user_id
                notification = Notification(
                    user_id=user_id,
                    title='Overpayment Detected',
                    message=f'You have overpaid tax return {tr.reference_number} by ${overpayment_amount:.2f}. This amount has been credited to your account.',
                    notification_type='Alert'
                )
                db.session.add(notification)
                
                # Set the tax return to finalized with zero due amount
                tr.due_amount = Decimal('0')
                tr.status = 'Finalized'
                
                # Add an extra message
                flash(f'Overpayment of ${overpayment_amount:.2f} detected and credited to account', 'info')
            else:
                # Normal payment processing (no overpayment)
                # Calculate new due amount
                new_due_amount = max(Decimal('0'), tr.due_amount - payment.amount)
                tr.due_amount = new_due_amount
                
                # Only change status to 'Finalized' if due amount is exactly zero
                if new_due_amount == Decimal('0'):
                    tr.status = 'Finalized'
                else:
                    # Ensure status remains 'Filed' if not zero
                    if tr.status not in ['Filed', 'Assessed']:
                        tr.status = 'Filed'
                    
            db.session.commit()
            flash('Payment approved successfully', 'success')
        elif action == 'decline':
            payment.status = 'Failed'
            db.session.commit()
            flash('Payment declined', 'warning')
        return redirect(url_for('tax.payments'))
    return render_template('tax/payment_detail.html', payment=payment, permissions=permissions)

@tax_bp.route('/refunds')
@login_required
def refunds():
    permissions = get_user_permissions(current_user)
    account_id = request.args.get('account_id', type=int)
    status = request.args.get('status')
    page = request.args.get('page', 1, type=int)
    per_page = 20
    
    # Build query based on filters and permissions
    query = Refund.query
    
    if account_id:
        query = query.filter_by(account_id=account_id)
    elif not 'view_all_accounts' in permissions:
        # If not admin/internal, only show refunds for user's accounts
        user_accounts = Account.query.filter_by(user_id=current_user.id).all()
        account_ids = [account.id for account in user_accounts]
        query = query.filter(Refund.account_id.in_(account_ids))
    
    if status:
        query = query.filter_by(status=status)
    
    # Get paginated results
    refunds = query.order_by(Refund.request_date.desc()).paginate(page=page, per_page=per_page)
    
    # Get filter options
    if 'view_all_accounts' in permissions:
        accounts = Account.query.all()
    else:
        accounts = Account.query.filter_by(user_id=current_user.id).all()
    
    statuses = ['Pending', 'Approved', 'Rejected', 'Paid']
    
    return render_template('tax/request_refund_list.html', 
                           refunds=refunds, 
                           accounts=accounts, 
                           statuses=statuses, 
                           selected_account_id=account_id, 
                           selected_status=status,
                           permissions=permissions)

@tax_bp.route('/refunds/request', methods=['GET', 'POST'])
@login_required
def request_refund():
    permissions = get_user_permissions(current_user)
    
    # Get user's accounts or all accounts for admin/internal users
    if 'view_all_accounts' in permissions:
        accounts = Account.query.all()
    else:
        accounts = Account.query.filter_by(user_id=current_user.id).all()
    
    # Get tax types for dropdown
    tax_types = TaxType.query.all()
    
    # Get unique tax periods with formatted labels
    periods = []
    
    # Get distinct period codes first
    distinct_period_codes = db.session.query(TaxPeriod.period_code).distinct().all()
    distinct_period_codes = [code[0] for code in distinct_period_codes]
    
    # For each distinct period code, get one tax period record
    for period_code in distinct_period_codes:
        # Get the first period with this code
        period = TaxPeriod.query.filter_by(period_code=period_code).first()
        if period:
            periods.append({
                'id': period.id,
                'label': f"{period.period_code} ({period.start_date.strftime('%d %b %Y')} - {period.end_date.strftime('%d %b %Y')})"
            })
    
    # Sort periods by start date (most recent first)
    periods = sorted(periods, key=lambda x: db.session.query(TaxPeriod.start_date)
                                           .filter(TaxPeriod.id == x['id']).first()[0], 
                     reverse=True)
    
    if request.method == 'POST':
        account_id = request.form.get('account_id', type=int)
        # Parse amount as Decimal to avoid float/Decimal arithmetic errors
        amount = Decimal(str(request.form.get('amount', type=float)))
        reason = request.form.get('reason')
        
        # Validate inputs
        if not all([account_id, amount, reason]):
            flash('All fields are required', 'danger')
            return render_template('tax/request_refund.html', 
                                   accounts=accounts,
                                   tax_types=tax_types,
                                   periods=periods, 
                                   permissions=permissions)
        
        # Generate reference number
        reference_number = f"REF-{uuid.uuid4().hex[:8].upper()}"
        
        # Create refund request
        refund = Refund(
            account_id=account_id,
            amount=amount,
            reason=reason,
            reference_number=reference_number
        )
        
        db.session.add(refund)
        db.session.commit()
        
        # Get the account details for the notification
        account = Account.query.get(account_id)
        
        # Create notification for the user
        user_notification = Notification(
            user_id=current_user.id,
            title="Refund Request Submitted",
            message=f"Your refund request ({reference_number}) for ${amount} has been submitted and is pending approval.",
            notification_type='Tax'
        )
        db.session.add(user_notification)
        
        # Create notifications for all admin users
        admin_users = User.query.filter_by(is_admin=True).all()
        for admin in admin_users:
            admin_notification = Notification(
                user_id=admin.id,
                title="New Refund Request",
                message=f"A new refund request ({reference_number}) for ${amount} has been submitted by {current_user.username} for account {account.account_number}.",
                notification_type='Alert'
            )
            db.session.add(admin_notification)
        
        db.session.commit()
        
        flash('Refund request submitted successfully', 'success')
        return redirect(url_for('tax.refunds'))
    
    return render_template('tax/request_refund.html', 
                           accounts=accounts,
                           tax_types=tax_types,
                           periods=periods,
                           permissions=permissions)

@tax_bp.route('/refunds/process/<int:refund_id>/<string:action>')
@login_required
def process_refund(refund_id, action):
    # Check if user has admin permissions
    permissions = get_user_permissions(current_user)
    if 'admin_access' not in permissions:
        flash('You do not have permission to perform this action', 'danger')
        return redirect(url_for('tax.refunds'))
    
    # Get the refund request
    refund = Refund.query.get_or_404(refund_id)
    
    # Only pending refunds can be processed
    if refund.status != 'Pending':
        flash('This refund request has already been processed', 'warning')
        return redirect(url_for('tax.refunds'))
    
    if action == 'approve':
        # Approve the refund
        refund.status = 'Approved'
        refund.approval_date = datetime.utcnow()
        
        # Create a notification for the account owner
        account = Account.query.get(refund.account_id)
        notification = Notification(
            user_id=account.user_id,
            title="Refund Approved",
            message=f"Your refund request ({refund.reference_number}) for ${refund.amount} has been approved.",
            notification_type='Alert'
        )
        
        # Create a credit in the taxpayer ledger
        # Get a tax type for this ledger entry (using the first tax type as default)
        default_tax_type = TaxType.query.first()
        
        ledger_entry = TaxpayerLedger(
            account_id=refund.account_id,
            tax_type_id=default_tax_type.id,  # Required field
            transaction_date=datetime.now().date(),
            transaction_type='Refund',
            description=f"Approved refund request {refund.reference_number}",
            credit_amount=refund.amount,
            debit_amount=0,
            balance=refund.amount,  # Credit increases the balance
            reference_number=refund.reference_number
        )
        
        db.session.add(notification)
        db.session.add(ledger_entry)
        db.session.commit()
        
        flash('Refund request has been approved and credit added to taxpayer account', 'success')
    
    elif action == 'reject':
        # Reject the refund
        refund.status = 'Rejected'
        refund.approval_date = datetime.utcnow()
        
        # Create a notification for the account owner
        account = Account.query.get(refund.account_id)
        notification = Notification(
            user_id=account.user_id,
            title="Refund Rejected",
            message=f"Your refund request ({refund.reference_number}) for ${refund.amount} has been rejected.",
            notification_type='Alert'
        )
        
        db.session.add(notification)
        db.session.commit()
        
        flash('Refund request has been rejected', 'info')
    
    else:
        flash('Invalid action', 'danger')
    
    return redirect(url_for('tax.refunds'))

@tax_bp.route('/objections')
@login_required
def objections():
    permissions = get_user_permissions(current_user)
    account_id = request.args.get('account_id', type=int)
    status = request.args.get('status')
    page = request.args.get('page', 1, type=int)
    per_page = 10
    
    # Build query based on filters and permissions
    query = Objection.query
    
    if account_id:
        query = query.join(TaxReturn).filter(TaxReturn.account_id == account_id)
    elif not 'view_all_accounts' in permissions:
        # If not admin/internal, only show objections for user's accounts
        user_accounts = Account.query.filter_by(user_id=current_user.id).all()
        account_ids = [account.id for account in user_accounts]
        query = query.join(TaxReturn).filter(TaxReturn.account_id.in_(account_ids))
    
    if status:
        query = query.filter_by(status=status)
    
    # Get paginated results
    objections = query.order_by(Objection.filing_date.desc()).paginate(page=page, per_page=per_page)
    
    # Get filter options
    if 'view_all_accounts' in permissions:
        accounts = Account.query.all()
    else:
        accounts = Account.query.filter_by(user_id=current_user.id).all()
    
    statuses = ['Pending', 'In Progress', 'Resolved', 'Rejected']
    
    return render_template('tax/file_objection_list.html', 
                           objections=objections, 
                           accounts=accounts, 
                           statuses=statuses, 
                           selected_account_id=account_id, 
                           selected_status=status,
                           permissions=permissions)

@tax_bp.route('/objections/process/<int:objection_id>/<string:action>')
@login_required
def process_objection(objection_id, action):
    # Check if user has admin permissions
    permissions = get_user_permissions(current_user)
    if 'admin_access' not in permissions:
        flash('You do not have permission to perform this action', 'danger')
        return redirect(url_for('tax.objections'))
    
    # Get the objection
    objection = Objection.query.get_or_404(objection_id)
    
    # Only pending and in-progress objections can be processed
    if objection.status not in ['Pending', 'In Progress']:
        flash('This objection has already been processed', 'warning')
        return redirect(url_for('tax.objections'))
    
    tax_return = objection.tax_return
    if not tax_return:
        flash('Cannot process this objection as the tax return is not available', 'danger')
        return redirect(url_for('tax.objections'))
    
    account = tax_return.account
    if not account or not account.owner:
        flash('Cannot process this objection as the account information is not available', 'danger')
        return redirect(url_for('tax.objections'))
    
    # Process based on the action
    if action == 'approve':
        # Approve the objection
        objection.status = 'Resolved'
        objection.decision_date = datetime.utcnow()
        objection.decision = 'Objection approved by tax administration.'
        
        # Create a notification for the account owner
        notification = Notification(
            user_id=account.owner.id,
            title="Objection Approved",
            message=f"Your objection ({objection.reference_number}) has been approved.",
            notification_type='Success'
        )
        
        db.session.add(notification)
        db.session.commit()
        
        flash('Objection has been approved', 'success')
    
    elif action == 'reject':
        # Reject the objection
        objection.status = 'Rejected'
        objection.decision_date = datetime.utcnow()
        objection.decision = 'Objection rejected by tax administration.'
        
        # Create a notification for the account owner
        notification = Notification(
            user_id=account.owner.id,
            title="Objection Rejected",
            message=f"Your objection ({objection.reference_number}) for tax return {tax_return.reference_number} has been rejected.",
            notification_type='Danger'
        )
        
        db.session.add(notification)
        db.session.commit()
        
        flash('Objection has been rejected', 'info')
    
    elif action == 'in_progress':
        # Mark as in progress for review
        objection.status = 'In Progress'
        
        # Create a notification for the account owner
        notification = Notification(
            user_id=account.owner.id,
            title="Objection Under Review",
            message=f"Your objection ({objection.reference_number}) is now under review by our tax officers.",
            notification_type='Info'
        )
        
        db.session.add(notification)
        db.session.commit()
        
        flash('Objection has been marked for review', 'info')
    
    else:
        flash('Invalid action', 'danger')
    
    return redirect(url_for('tax.objections'))

@tax_bp.route('/objections/file', methods=['GET', 'POST'])
@login_required
def file_objection():
    permissions = get_user_permissions(current_user)
    tax_return_id = request.args.get('tax_return_id', type=int)
    
    if tax_return_id:
        tax_return = TaxReturn.query.get_or_404(tax_return_id)
        
        # Check if user has permission to object to this return
        if not 'view_all_accounts' in permissions:
            user_accounts = Account.query.filter_by(user_id=current_user.id).all()
            account_ids = [account.id for account in user_accounts]
            if tax_return.account_id not in account_ids:
                flash('You do not have permission to file objections for this tax return', 'danger')
                return redirect(url_for('tax.tax_returns'))
    else:
        tax_return = None
    
    # Get user's tax returns or all returns for admin/internal users
    if 'view_all_accounts' in permissions:
        if not tax_return:
            tax_returns = TaxReturn.query.filter(TaxReturn.status.in_(['Filed', 'Assessed'])).all()
        else:
            tax_returns = [tax_return]
    else:
        user_accounts = Account.query.filter_by(user_id=current_user.id).all()
        account_ids = [account.id for account in user_accounts]
        if not tax_return:
            tax_returns = TaxReturn.query.filter(TaxReturn.account_id.in_(account_ids), TaxReturn.status.in_(['Filed', 'Assessed'])).all()
        elif tax_return.account_id in account_ids:
            tax_returns = [tax_return]
        else:
            tax_returns = []
    
    if request.method == 'POST':
        tax_return_id = request.form.get('tax_return_id', type=int)
        reason = request.form.get('reason')
        
        # Validate inputs
        if not all([tax_return_id, reason]):
            flash('All fields are required', 'danger')
            return render_template('tax/file_objection.html', 
                                   tax_returns=tax_returns, 
                                   selected_tax_return=tax_return, 
                                   permissions=permissions)
        
        # Generate reference number
        reference_number = f"OBJ-{uuid.uuid4().hex[:8].upper()}"
        
        # Create objection
        objection = Objection(
            tax_return_id=tax_return_id,
            reason=reason,
            reference_number=reference_number
        )
        
        db.session.add(objection)
        db.session.commit()
        
        # Get tax return details for the notification
        tax_return = TaxReturn.query.get(tax_return_id)
        account = tax_return.account if tax_return else None
        
        # Create notification for the submitting user
        user_notification = Notification(
            user_id=current_user.id,
            title="Objection Filed",
            message=f"Your objection ({reference_number}) for tax return {tax_return.reference_number if tax_return else ''} has been submitted and is pending review.",
            notification_type='Tax'
        )
        db.session.add(user_notification)
        
        # Create notifications for all admin users
        admin_users = User.query.filter_by(is_admin=True).all()
        for admin in admin_users:
            admin_notification = Notification(
                user_id=admin.id,
                title="New Objection Filed",
                message=f"A new objection ({reference_number}) has been filed by {current_user.username} for tax return {tax_return.reference_number if tax_return else ''}{' for account ' + account.account_number if account else ''}.",
                notification_type='Alert'
            )
            db.session.add(admin_notification)
        
        db.session.commit()
        
        flash('Objection filed successfully', 'success')
        return redirect(url_for('tax.objections'))
    
    return render_template('tax/file_objection.html', 
                           tax_returns=tax_returns, 
                           selected_tax_return=tax_return, 
                           permissions=permissions)

@tax_bp.route('/audits')
@login_required
def audits():
    # Get user permissions
    permissions = get_user_permissions(current_user)
    # Build audit query: admins see all, others see only audits for their own accounts
    if any(perm in permissions for perm in ['view_all_accounts', 'admin_access']):
        query = Audit.query
    else:
        user_accounts = Account.query.filter_by(user_id=current_user.id).all()
        account_ids = [acc.id for acc in user_accounts]
        query = Audit.query.filter(Audit.account_id.in_(account_ids))
    page = request.args.get('page', 1, type=int)
    per_page = 20
    status = request.args.get('status', '')
    audit_type = request.args.get('type', '')
    if status:
        query = query.filter(Audit.status == status)
    if audit_type:
        query = query.filter(Audit.audit_type == audit_type)
    audits = query.order_by(Audit.start_date.desc()).paginate(page=page, per_page=per_page)
    # Get filter options
    statuses = ['Planned', 'In Progress', 'Completed', 'Cancelled']
    audit_types = ['Desk', 'Field', 'Comprehensive']
    return render_template('tax/audits.html',
                           audits=audits,
                           statuses=statuses,
                           audit_types=audit_types,
                           selected_status=status,
                           selected_type=audit_type,
                           permissions=permissions)

@tax_bp.route('/audits/new', methods=['GET', 'POST'])
@login_required
def new_audit():
    permissions = get_user_permissions(current_user)
    if not any(perm in permissions for perm in ['view_all_accounts', 'admin_access']):
        flash('You do not have permission to create audits', 'danger')
        return redirect(url_for('tax.audits'))
    # Fetch eligible tax returns
    if 'view_all_accounts' in permissions:
        tax_returns_list = TaxReturn.query.filter(TaxReturn.status.in_(['Filed', 'Assessed'])).all()
    else:
        user_accounts = Account.query.filter_by(user_id=current_user.id).all()
        account_ids = [acc.id for acc in user_accounts]
        tax_returns_list = TaxReturn.query.filter(TaxReturn.account_id.in_(account_ids), TaxReturn.status.in_(['Filed', 'Assessed'])).all()
    audit_types = ['Desk', 'Field', 'Comprehensive']
    if request.method == 'POST':
        tax_return_id = request.form.get('tax_return_id', type=int)
        audit_type = request.form.get('audit_type')
        start_date = request.form.get('start_date')
        end_date = request.form.get('end_date')
        if not (tax_return_id and audit_type and start_date):
            flash('All required fields must be filled', 'danger')
            return render_template('tax/new_audit.html', tax_returns=tax_returns_list, audit_types=audit_types, permissions=permissions)
        reference_number = f"AUD-{uuid.uuid4().hex[:8].upper()}"
        tr = TaxReturn.query.get_or_404(tax_return_id)
        audit = Audit(
            account_id=tr.account_id,
            tax_type_id=tr.tax_type_id,
            audit_type=audit_type,
            start_date=start_date,
            end_date=end_date or None,
            status='Planned',
            auditor_id=current_user.id,
            reference_number=reference_number
        )
        db.session.add(audit)
        db.session.commit()
        
        # Create AuditCase to link the specific tax return with the audit
        from app.models.registration import AuditCase
        from datetime import date
        
        case_number = f"CASE-{uuid.uuid4().hex[:8].upper()}"
        audit_case = AuditCase(
            account_id=tr.account_id,
            audit_id=audit.id,
            case_number=case_number,
            open_date=date.today(),
            status='Open'
        )
        
        db.session.add(audit_case)
        db.session.commit()
        
        # Notify account owner about the audit
        account = Account.query.get(tr.account_id)
        if account and account.owner:
            notification = Notification(
                user_id=account.owner.id,
                title="Tax Return Under Audit",
                message=f"Your tax return {tr.reference_number} for {tr.tax_type.name if tr.tax_type else 'Unknown'} tax type has been selected for {audit_type} audit. Reference: {reference_number}",
                notification_type='Warning'
            )
            db.session.add(notification)
            db.session.commit()
            
        flash('Audit created successfully', 'success')
        return redirect(url_for('tax.audits'))
    return render_template('tax/new_audit.html', tax_returns=tax_returns_list, audit_types=audit_types, permissions=permissions)