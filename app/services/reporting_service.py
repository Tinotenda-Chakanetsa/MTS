from app import db
from app.models.user import User, Account
from app.models.tax import TaxType, TaxPeriod, TaxReturn, Payment, Refund
from app.models.process import Audit, Collection
from app.models.registration import Registration, IndividualRegistration, NonIndividualRegistration, SoleProprietorRegistration
from datetime import datetime, timedelta
import calendar

def generate_report(report_type, start_date, end_date, tax_type_id=None):
    """Generate report based on type and parameters"""
    if report_type == 'tax_collection':
        return generate_tax_collection_report(start_date, end_date, tax_type_id)
    elif report_type == 'compliance':
        return generate_compliance_report(start_date, end_date, tax_type_id)
    elif report_type == 'registration':
        return generate_registration_report(start_date, end_date)
    elif report_type == 'audit':
        return generate_audit_report(start_date, end_date, tax_type_id)
    elif report_type == 'refund':
        return generate_refund_report(start_date, end_date, tax_type_id)
    elif report_type == 'revenue':
        return generate_revenue_report(start_date, end_date)
    else:
        return None

def generate_tax_collection_report(start_date, end_date, tax_type_id=None):
    """Generate report on tax collection by type and period"""
    query = db.session.query(
        TaxType.name.label('tax_type'),
        db.func.sum(Payment.amount).label('total_amount'),
        db.func.count(Payment.id).label('payment_count')
    ).join(TaxReturn, Payment.tax_return_id == TaxReturn.id)\
     .join(TaxType, TaxReturn.tax_type_id == TaxType.id)\
     .filter(Payment.payment_date.between(start_date, end_date))\
     .group_by(TaxType.name)
    
    if tax_type_id:
        query = query.filter(TaxReturn.tax_type_id == tax_type_id)
    
    results = query.all()
    
    # Convert to dictionary format for easier template rendering
    report_data = {
        'title': 'Tax Collection Report',
        'period': f'{start_date.strftime("%Y-%m-%d")} to {end_date.strftime("%Y-%m-%d")}',
        'summary': {
            'total_collected': sum(r.total_amount or 0 for r in results),
            'total_payments': sum(r.payment_count or 0 for r in results)
        },
        'details': []
    }
    
    for r in results:
        report_data['details'].append({
            'tax_type': r.tax_type,
            'total_amount': float(r.total_amount or 0),
            'payment_count': r.payment_count or 0
        })
    
    # Add monthly breakdown
    monthly_data = []
    current_date = start_date
    while current_date <= end_date:
        month_start = datetime(current_date.year, current_date.month, 1).date()
        month_end = datetime(current_date.year, current_date.month, 
                             calendar.monthrange(current_date.year, current_date.month)[1]).date()
        
        query = db.session.query(db.func.sum(Payment.amount))\
               .join(TaxReturn, Payment.tax_return_id == TaxReturn.id)\
               .filter(Payment.payment_date.between(month_start, month_end))
        
        if tax_type_id:
            query = query.filter(TaxReturn.tax_type_id == tax_type_id)
        
        total = query.scalar() or 0
        
        monthly_data.append({
            'month': month_start.strftime('%b %Y'),
            'total': float(total)
        })
        
        # Move to next month
        if current_date.month == 12:
            current_date = datetime(current_date.year + 1, 1, 1).date()
        else:
            current_date = datetime(current_date.year, current_date.month + 1, 1).date()
    
    report_data['monthly_breakdown'] = monthly_data
    
    return report_data

