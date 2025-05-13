from flask import Blueprint, render_template, redirect, url_for, flash, request, jsonify
from flask_login import login_required, current_user
from app import db
from app.models.user import User, Account
from app.models.tax import TaxType, TaxPeriod, TaxReturn, Payment, Refund
from app.models.process import Collection
from app.models.registration import TaxpayerLedger
from app.services.auth_service import get_user_permissions
from app.services.reporting_service import generate_report
from datetime import datetime, timedelta
import calendar
import json

reporting_bp = Blueprint('reporting', __name__, url_prefix='/reporting')

@reporting_bp.route('/')
@login_required
def index():
    # Get user permissions
    permissions = get_user_permissions(current_user)
    
    # Check if user has permission to view reports
    if not any(perm in permissions for perm in ['view_reports', 'view_statistics', 'admin_access']):
        flash('You do not have permission to access reporting', 'danger')
        return redirect(url_for('dashboard.index'))
    
    return render_template('reporting/index.html', permissions=permissions)

@reporting_bp.route('/reports')
@login_required
def reports():
    # Get user permissions
    permissions = get_user_permissions(current_user)
    
    # Check if user has permission to view reports
    if not any(perm in permissions for perm in ['view_reports', 'view_statistics', 'admin_access']):
        flash('You do not have permission to access reports', 'danger')
        return redirect(url_for('reporting.index'))
    
    # Define available reports
    available_reports = [
        {
            'id': 'tax_collection',
            'name': 'Tax Collection Report',
            'description': 'Report on tax collection by type, period, and region'
        },
        {
            'id': 'compliance',
            'name': 'Compliance Report',
            'description': 'Report on taxpayer compliance rates and trends'
        },
        {
            'id': 'registration',
            'name': 'Registration Report',
            'description': 'Report on taxpayer registrations by type and status'
        },
        {
            'id': 'audit',
            'name': 'Audit Report',
            'description': 'Report on audit activities, findings, and outcomes'
        },
        {
            'id': 'refund',
            'name': 'Refund Report',
            'description': 'Report on refund requests, approvals, and payments'
        },
        {
            'id': 'revenue',
            'name': 'Revenue Report',
            'description': 'Report on overall revenue collection and trends'
        }
    ]
    
    return render_template('reporting/reports.html', 
                           available_reports=available_reports, 
                           permissions=permissions)

@reporting_bp.route('/generate-report')
@login_required
def generate_report_view():
    # Get user permissions
    permissions = get_user_permissions(current_user)
    
    # Check if user has permission to view reports
    if not any(perm in permissions for perm in ['view_reports', 'view_statistics', 'admin_access']):
        flash('You do not have permission to generate reports', 'danger')
        return redirect(url_for('reporting.index'))
    
    report_type = request.args.get('type', '')
    start_date = request.args.get('start_date')
    end_date = request.args.get('end_date')
    tax_type_id = request.args.get('tax_type_id', type=int)
    
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
    
    # Get tax types for filter
    tax_types = TaxType.query.all()
    
    # Generate report if type is specified
    report_data = None
    if report_type:
        report_data = generate_report(report_type, start_date, end_date, tax_type_id)
    
    return render_template('reporting/generate_report.html', 
                           report_type=report_type, 
                           start_date=start_date.strftime('%Y-%m-%d'), 
                           end_date=end_date.strftime('%Y-%m-%d'), 
                           tax_types=tax_types, 
                           selected_tax_type_id=tax_type_id, 
                           report_data=report_data, 
                           permissions=permissions)

@reporting_bp.route('/dashboards')
@login_required
def dashboards():
    # Get user permissions
    permissions = get_user_permissions(current_user)
    
    # Check if user has permission to view dashboards
    if not any(perm in permissions for perm in ['view_reports', 'view_statistics', 'admin_access']):
        flash('You do not have permission to access dashboards', 'danger')
        return redirect(url_for('reporting.index'))
    
    # Get date range for dashboard data
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
    
    # Registration statistics
    from app.models.registration import Registration, IndividualRegistration, NonIndividualRegistration, SoleProprietorRegistration
    
    individual_count = IndividualRegistration.query.count()
    non_individual_count = NonIndividualRegistration.query.count()
    sole_proprietor_count = SoleProprietorRegistration.query.count()
    
    registration_data = [
        {'name': 'Individuals', 'count': individual_count},
        {'name': 'Non-Individuals', 'count': non_individual_count},
        {'name': 'Sole Proprietors', 'count': sole_proprietor_count}
    ]
    
    return render_template('reporting/dashboards.html', 
                           tax_collection_data=json.dumps(tax_collection_data), 
                           monthly_trend=json.dumps(monthly_trend), 
                           compliance_data=json.dumps(compliance_data), 
                           registration_data=json.dumps(registration_data), 
                           permissions=permissions)

