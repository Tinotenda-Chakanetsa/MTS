from app import db
from app.models.tax import TaxType, TaxPeriod, TaxReturn, Payment, Refund, Objection
from app.models.registration import TaxpayerLedger
from datetime import datetime
from decimal import Decimal
import uuid


def auto_flag_return(tax_return):
    """
    Automatically flag a tax return if it violates certain compliance conditions.
    Sets is_flagged and flag_reason on the tax_return instance.
    """
    reasons = []
    # Example rule 1: Negative or zero due amount
    if tax_return.due_amount is None or Decimal(tax_return.due_amount) <= 0:
        reasons.append("Due amount is zero or negative.")
    # Example rule 2: Excessive refund (if refund > 80% of due)
    refund = Refund.query.filter_by(account_id=tax_return.account_id).order_by(Refund.request_date.desc()).first()
    if refund and tax_return.due_amount and refund.amount:
        try:
            if Decimal(refund.amount) > Decimal(tax_return.due_amount) * Decimal('0.8'):
                reasons.append(f"Recent refund ({refund.amount}) exceeds 80% of due amount ({tax_return.due_amount}).")
        except Exception:
            pass
    # Example rule 3: Late filing (filed after period due date)
    if tax_return.filing_date and tax_return.period and tax_return.period.due_date:
        if tax_return.filing_date.date() > tax_return.period.due_date:
            reasons.append("Return filed after due date.")
    # Add more rules as needed
    if reasons:
        tax_return.is_flagged = True
        tax_return.flag_reason = "; ".join(reasons)
    else:
        tax_return.is_flagged = False
        tax_return.flag_reason = None

def calculate_tax_due(tax_type_id, income, deductions=0):
    """
    Calculate tax due based on tax type, income, and deductions
    This is a simplified implementation - in a real system, this would be more complex
    with progressive tax rates, etc.
    """
    tax_type = TaxType.query.get(tax_type_id)
    taxable_income = max(0, income - deductions)
    
    # Simple tax calculation based on tax type
    if tax_type.code == 'VAT':
        # VAT is typically a flat percentage
        return taxable_income * 0.15  # 15% VAT rate
    elif tax_type.code == 'PIT':
        # Personal Income Tax with progressive rates
        if taxable_income <= 50000:
            return taxable_income * 0.10
        elif taxable_income <= 100000:
            return 5000 + (taxable_income - 50000) * 0.15
        elif taxable_income <= 250000:
            return 12500 + (taxable_income - 100000) * 0.25
        else:
            return 50000 + (taxable_income - 250000) * 0.35
    elif tax_type.code == 'CIT':
        # Corporate Income Tax - typically flat rate
        return taxable_income * 0.28  # 28% corporate tax rate
    elif tax_type.code == 'WT':
        # Withholding Tax - typically flat rate
        return taxable_income * 0.15  # 15% withholding tax rate
    elif tax_type.code == 'PT':
        # Property Tax - typically based on property value
        return taxable_income * 0.02  # 2% property tax rate
    elif tax_type.code == 'EXT':
        # Excise Tax - typically specific rates for specific goods
        return taxable_income * 0.10  # 10% excise tax rate
    else:
        # Default rate for other tax types
        return taxable_income * 0.15  # 15% default rate

def generate_reference_number():
    """
    Generate a unique reference number for tax returns, payments, etc.
    """
    return f"TX-{uuid.uuid4().hex[:8].upper()}"

def get_tax_periods_for_tax_type(tax_type_id):
    """
    Get all tax periods for a specific tax type
    """
    return TaxPeriod.query.filter_by(tax_type_id=tax_type_id).order_by(TaxPeriod.start_date.desc()).all()

def get_current_tax_period(tax_type_id):
    """
    Get the current tax period for a specific tax type
    """
    today = datetime.utcnow().date()
    return TaxPeriod.query.filter_by(
        tax_type_id=tax_type_id,
        status='Open'
    ).filter(
        TaxPeriod.start_date <= today,
        TaxPeriod.end_date >= today
    ).first()

def get_tax_returns_for_account(account_id, tax_type_id=None, status=None):
    """
    Get tax returns for a specific account, optionally filtered by tax type and status
    """
    query = TaxReturn.query.filter_by(account_id=account_id)
    
    if tax_type_id:
        query = query.filter_by(tax_type_id=tax_type_id)
    
    if status:
        query = query.filter_by(status=status)
    
    return query.order_by(TaxReturn.created_at.desc()).all()

def get_payments_for_tax_return(tax_return_id):
    """
    Get all payments for a specific tax return
    """
    return Payment.query.filter_by(tax_return_id=tax_return_id).order_by(Payment.payment_date.desc()).all()