def generate_compliance_report(start_date, end_date, tax_type_id=None):
    """Generate report on taxpayer compliance rates and trends"""
    # Join TaxPeriod to filter by due_date
    base_query = TaxReturn.query.join(TaxPeriod).filter(TaxPeriod.due_date.between(start_date, end_date))
    if tax_type_id:
        base_query = base_query.filter(TaxReturn.tax_type_id == tax_type_id)
    
    # Get total returns
    total_returns = base_query.count()
    
    # Get filed returns (on time)
    filed_on_time_query = base_query.filter(
        TaxReturn.status.in_(['Filed', 'Assessed', 'Finalized']),
        TaxReturn.filing_date <= TaxPeriod.due_date
    )
    filed_on_time = filed_on_time_query.count()
    
    # Get filed returns (late)
    filed_late_query = base_query.filter(
        TaxReturn.status.in_(['Filed', 'Assessed', 'Finalized']),
        TaxReturn.filing_date > TaxPeriod.due_date
    )
    filed_late = filed_late_query.count()
    
    # Get not filed returns
    not_filed = base_query.filter(TaxReturn.status == 'Not Filed').count()
    
    # Calculate compliance rates
    filing_compliance_rate = (filed_on_time / total_returns * 100) if total_returns > 0 else 0
    overall_filing_rate = ((filed_on_time + filed_late) / total_returns * 100) if total_returns > 0 else 0
    
    # Payment compliance
    payment_query = base_query.filter(TaxReturn.status.in_(['Filed', 'Assessed', 'Finalized']))
    total_assessed = payment_query.count()
    
    # Count returns with completed payments
    paid_in_full = payment_query.join(Payment).filter(Payment.status == 'Completed').count()
    payment_compliance_rate = (paid_in_full / total_assessed * 100) if total_assessed > 0 else 0
    
    # Compliance by tax type
    tax_type_compliance = []
    if not tax_type_id:  # Only show breakdown by tax type if not already filtered
        tax_types = TaxType.query.all()
        for tax_type in tax_types:
            # Join TaxPeriod to filter by due_date
            type_total = TaxReturn.query.join(TaxPeriod).filter(
                TaxReturn.tax_type_id == tax_type.id,
                TaxPeriod.due_date.between(start_date, end_date)
            ).count()
            
            # Join TaxPeriod to filter by due_date and status
            type_filed = TaxReturn.query.join(TaxPeriod).filter(
                TaxReturn.tax_type_id == tax_type.id,
                TaxReturn.status.in_(['Filed', 'Assessed', 'Finalized']),
                TaxPeriod.due_date.between(start_date, end_date)
            ).count()
            
            type_compliance = (type_filed / type_total * 100) if type_total > 0 else 0
            
            tax_type_compliance.append({
                'tax_type': tax_type.name,
                'total_returns': type_total,
                'filed_returns': type_filed,
                'compliance_rate': round(type_compliance, 2)
            })
    
    # Prepare report data
    report_data = {
        'title': 'Compliance Report',
        'period': f'{start_date.strftime("%Y-%m-%d")} to {end_date.strftime("%Y-%m-%d")}',
        'summary': {
            'total_returns': total_returns,
            'filed_on_time': filed_on_time,
            'filed_late': filed_late,
            'not_filed': not_filed,
            'filing_compliance_rate': round(filing_compliance_rate, 2),
            'overall_filing_rate': round(overall_filing_rate, 2),
            'payment_compliance_rate': round(payment_compliance_rate, 2)
        },
        'tax_type_compliance': tax_type_compliance
    }
    
    return report_data

def generate_registration_report(start_date, end_date):
    """Generate report on taxpayer registrations by type and status"""
    # Count registrations by type
    individual_count = IndividualRegistration.query.filter(
        IndividualRegistration.registered_date.between(start_date, end_date)
    ).count()
    
    non_individual_count = NonIndividualRegistration.query.filter(
        NonIndividualRegistration.registered_date.between(start_date, end_date)
    ).count()
    
    sole_proprietor_count = SoleProprietorRegistration.query.filter(
        SoleProprietorRegistration.registered_date.between(start_date, end_date)
    ).count()
    
    # Count registrations by status
    pending_count = Registration.query.filter(
        Registration.status == 'Pending',
        Registration.registered_date.between(start_date, end_date)
    ).count()
    
    approved_count = Registration.query.filter(
        Registration.status == 'Approved',
        Registration.registered_date.between(start_date, end_date)
    ).count()
    
    rejected_count = Registration.query.filter(
        Registration.status == 'Rejected',
        Registration.registered_date.between(start_date, end_date)
    ).count()
    
    # Monthly registration trend
    monthly_data = []
    current_date = start_date
    while current_date <= end_date:
        month_start = datetime(current_date.year, current_date.month, 1).date()
        month_end = datetime(current_date.year, current_date.month, 
                             calendar.monthrange(current_date.year, current_date.month)[1]).date()
        
        month_count = Registration.query.filter(
            Registration.registered_date.between(month_start, month_end)
        ).count()
        
        monthly_data.append({
            'month': month_start.strftime('%b %Y'),
            'count': month_count
        })
        
        # Move to next month
        if current_date.month == 12:
            current_date = datetime(current_date.year + 1, 1, 1).date()
        else:
            current_date = datetime(current_date.year, current_date.month + 1, 1).date()
    
    # Prepare report data
    report_data = {
        'title': 'Registration Report',
        'period': f'{start_date.strftime("%Y-%m-%d")} to {end_date.strftime("%Y-%m-%d")}',
        'summary': {
            'total_registrations': individual_count + non_individual_count + sole_proprietor_count,
            'individual_count': individual_count,
            'non_individual_count': non_individual_count,
            'sole_proprietor_count': sole_proprietor_count,
            'pending_count': pending_count,
            'approved_count': approved_count,
            'rejected_count': rejected_count
        },
        'monthly_trend': monthly_data
    }
    
    return report_data