@reporting_bp.route('/tadat-dashboard')
@login_required
def tadat_dashboard():
    # Get user permissions
    permissions = get_user_permissions(current_user)
    
    # Check if user has permission to view TADAT dashboard
    if not any(perm in permissions for perm in ['view_reports', 'view_statistics', 'admin_access']):
        flash('You do not have permission to access TADAT dashboard', 'danger')
        return redirect(url_for('reporting.index'))
    
    # TADAT (Tax Administration Diagnostic Assessment Tool) metrics
    # These would be calculated based on actual data in a real implementation
    # Here we're using placeholder data
    
    # Performance Outcome Areas (POAs)
    poas = [
        {
            'id': 'POA1',
            'name': 'Integrity of the Registered Taxpayer Base',
            'score': 'B',
            'indicators': [
                {'id': 'P1-1', 'name': 'Accurate and Reliable Taxpayer Information', 'score': 'B+'},
                {'id': 'P1-2', 'name': 'Knowledge of the Potential Taxpayer Base', 'score': 'B'}
            ]
        },
        {
            'id': 'POA2',
            'name': 'Effective Risk Management',
            'score': 'C+',
            'indicators': [
                {'id': 'P2-3', 'name': 'Identification, Assessment, and Mitigation of Risks', 'score': 'C'},
                {'id': 'P2-4', 'name': 'Management of Compliance Risk', 'score': 'C+'},
                {'id': 'P2-5', 'name': 'Monitoring and Evaluation of Compliance Risk Mitigation Activities', 'score': 'B-'}
            ]
        },
        {
            'id': 'POA3',
            'name': 'Supporting Voluntary Compliance',
            'score': 'B-',
            'indicators': [
                {'id': 'P3-6', 'name': 'Scope, Currency, and Accessibility of Information', 'score': 'B'},
                {'id': 'P3-7', 'name': 'Scope of Initiatives to Reduce Taxpayer Compliance Costs', 'score': 'C+'},
                {'id': 'P3-8', 'name': 'Obtaining Taxpayer Feedback', 'score': 'B-'}
            ]
        },
        {
            'id': 'POA4',
            'name': 'Timely Filing of Tax Declarations',
            'score': 'B',
            'indicators': [
                {'id': 'P4-9', 'name': 'On-time Filing Rate', 'score': 'B+'},
                {'id': 'P4-10', 'name': 'Management of Non-filers', 'score': 'B-'}
            ]
        },
        {
            'id': 'POA5',
            'name': 'Timely Payment of Taxes',
            'score': 'B-',
            'indicators': [
                {'id': 'P5-11', 'name': 'Use of Electronic Payment Methods', 'score': 'B'},
                {'id': 'P5-12', 'name': 'Collection of Tax Arrears', 'score': 'C+'},
                {'id': 'P5-13', 'name': 'Management of Tax Refunds', 'score': 'B-'}
            ]
        },
        {
            'id': 'POA6',
            'name': 'Accurate Reporting in Declarations',
            'score': 'C+',
            'indicators': [
                {'id': 'P6-14', 'name': 'Tax Audit Selection', 'score': 'C'},
                {'id': 'P6-15', 'name': 'Tax Audit Completion', 'score': 'C+'},
                {'id': 'P6-16', 'name': 'Tax Audit Results', 'score': 'B-'}
            ]
        },
        {
            'id': 'POA7',
            'name': 'Effective Tax Dispute Resolution',
            'score': 'B',
            'indicators': [
                {'id': 'P7-17', 'name': 'Existence of Independent Tax Dispute Resolution Process', 'score': 'B+'},
                {'id': 'P7-18', 'name': 'Time Taken to Resolve Disputes', 'score': 'B-'},
                {'id': 'P7-19', 'name': 'Degree to Which Dispute Outcomes are Implemented', 'score': 'B'}
            ]
        },
        {
            'id': 'POA8',
            'name': 'Efficient Revenue Management',
            'score': 'B-',
            'indicators': [
                {'id': 'P8-20', 'name': 'Contribution to Government Tax Revenue Forecasting', 'score': 'B'},
                {'id': 'P8-21', 'name': 'Adequacy of Tax Revenue Accounting', 'score': 'B-'},
                {'id': 'P8-22', 'name': 'Revenue Reporting', 'score': 'B'}
            ]
        },
        {
            'id': 'POA9',
            'name': 'Accountability and Transparency',
            'score': 'B',
            'indicators': [
                {'id': 'P9-23', 'name': 'Internal Assurance Mechanisms', 'score': 'B'},
                {'id': 'P9-24', 'name': 'External Oversight of the Tax Administration', 'score': 'B+'},
                {'id': 'P9-25', 'name': 'Public Perception of Integrity', 'score': 'B-'},
                {'id': 'P9-26', 'name': 'Publication of Activities, Results, and Plans', 'score': 'B'}
            ]
        }
    ]
    
    return render_template('reporting/tadat_dashboard.html', 
                           poas=poas, 
                           permissions=permissions)