def get_total_paid_for_tax_return(tax_return_id):
    """
    Calculate the total amount paid for a specific tax return
    """
    total = db.session.query(db.func.sum(Payment.amount)).filter_by(
        tax_return_id=tax_return_id,
        status='Completed'
    ).scalar()
    return total or 0

def get_balance_for_tax_return(tax_return_id):
    """
    Calculate the remaining balance for a specific tax return
    """
    tax_return = TaxReturn.query.get(tax_return_id)
    total_paid = get_total_paid_for_tax_return(tax_return_id)
    return max(0, tax_return.due_amount - total_paid)

def get_refunds_for_account(account_id, status=None):
    """
    Get refunds for a specific account, optionally filtered by status
    """
    query = Refund.query.filter_by(account_id=account_id)
    
    if status:
        query = query.filter_by(status=status)
    
    return query.order_by(Refund.request_date.desc()).all()

def get_objections_for_account(account_id, status=None):
    """
    Get objections for a specific account, optionally filtered by status
    """
    query = Objection.query.join(TaxReturn).filter(TaxReturn.account_id == account_id)
    
    if status:
        query = query.filter(Objection.status == status)
    
    return query.order_by(Objection.filing_date.desc()).all()

def get_ledger_entries_for_account(account_id, tax_type_id=None, start_date=None, end_date=None):
    """
    Get ledger entries for a specific account, optionally filtered by tax type and date range
    """
    query = TaxpayerLedger.query.filter_by(account_id=account_id)
    
    if tax_type_id:
        query = query.filter_by(tax_type_id=tax_type_id)
    
    if start_date:
        query = query.filter(TaxpayerLedger.transaction_date >= start_date)
    
    if end_date:
        query = query.filter(TaxpayerLedger.transaction_date <= end_date)
    
    return query.order_by(TaxpayerLedger.transaction_date.desc()).all()

def get_account_balance(account_id, tax_type_id=None):
    """
    Calculate the current balance for an account, optionally for a specific tax type
    """
    query = db.session.query(db.func.sum(TaxpayerLedger.debit_amount).label('debits'),
                           db.func.sum(TaxpayerLedger.credit_amount).label('credits'))\
                    .filter_by(account_id=account_id)
    
    if tax_type_id:
        query = query.filter_by(tax_type_id=tax_type_id)
    
    result = query.first()
    debits = result.debits or 0
    credits = result.credits or 0
    
    return debits - credits

def process_payment(tax_return_id, amount, payment_method, reference_number=None):
    """
    Process a payment for a tax return
    """
    tax_return = TaxReturn.query.get(tax_return_id)
    
    if not tax_return:
        return False, "Tax return not found"
    
    if not reference_number:
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
        balance=tax_return.due_amount - amount,  # This is simplified, should consider previous payments
        reference_number=reference_number
    )
    
    db.session.add(ledger_entry)
    
    # Update tax return status if fully paid
    total_paid = get_total_paid_for_tax_return(tax_return_id) + amount
    
    if total_paid >= tax_return.due_amount:
        tax_return.status = 'Finalized'
    
    db.session.commit()
    
    return True, "Payment processed successfully"

def process_refund_request(account_id, amount, reason):
    """
    Process a refund request
    """
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
    
    return True, "Refund request submitted successfully"

def approve_refund(refund_id):
    """
    Approve a refund request
    """
    refund = Refund.query.get(refund_id)
    
    if not refund:
        return False, "Refund not found"
    
    refund.status = 'Approved'
    refund.approval_date = datetime.utcnow()
    
    # Create ledger entry for approved refund
    ledger_entry = TaxpayerLedger(
        account_id=refund.account_id,
        transaction_date=datetime.utcnow().date(),
        transaction_type='Refund',
        description=f'Approved refund: {refund.reference_number}',
        debit_amount=0,
        credit_amount=refund.amount,
        balance=-refund.amount,  # This is simplified, should consider account balance
        reference_number=refund.reference_number
    )
    
    db.session.add(ledger_entry)
    db.session.commit()
    
    return True, "Refund approved successfully"

def process_objection(tax_return_id, reason):
    """
    Process an objection to a tax assessment
    """
    tax_return = TaxReturn.query.get(tax_return_id)
    
    if not tax_return:
        return False, "Tax return not found"
    
    reference_number = f"OBJ-{uuid.uuid4().hex[:8].upper()}"
    
    # Create objection
    objection = Objection(
        tax_return_id=tax_return_id,
        reason=reason,
        reference_number=reference_number
    )
    
    db.session.add(objection)
    db.session.commit()
    
    return True, "Objection filed successfully"