def generate_audit_report(start_date, end_date, tax_type_id=None):
    """Generate report on audit activities, findings, and outcomes"""
    # Base query for audits in the period
    base_query = Audit.query.filter(Audit.start_date.between(start_date, end_date))
    
    # Count audits by status
    total_audits = base_query.count()
    in_progress = base_query.filter(Audit.status == 'In Progress').count()
    completed = base_query.filter(Audit.status == 'Completed').count()
    
    # Calculate additional assessment amounts
    additional_assessment_query = db.session.query(db.func.sum(Audit.additional_assessment))\
                                  .filter(Audit.start_date.between(start_date, end_date))
    additional_assessment = additional_assessment_query.scalar() or 0
    
    # Audit results by outcome
    audit_outcomes = db.session.query(
        Audit.outcome, db.func.count(Audit.id).label('count')
    ).filter(Audit.start_date.between(start_date, end_date))\
     .group_by(Audit.outcome).all()
    
    outcome_data = []
    for outcome, count in audit_outcomes:
        if outcome:  # Skip None values
            outcome_data.append({
                'outcome': outcome,
                'count': count
            })
    
    # Prepare report data
    report_data = {
        'title': 'Audit Report',
        'period': f'{start_date.strftime("%Y-%m-%d")} to {end_date.strftime("%Y-%m-%d")}',
        'summary': {
            'total_audits': total_audits,
            'in_progress': in_progress,
            'completed': completed,
            'additional_assessment': float(additional_assessment)
        },
        'outcomes': outcome_data
    }
    
    return report_data

def generate_refund_report(start_date, end_date, tax_type_id=None):
    """Generate report on refund requests, approvals, and payments"""
    # Base query for refunds in the period
    base_query = Refund.query.filter(Refund.request_date.between(start_date, end_date))
    if tax_type_id:
        # Filter refunds by tax type via account_id subquery
        acct_subq = TaxReturn.query.with_entities(TaxReturn.account_id).filter(
            TaxReturn.tax_type_id == tax_type_id
        ).subquery()
        base_query = base_query.filter(Refund.account_id.in_(acct_subq))
    
    # Count refunds by status
    total_refunds = base_query.count()
    pending = base_query.filter(Refund.status == 'Pending').count()
    approved = base_query.filter(Refund.status == 'Approved').count()
    rejected = base_query.filter(Refund.status == 'Rejected').count()
    paid = base_query.filter(Refund.status == 'Paid').count()
    
    # Calculate total refund amounts
    requested_amount_query = db.session.query(db.func.sum(Refund.amount))\
                             .filter(Refund.request_date.between(start_date, end_date))
    if tax_type_id:
        acct_subq = TaxReturn.query.with_entities(TaxReturn.account_id).filter(
            TaxReturn.tax_type_id == tax_type_id
        ).subquery()
        requested_amount_query = requested_amount_query.filter(Refund.account_id.in_(acct_subq))
    requested_amount = requested_amount_query.scalar() or 0
    
    approved_amount_query = db.session.query(db.func.sum(Refund.amount))\
                            .filter(Refund.request_date.between(start_date, end_date),
                                    Refund.status.in_(['Approved', 'Paid']))
    if tax_type_id:
        acct_subq = TaxReturn.query.with_entities(TaxReturn.account_id).filter(
            TaxReturn.tax_type_id == tax_type_id
        ).subquery()
        approved_amount_query = approved_amount_query.filter(Refund.account_id.in_(acct_subq))
    approved_amount = approved_amount_query.scalar() or 0
    
    # Refunds by tax type
    tax_type_refunds = []
    if not tax_type_id:  # Only show breakdown by tax type if not already filtered
        tax_types = TaxType.query.all()
        for tax_type in tax_types:
            # Count refunds for this tax type via account_id subquery
            acct_subq = TaxReturn.query.with_entities(TaxReturn.account_id).filter(
                TaxReturn.tax_type_id == tax_type.id
            ).subquery()
            type_count = Refund.query.filter(
                Refund.account_id.in_(acct_subq),
                Refund.request_date.between(start_date, end_date)
            ).count()
            
            type_amount = db.session.query(db.func.sum(Refund.amount)).filter(
                Refund.account_id.in_(acct_subq),
                Refund.request_date.between(start_date, end_date)
            ).scalar() or 0
            
            tax_type_refunds.append({
                'tax_type': tax_type.name,
                'count': type_count,
                'amount': float(type_amount)
            })
    
    # Prepare report data
    report_data = {
        'title': 'Refund Report',
        'period': f'{start_date.strftime("%Y-%m-%d")} to {end_date.strftime("%Y-%m-%d")}',
        'summary': {
            'total_refunds': total_refunds,
            'pending': pending,
            'approved': approved,
            'rejected': rejected,
            'paid': paid,
            'requested_amount': float(requested_amount),
            'approved_amount': float(approved_amount)
        },
        'tax_type_refunds': tax_type_refunds
    }
    
    return report_data