@reporting_bp.route('/business-analytics')
@login_required
def business_analytics():
    # Get user permissions
    permissions = get_user_permissions(current_user)
    
    # Check if user has permission to view business analytics
    if not any(perm in permissions for perm in ['view_reports', 'view_statistics', 'admin_access']):
        flash('You do not have permission to access business analytics', 'danger')
        return redirect(url_for('reporting.index'))
    
    # Get date range for analytics
    end_date = datetime.utcnow().date()
    start_date = end_date - timedelta(days=365)  # Last year
    
    # Tax collection by region (simplified example)
    # In a real implementation, this would be based on actual regional data
    region_data = [
        {'name': 'Northern Region', 'amount': 2500000},
        {'name': 'Southern Region', 'amount': 3200000},
        {'name': 'Eastern Region', 'amount': 1800000},
        {'name': 'Western Region', 'amount': 2100000},
        {'name': 'Central Region', 'amount': 4500000}
    ]
    
    # Taxpayer segment analysis
    # In a real implementation, this would be based on actual taxpayer segments
    segment_data = [
        {'name': 'Large Taxpayers', 'count': 250, 'revenue': 5500000, 'compliance': 92},
        {'name': 'Medium Taxpayers', 'count': 1500, 'revenue': 3800000, 'compliance': 85},
        {'name': 'Small Taxpayers', 'count': 8500, 'revenue': 2200000, 'compliance': 72},
        {'name': 'Micro Businesses', 'count': 25000, 'revenue': 1500000, 'compliance': 65},
        {'name': 'Individual Taxpayers', 'count': 150000, 'revenue': 1000000, 'compliance': 78}
    ]
    
    # Tax gap analysis (simplified)
    # In a real implementation, this would be based on economic data and tax collection
    tax_gap_data = [
        {'year': '2020', 'potential': 12000000, 'collected': 9500000, 'gap': 2500000, 'gap_percent': 20.8},
        {'year': '2021', 'potential': 13500000, 'collected': 10800000, 'gap': 2700000, 'gap_percent': 20.0},
        {'year': '2022', 'potential': 15000000, 'collected': 12200000, 'gap': 2800000, 'gap_percent': 18.7},
        {'year': '2023', 'potential': 16500000, 'collected': 13700000, 'gap': 2800000, 'gap_percent': 17.0},
        {'year': '2024', 'potential': 18000000, 'collected': 15300000, 'gap': 2700000, 'gap_percent': 15.0}
    ]
    
    # Compliance trend analysis
    compliance_trend = [
        {'year': '2020', 'filing': 75, 'payment': 72, 'reporting': 68},
        {'year': '2021', 'filing': 78, 'payment': 75, 'reporting': 70},
        {'year': '2022', 'filing': 80, 'payment': 77, 'reporting': 73},
        {'year': '2023', 'filing': 83, 'payment': 80, 'reporting': 76},
        {'year': '2024', 'filing': 85, 'payment': 82, 'reporting': 78}
    ]
    
    return render_template('reporting/business_analytics.html', 
                           region_data=json.dumps(region_data), 
                           segment_data=json.dumps(segment_data), 
                           tax_gap_data=json.dumps(tax_gap_data), 
                           compliance_trend=json.dumps(compliance_trend), 
                           permissions=permissions)