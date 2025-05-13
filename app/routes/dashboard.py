from flask import Blueprint, render_template, redirect, url_for, flash, request, jsonify
from flask_login import login_required, current_user
from app import db
from app.models.user import User, Account
from app.models.tax import TaxType, TaxPeriod, TaxReturn, Payment, Refund
from app.models.process import Person, Organization, Property, Request, Audit, Collection
from app.models.functionality import Notification, Case, WorkItem, WorkList
from app.services.auth_service import get_user_permissions
from datetime import datetime, timedelta
import calendar
import json

dashboard_bp = Blueprint('dashboard', __name__, url_prefix='/dashboard')

@dashboard_bp.route('/')
@login_required
def index():
    # Get user permissions
    permissions = get_user_permissions(current_user)
    
    # Get notifications for the user (limited to 2 for dashboard)
    notifications = Notification.query.filter_by(user_id=current_user.id, is_read=False).order_by(Notification.created_at.desc()).limit(2).all()
    
    # Get total count of unread notifications for the badge
    notifications_count = Notification.query.filter_by(user_id=current_user.id, is_read=False).count()
    
    # Get assigned work items
    work_items = WorkItem.query.filter_by(assigned_to=current_user.id, status='Pending').order_by(WorkItem.due_date.asc()).limit(5).all()
    
    # Get assigned cases
    cases = Case.query.filter_by(assigned_to=current_user.id, status='Open').order_by(Case.created_at.desc()).limit(5).all()
    
    # Get statistics based on user type
    stats = {}
    
    if 'view_all_accounts' in permissions or 'admin_access' in permissions:
        # For admin and internal users
        stats['total_accounts'] = Account.query.count()
        stats['active_accounts'] = Account.query.filter_by(is_active=True).count()
        stats['total_returns'] = TaxReturn.query.filter(TaxReturn.status != 'Not Filed').count()
        stats['pending_returns'] = TaxReturn.query.filter_by(status='Not Filed').count()
        # Calculate sum of payment amounts instead of count
        stats['total_payments'] = db.session.query(db.func.sum(Payment.amount)).filter_by(status='Completed').scalar() or 0
        stats['total_refunds'] = Refund.query.filter_by(status='Pending').count()
        stats['total_audits'] = Audit.query.count()
        stats['total_collections'] = Collection.query.count()
    else:
        # For regular users
        user_accounts = Account.query.filter_by(user_id=current_user.id).all()
        account_ids = [account.id for account in user_accounts]
        
        stats['total_accounts'] = len(account_ids)
        stats['active_accounts'] = Account.query.filter(Account.id.in_(account_ids), Account.is_active==True).count()
        stats['total_returns'] = TaxReturn.query.filter(TaxReturn.account_id.in_(account_ids)).count()
        stats['pending_returns'] = TaxReturn.query.filter(TaxReturn.account_id.in_(account_ids), TaxReturn.status=='Not Filed').count()
        # Calculate sum of payment amounts instead of count
        stats['total_payments'] = db.session.query(db.func.sum(Payment.amount)).join(TaxReturn).filter(TaxReturn.account_id.in_(account_ids)).scalar() or 0
        stats['total_refunds'] = Refund.query.filter(Refund.account_id.in_(account_ids)).count()
    
    # Get upcoming tax periods
    today = datetime.utcnow().date()
    upcoming_periods = TaxPeriod.query.filter(TaxPeriod.due_date >= today).order_by(TaxPeriod.due_date.asc()).limit(5).all()
    
    # Get recent activities (tax filings and payments)
    activities = []
    
    if 'view_all_accounts' in permissions or 'admin_access' in permissions:
        # For admin users, show all recent activities
        recent_returns = TaxReturn.query.filter(TaxReturn.status != 'Not Filed').order_by(TaxReturn.filing_date.desc()).limit(5).all()
        recent_payments = Payment.query.order_by(Payment.payment_date.desc()).limit(5).all()
    else:
        # For regular users, show only their activities
        user_accounts = Account.query.filter_by(user_id=current_user.id).all()
        account_ids = [account.id for account in user_accounts]
        
        recent_returns = TaxReturn.query.filter(TaxReturn.account_id.in_(account_ids), 
                                            TaxReturn.status != 'Not Filed').order_by(TaxReturn.filing_date.desc()).limit(5).all()
        recent_payments = Payment.query.join(TaxReturn).filter(TaxReturn.account_id.in_(account_ids)).order_by(Payment.payment_date.desc()).limit(5).all()
    
    # Add tax returns to activities
    for tax_return in recent_returns:
        activities.append({
            'type': 'tax_return',
            'description': f'Tax Return Filed: {tax_return.reference_number}',
            'icon': 'file-invoice',
            'date': tax_return.filing_date or tax_return.created_at,
            'status': tax_return.status.lower() if tax_return.status in ['Filed', 'Finalized'] else 'primary',
            'link': url_for('tax.view_tax_return', return_id=tax_return.id)
        })
    
    # Add payments to activities
    for payment in recent_payments:
        activities.append({
            'type': 'payment',
            'description': f'Payment Made: ${payment.amount:,.2f}',
            'icon': 'money-bill-wave',
            'date': payment.payment_date,
            'status': 'success' if payment.status == 'Completed' else 'warning',
            'link': url_for('tax.payment_detail', payment_id=payment.id)
        })
    
    # Sort activities by date, newest first
    activities.sort(key=lambda x: x['date'], reverse=True)
    
    # Limit to 4 most recent activities for simplicity
    activities = activities[:4]
    
    return render_template('dashboard/index.html',
                           notifications=notifications,
                           notifications_count=notifications_count,
                           work_items=work_items,
                           cases=cases,
                           stats=stats,
                           upcoming_periods=upcoming_periods,
                           activities=activities,
                           permissions=permissions)