def generate_revenue_report(start_date, end_date):
    """Generate report on overall revenue collection and trends"""
    # Calculate total revenue
    total_revenue_query = db.session.query(db.func.sum(Payment.amount))\
                          .filter(Payment.payment_date.between(start_date, end_date))
    total_revenue = total_revenue_query.scalar() or 0
    
    # Revenue by tax type
    tax_type_revenue = db.session.query(
        TaxType.name.label('tax_type'),
        db.func.sum(Payment.amount).label('amount')
    ).join(TaxReturn, Payment.tax_return_id == TaxReturn.id)\
     .join(TaxType, TaxReturn.tax_type_id == TaxType.id)\
     .filter(Payment.payment_date.between(start_date, end_date))\
     .group_by(TaxType.name).all()
    
    tax_type_data = []
    for tax_type, amount in tax_type_revenue:
        tax_type_data.append({
            'tax_type': tax_type,
            'amount': float(amount or 0)
        })
    
    # Monthly revenue trend
    monthly_data = []
    current_date = start_date
    while current_date <= end_date:
        month_start = datetime(current_date.year, current_date.month, 1).date()
        month_end = datetime(current_date.year, current_date.month, 
                             calendar.monthrange(current_date.year, current_date.month)[1]).date()
        
        month_revenue = db.session.query(db.func.sum(Payment.amount))\
                       .filter(Payment.payment_date.between(month_start, month_end))\
                       .scalar() or 0
        
        monthly_data.append({
            'month': month_start.strftime('%b %Y'),
            'amount': float(month_revenue)
        })
        
        # Move to next month
        if current_date.month == 12:
            current_date = datetime(current_date.year + 1, 1, 1).date()
        else:
            current_date = datetime(current_date.year, current_date.month + 1, 1).date()
    
    # Revenue vs target (simplified example)
    # In a real implementation, this would be based on actual targets
    target_data = []
    for month_data in monthly_data:
        # Assume a simple target of 1,000,000 per month
        target = 1000000
        target_data.append({
            'month': month_data['month'],
            'target': target,
            'actual': month_data['amount'],
            'variance': month_data['amount'] - target,
            'achievement': (month_data['amount'] / target * 100) if target > 0 else 0
        })
    
    # Prepare report data
    report_data = {
        'title': 'Revenue Report',
        'period': f'{start_date.strftime("%Y-%m-%d")} to {end_date.strftime("%Y-%m-%d")}',
        'summary': {
            'total_revenue': float(total_revenue)
        },
        'tax_type_revenue': tax_type_data,
        'monthly_trend': monthly_data,
        'target_comparison': target_data
    }
    
    return report_data