@dashboard_bp.route('/analytics')
@login_required
def analytics():
    # Check if user has permission to view analytics
    permissions = get_user_permissions(current_user)
    if not ('view_reports' in permissions or 'admin_access' in permissions):
        flash('You do not have permission to access analytics', 'danger')
        return redirect(url_for('dashboard.index'))
    
    # Get date range for analytics
    end_date = datetime.utcnow().date()
    start_date = end_date - timedelta(days=365)  # Last year
    
    # Tax collection by type
    tax_types = TaxType.query.all()
    tax_collection_data = []
    
    for tax_type in tax_types:
        total_amount = db.session.query(db.func.sum(Payment.amount)).join(TaxReturn).filter(
            TaxReturn.tax_type_id == tax_type.id,
            Payment.payment_date.between(start_date, end_date)
        ).scalar() or 0
        
        tax_collection_data.append({
            'name': tax_type.name,
            'amount': float(total_amount),
            'is_core': tax_type.is_core
        })
    
    # Monthly collection trend
    monthly_trend = []
    for i in range(12):
        month_date = end_date - timedelta(days=30 * i)
        month_start = datetime(month_date.year, month_date.month, 1).date()
        month_end = datetime(month_date.year, month_date.month, calendar.monthrange(month_date.year, month_date.month)[1]).date()
        
        total_amount = db.session.query(db.func.sum(Payment.amount)).filter(
            Payment.payment_date.between(month_start, month_end)
        ).scalar() or 0
        
        monthly_trend.append({
            'month': month_start.strftime('%b %Y'),
            'amount': float(total_amount)
        })
    
    monthly_trend.reverse()  # Show oldest to newest
    
    # Return filing compliance
    compliance_data = []
    for tax_type in tax_types:
        total_returns = TaxReturn.query.filter(
            TaxReturn.tax_type_id == tax_type.id,
            TaxReturn.due_amount > 0
        ).count()
        
        filed_returns = TaxReturn.query.filter(
            TaxReturn.tax_type_id == tax_type.id,
            TaxReturn.status.in_(['Filed', 'Assessed', 'Finalized']),
            TaxReturn.due_amount > 0
        ).count()
        
        compliance_rate = (filed_returns / total_returns * 100) if total_returns > 0 else 0
        
        compliance_data.append({
            'name': tax_type.name,
            'compliance_rate': round(compliance_rate, 2)
        })
    
    return render_template('dashboard/analytics.html',
                           tax_collection_data=json.dumps(tax_collection_data),
                           monthly_trend=json.dumps(monthly_trend),
                           compliance_data=json.dumps(compliance_data))

@dashboard_bp.route('/notifications')
@login_required
def notifications():
    page = request.args.get('page', 1, type=int)
    per_page = 5  # Changed from 20 to 5 for pagination in groups of 5
    
    notifications = Notification.query.filter_by(user_id=current_user.id).order_by(
        Notification.is_read.asc(),
        Notification.created_at.desc()
    ).paginate(page=page, per_page=per_page)
    
    return render_template('dashboard/notifications.html', notifications=notifications)

@dashboard_bp.route('/notifications/mark-read/<int:notification_id>', methods=['POST'])
@login_required
def mark_notification_read(notification_id):
    notification = Notification.query.get_or_404(notification_id)
    
    if notification.user_id != current_user.id:
        return jsonify({'success': False, 'message': 'Unauthorized'}), 403
    
    notification.is_read = True
    notification.read_at = datetime.utcnow()
    db.session.commit()
    
    return jsonify({'success': True})

@dashboard_bp.route('/notifications/mark-all-read', methods=['POST'])
@login_required
def mark_all_notifications_read():
    # Find all unread notifications for the current user
    unread_count = Notification.query.filter_by(
        user_id=current_user.id, 
        is_read=False
    ).count()
    
    # Mark all as read
    now = datetime.utcnow()
    notifications = Notification.query.filter_by(
        user_id=current_user.id, 
        is_read=False
    ).update({
        'is_read': True,
        'read_at': now
    })
    
    db.session.commit()
    
    return jsonify({
        'success': True, 
        'count': unread_count,
        'message': f'{unread_count} notifications marked as read'
    })

@dashboard_bp.route('/work-items')
@login_required
def work_items():
    page = request.args.get('page', 1, type=int)
    per_page = 20
    status = request.args.get('status', 'all')
    
    query = WorkItem.query.filter_by(assigned_to=current_user.id)
    
    if status != 'all':
        query = query.filter_by(status=status)
    
    work_items = query.order_by(WorkItem.due_date.asc()).paginate(page=page, per_page=per_page)
    
    return render_template('dashboard/work_items.html', work_items=work_items, current_status=status)

@dashboard_bp.route('/work-items/<int:item_id>/update', methods=['POST'])
@login_required
def update_work_item(item_id):
    work_item = WorkItem.query.get_or_404(item_id)
    
    if work_item.assigned_to != current_user.id:
        flash('You are not authorized to update this work item', 'danger')
        return redirect(url_for('dashboard.work_items'))
    
    status = request.form.get('status')
    if status in ['Pending', 'In Progress', 'Completed', 'Cancelled']:
        work_item.status = status
        
        if status == 'Completed':
            work_item.completed_at = datetime.utcnow()
        
        db.session.commit()
        flash('Work item updated successfully', 'success')
    else:
        flash('Invalid status', 'danger')
    
    return redirect(url_for('dashboard.work_items'))

@dashboard_bp.route('/cases')
@login_required
def cases():
    page = request.args.get('page', 1, type=int)
    per_page = 20
    status = request.args.get('status', 'all')
    
    query = Case.query.filter_by(assigned_to=current_user.id)
    
    if status != 'all':
        query = query.filter_by(status=status)
    
    cases = query.order_by(Case.created_at.desc()).paginate(page=page, per_page=per_page)
    
    return render_template('dashboard/cases.html', cases=cases, current_status=status)

@dashboard_bp.route('/cases/<int:case_id>')
@login_required
def view_case(case_id):
    case = Case.query.get_or_404(case_id)
    
    if case.assigned_to != current_user.id and case.created_by != current_user.id:
        flash('You are not authorized to view this case', 'danger')
        return redirect(url_for('dashboard.cases'))
    
    return render_template('dashboard/case_detail.html', case=case)

@dashboard_bp.route('/cases/<int:case_id>/add-note', methods=['POST'])
@login_required
def add_case_note(case_id):
    case = Case.query.get_or_404(case_id)
    
    if case.assigned_to != current_user.id and case.created_by != current_user.id:
        flash('You are not authorized to add notes to this case', 'danger')
        return redirect(url_for('dashboard.cases'))
    
    content = request.form.get('content')
    if content:
        from app.models.functionality import CaseNote
        note = CaseNote(
            case_id=case.id,
            content=content,
            created_by=current_user.id
        )
        db.session.add(note)
        db.session.commit()
        flash('Note added successfully', 'success')
    else:
        flash('Note content cannot be empty', 'danger')
    
    return redirect(url_for('dashboard.view_case', case_id=case.id))