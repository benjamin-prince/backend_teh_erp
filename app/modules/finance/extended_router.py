"""TEHTEK — Finance Extended Router.
Covers: income, finance_expenses, locations, money_accounts,
        debts, receivables, summary.

Register in main.py BEFORE finance_router so /finance/expenses
is served by this router (finance_expenses table) not the old one.
"""
from datetime import datetime
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.dependencies import get_current_user, require_permission
from app.modules.finance.models import Debt, DebtPayment
from app.modules.finance.extended_models import (
    IncomeRecord, FinanceExpense, Location, MoneyAccount,
    Receivable, BudgetLine,
)

router = APIRouter(
    prefix="/api/v1/finance",
    tags=["finance-extended"],
    dependencies=[Depends(get_current_user)],
)

# ── Number generators ─────────────────────────────────────────────────────────

def _next_number(db: Session, model, col, prefix: str, company_id: int) -> str:
    """Generate INC-2026-05-0001 style numbers per company per month."""
    now = datetime.utcnow()
    ym = f"{now.year}-{now.month:02d}"
    count = (
        db.query(func.count(model.id))
        .filter(
            col == company_id,
            func.extract("year",  model.created_at) == now.year,
            func.extract("month", model.created_at) == now.month,
        )
        .scalar()
    ) or 0
    return f"{prefix}-{ym}-{(count + 1):04d}"


# ── Pydantic schemas ──────────────────────────────────────────────────────────

class IncomeCreate(BaseModel):
    date:             str
    description:      str
    category:         str
    ref_model:        Optional[str] = None
    ref_id:           Optional[int] = None
    ref_label:        Optional[str] = None
    amount:           float
    currency:         str = "XAF"
    exchange_rate:    float = 1.0
    payment_method:   str = "cash"
    money_account_id: Optional[int] = None
    status:           str = "received"
    notes:            Optional[str] = None
    receipt_url:      Optional[str] = None


class ExpenseCreate(BaseModel):
    date:             str
    description:      str
    category:         str
    ref_model:        Optional[str] = None
    ref_id:           Optional[int] = None
    ref_label:        Optional[str] = None
    amount:           float
    currency:         str = "XAF"
    exchange_rate:    float = 1.0
    payment_method:   Optional[str] = None
    money_account_id: Optional[int] = None
    status:           str = "pending"
    notes:            Optional[str] = None
    receipt_url:      Optional[str] = None


class LocationCreate(BaseModel):
    name:                    str
    type:                    str
    address:                 Optional[str] = None
    city:                    str
    country:                 str = "Cameroon"
    currency:                str = "XAF"
    rent_monthly:            float = 0
    electricity_monthly:     float = 0
    water_monthly:           float = 0
    internet_monthly:        float = 0
    other_utilities_monthly: float = 0
    lease_start:             Optional[str] = None
    lease_end:               Optional[str] = None
    next_payment_due:        Optional[str] = None
    landlord_name:           Optional[str] = None
    landlord_contact:        Optional[str] = None
    notes:                   Optional[str] = None


class DebtCreate(BaseModel):
    creditor_name:    str
    creditor_type:    str
    purpose:          str
    ref_model:        Optional[str] = None
    ref_id:           Optional[int] = None
    ref_label:        Optional[str] = None
    principal:        float
    outstanding:      Optional[float] = None
    monthly_payment:  Optional[float] = None
    interest_rate:    Optional[float] = None
    start_date:       str
    end_date:         Optional[str] = None
    next_due_date:    Optional[str] = None
    currency:         str = "XAF"
    exchange_rate:    float = 1.0
    notes:            Optional[str] = None


class DebtPaymentCreate(BaseModel):
    amount:           float
    payment_date:     Optional[str] = None
    money_account_id: Optional[int] = None
    payment_method:   str = "bank_transfer"
    note:             Optional[str] = None


class DebtUpdate(BaseModel):
    status:         Optional[str] = None
    outstanding:    Optional[float] = None
    next_due_date:  Optional[str] = None
    notes:          Optional[str] = None


class ReceivableCreate(BaseModel):
    client_name:    str
    client_id:      Optional[int] = None
    invoice_number: Optional[str] = None
    ref_model:      str
    ref_id:         Optional[int] = None
    ref_label:      str
    amount:         float
    currency:       str = "XAF"
    exchange_rate:  float = 1.0
    issue_date:     str
    due_date:       str
    notes:          Optional[str] = None


class CollectPayment(BaseModel):
    amount:           float
    money_account_id: Optional[int] = None
    payment_method:   str = "cash"
    note:             Optional[str] = None


def _parse_date(s: Optional[str]) -> Optional[datetime]:
    if not s:
        return None
    for fmt in ("%Y-%m-%dT%H:%M:%S", "%Y-%m-%d"):
        try:
            return datetime.strptime(s, fmt)
        except ValueError:
            continue
    return None


# ══════════════════════════════════════════════════════════════════════════════
# INCOME
# ══════════════════════════════════════════════════════════════════════════════

@router.get("/income")
def list_income(
    skip:     int = 0,
    limit:    int = 100,
    period:   Optional[str] = None,   # "today" | "month" | "year"
    category: Optional[str] = None,
    db:       Session = Depends(get_db),
    current_user=Depends(require_permission("finance:income")),
):
    q = db.query(IncomeRecord).filter(
        IncomeRecord.company_id == current_user.company_id,
        IncomeRecord.deleted_at.is_(None),
    )
    if category:
        q = q.filter(IncomeRecord.category == category)
    if period:
        now = datetime.utcnow()
        if period == "today":
            q = q.filter(func.date(IncomeRecord.date) == now.date())
        elif period == "month":
            q = q.filter(
                func.extract("year",  IncomeRecord.date) == now.year,
                func.extract("month", IncomeRecord.date) == now.month,
            )
        elif period == "year":
            q = q.filter(func.extract("year", IncomeRecord.date) == now.year)
    records = q.order_by(IncomeRecord.date.desc()).offset(skip).limit(limit).all()

    # Resolve the underlying source type for income tied to an invoice
    # (the invoice itself carries order / service_project / shipment / …).
    from app.modules.finance.models import Invoice
    inv_ids = [r.ref_id for r in records if r.ref_model == "invoice" and r.ref_id]
    inv_src = {}
    if inv_ids:
        for inv in db.query(Invoice).filter(Invoice.id.in_(inv_ids)).all():
            src = inv.ref_model or "invoice"
            if src == "service_project":
                src = "project"
            inv_src[inv.id] = src

    for r in records:
        if r.money_account_id:
            acc = db.query(MoneyAccount).filter_by(id=r.money_account_id).first()
            r.__dict__['money_account_name'] = acc.name if acc else None
        else:
            r.__dict__['money_account_name'] = None
        # Normalized source type for filtering (order | project | shipment | …)
        if r.ref_model == "invoice" and r.ref_id in inv_src:
            r.__dict__['source_model'] = inv_src[r.ref_id]
        elif r.ref_model == "service_project":
            r.__dict__['source_model'] = "project"
        else:
            r.__dict__['source_model'] = r.ref_model
    return records


@router.post("/income", status_code=201)
def create_income(
    body: IncomeCreate,
    db:   Session = Depends(get_db),
    current_user=Depends(require_permission("finance:income")),
):
    number     = _next_number(db, IncomeRecord, IncomeRecord.company_id, "INC", current_user.company_id)
    amount_base = body.amount * body.exchange_rate
    record = IncomeRecord(
        company_id    = current_user.company_id,
        branch_id     = current_user.branch_id,
        income_number = number,
        date          = _parse_date(body.date) or datetime.utcnow(),
        description   = body.description,
        category      = body.category,
        ref_model     = body.ref_model,
        ref_id        = body.ref_id,
        ref_label     = body.ref_label,
        amount        = body.amount,
        currency      = body.currency,
        exchange_rate = body.exchange_rate,
        amount_base   = amount_base,
        payment_method   = body.payment_method,
        money_account_id = body.money_account_id or None,
        status        = body.status,
        notes         = body.notes,
        receipt_url   = body.receipt_url,
        created_by    = current_user.id,
    )
    db.add(record)
    # Update money account balance
    if body.money_account_id:
        acc = db.query(MoneyAccount).filter_by(id=body.money_account_id, company_id=current_user.company_id).first()
        if acc:
            acc.current_balance = float(acc.current_balance or 0) + amount_base
    db.commit()
    db.refresh(record)
    return record


@router.get("/income/{income_id}")
def get_income(
    income_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(require_permission("finance:income")),
):
    rec = db.query(IncomeRecord).filter_by(id=income_id, company_id=current_user.company_id).first()
    if not rec:
        raise HTTPException(404, "Income entry not found")
    return rec


@router.delete("/income/{income_id}", status_code=204)
def delete_income(
    income_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(require_permission("finance:income")),
):
    rec = db.query(IncomeRecord).filter_by(id=income_id, company_id=current_user.company_id).first()
    if not rec:
        raise HTTPException(404, "Income entry not found")
    rec.deleted_at = datetime.utcnow()
    db.commit()


# ══════════════════════════════════════════════════════════════════════════════
# FINANCE EXPENSES  (replaces old /finance/expenses → old `expenses` table)
# ══════════════════════════════════════════════════════════════════════════════

@router.get("/expenses")
def list_finance_expenses(
    skip:     int = 0,
    limit:    int = 100,
    period:   Optional[str] = None,
    category: Optional[str] = None,
    db:       Session = Depends(get_db),
    current_user=Depends(require_permission("finance:expenses")),
):
    q = db.query(FinanceExpense).filter(
        FinanceExpense.company_id == current_user.company_id,
        FinanceExpense.deleted_at.is_(None),
    )
    if category:
        q = q.filter(FinanceExpense.category == category)
    if period:
        now = datetime.utcnow()
        if period == "today":
            q = q.filter(func.date(FinanceExpense.date) == now.date())
        elif period == "month":
            q = q.filter(
                func.extract("year",  FinanceExpense.date) == now.year,
                func.extract("month", FinanceExpense.date) == now.month,
            )
        elif period == "year":
            q = q.filter(func.extract("year", FinanceExpense.date) == now.year)
    records = q.order_by(FinanceExpense.date.desc()).offset(skip).limit(limit).all()
    for r in records:
        if r.money_account_id:
            acc = db.query(MoneyAccount).filter_by(id=r.money_account_id).first()
            r.__dict__['money_account_name'] = acc.name if acc else None
        else:
            r.__dict__['money_account_name'] = None
    return records


@router.post("/expenses", status_code=201)
def create_finance_expense(
    body: ExpenseCreate,
    db:   Session = Depends(get_db),
    current_user=Depends(require_permission("finance:expenses")),
):
    number      = _next_number(db, FinanceExpense, FinanceExpense.company_id, "EXP", current_user.company_id)
    amount_base = body.amount * body.exchange_rate
    record = FinanceExpense(
        company_id    = current_user.company_id,
        branch_id     = current_user.branch_id,
        expense_number = number,
        date          = _parse_date(body.date) or datetime.utcnow(),
        description   = body.description,
        category      = body.category,
        ref_model     = body.ref_model,
        ref_id        = body.ref_id,
        ref_label     = body.ref_label,
        amount        = body.amount,
        currency      = body.currency,
        exchange_rate = body.exchange_rate,
        amount_base   = amount_base,
        payment_method   = body.payment_method,
        money_account_id = body.money_account_id or None,
        status        = body.status,
        notes         = body.notes,
        receipt_url   = body.receipt_url,
        created_by    = current_user.id,
    )
    db.add(record)
    if body.money_account_id:
        acc = db.query(MoneyAccount).filter_by(id=body.money_account_id, company_id=current_user.company_id).first()
        if acc:
            acc.current_balance = float(acc.current_balance or 0) - amount_base
    db.commit()
    db.refresh(record)
    return record


@router.delete("/expenses/{expense_id}", status_code=204)
def delete_finance_expense(
    expense_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(require_permission("finance:expenses")),
):
    rec = db.query(FinanceExpense).filter_by(id=expense_id, company_id=current_user.company_id, is_active=True).first()
    if not rec:
        raise HTTPException(404, "Expense not found")
    rec.deleted_at = datetime.utcnow()
    db.commit()


# ══════════════════════════════════════════════════════════════════════════════
# LOCATIONS
# ══════════════════════════════════════════════════════════════════════════════

@router.get("/locations")
def list_locations(
    db: Session = Depends(get_db),
    current_user=Depends(require_permission("finance:locations")),
):
    return db.query(Location).filter_by(company_id=current_user.company_id).all()


@router.post("/locations", status_code=201)
def create_location(
    body: LocationCreate,
    db:   Session = Depends(get_db),
    current_user=Depends(require_permission("finance:locations")),
):
    loc = Location(
        company_id              = current_user.company_id,
        name                    = body.name,
        type                    = body.type,
        address                 = body.address,
        city                    = body.city,
        country                 = body.country,
        currency                = body.currency,
        rent_monthly            = body.rent_monthly,
        electricity_monthly     = body.electricity_monthly,
        water_monthly           = body.water_monthly,
        internet_monthly        = body.internet_monthly,
        other_utilities_monthly = body.other_utilities_monthly,
        lease_start             = _parse_date(body.lease_start),
        lease_end               = _parse_date(body.lease_end),
        next_payment_due        = _parse_date(body.next_payment_due),
        landlord_name           = body.landlord_name,
        landlord_contact        = body.landlord_contact,
        notes                   = body.notes,
    )
    db.add(loc)
    db.commit()
    db.refresh(loc)
    return loc


@router.patch("/locations/{location_id}")
def update_location(
    location_id: int,
    body: LocationCreate,
    db:   Session = Depends(get_db),
    current_user=Depends(require_permission("finance:locations")),
):
    loc = db.query(Location).filter_by(id=location_id, company_id=current_user.company_id).first()
    if not loc:
        raise HTTPException(404, "Location not found")
    for field, value in body.model_dump(exclude_unset=True).items():
        if field in ("lease_start", "lease_end", "next_payment_due"):
            setattr(loc, field, _parse_date(value))
        else:
            setattr(loc, field, value)
    db.commit()
    db.refresh(loc)
    return loc


@router.delete("/locations/{location_id}", status_code=204)
def delete_location(
    location_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(require_permission("finance:locations")),
):
    loc = db.query(Location).filter_by(id=location_id, company_id=current_user.company_id).first()
    if not loc:
        raise HTTPException(404, "Location not found")
    db.delete(loc)
    db.commit()


# ══════════════════════════════════════════════════════════════════════════════
# MONEY ACCOUNTS / BALANCES
# ══════════════════════════════════════════════════════════════════════════════


# ══════════════════════════════════════════════════════════════════════════════
# DEBT
# ══════════════════════════════════════════════════════════════════════════════

@router.get("/debt")
def list_debts(
    status: Optional[str] = None,
    skip:   int = 0,
    limit:  int = 100,
    db:     Session = Depends(get_db),
    current_user=Depends(require_permission("finance:debt")),
):
    q = db.query(Debt).filter_by(company_id=current_user.company_id)
    if status:
        q = q.filter(Debt.status == status)
    return q.order_by(Debt.created_at.desc()).offset(skip).limit(limit).all()


@router.post("/debt", status_code=201)
def create_debt(
    body: DebtCreate,
    db:   Session = Depends(get_db),
    current_user=Depends(require_permission("finance:debt")),
):
    number      = _next_number(db, Debt, Debt.company_id, "DBT", current_user.company_id)
    outstanding = body.outstanding if body.outstanding is not None else body.principal
    record = Debt(
        company_id    = current_user.company_id,
        debt_number   = number,
        creditor_name = body.creditor_name,
        creditor_type = body.creditor_type,
        purpose       = body.purpose,
        ref_model     = body.ref_model,
        ref_id        = body.ref_id,
        ref_label     = body.ref_label,
        principal     = body.principal,
        outstanding   = outstanding,
        monthly_payment = body.monthly_payment,
        interest_rate = body.interest_rate,
        start_date    = _parse_date(body.start_date) or datetime.utcnow(),
        end_date      = _parse_date(body.end_date),
        next_due_date = _parse_date(body.next_due_date),
        currency      = body.currency,
        exchange_rate = body.exchange_rate,
        amount_base   = body.principal * body.exchange_rate,
        notes         = body.notes,
    )
    db.add(record)
    db.commit()
    db.refresh(record)
    return record


@router.patch("/debt/{debt_id}")
def update_debt(
    debt_id: int,
    body:    DebtUpdate,
    db:      Session = Depends(get_db),
    current_user=Depends(require_permission("finance:debt")),
):
    d = db.query(Debt).filter_by(id=debt_id, company_id=current_user.company_id).first()
    if not d:
        raise HTTPException(404, "Debt not found")
    if body.status:
        d.status = body.status
    if body.outstanding is not None:
        d.outstanding = body.outstanding
    if body.next_due_date:
        d.next_due_date = _parse_date(body.next_due_date)
    if body.notes is not None:
        d.notes = body.notes
    d.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(d)
    return d


@router.post("/debt/{debt_id}/payment", status_code=201)
def record_debt_payment(
    debt_id: int,
    body:    DebtPaymentCreate,
    db:      Session = Depends(get_db),
    current_user=Depends(require_permission("finance:debt")),
):
    d = db.query(Debt).filter_by(id=debt_id, company_id=current_user.company_id).first()
    if not d:
        raise HTTPException(404, "Debt not found")
    payment = DebtPayment(
        company_id       = current_user.company_id,
        debt_id          = debt_id,
        amount           = body.amount,
        payment_date     = _parse_date(body.payment_date) or datetime.utcnow(),
        money_account_id = body.money_account_id or None,
        payment_method   = body.payment_method,
        note             = body.note,
        created_by       = current_user.id,
    )
    db.add(payment)
    # Update outstanding
    new_outstanding = max(0, float(d.outstanding) - body.amount)
    d.outstanding         = new_outstanding
    d.last_payment_date   = datetime.utcnow()
    d.last_payment_amount = body.amount
    if new_outstanding <= 0:
        d.status = "paid_off"
    d.updated_at = datetime.utcnow()
    # Debit account
    acc = db.query(MoneyAccount).filter_by(id=body.money_account_id, company_id=current_user.company_id).first()
    if acc:
        acc.current_balance = float(acc.current_balance or 0) - body.amount
    db.commit()
    db.refresh(d)
    return d


@router.delete("/debt/{debt_id}", status_code=204)
def delete_debt(
    debt_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(require_permission("finance:debt")),
):
    d = db.query(Debt).filter_by(id=debt_id, company_id=current_user.company_id).first()
    if not d:
        raise HTTPException(404, "Debt not found")
    db.delete(d)
    db.commit()


# ══════════════════════════════════════════════════════════════════════════════
# RECEIVABLES
# ══════════════════════════════════════════════════════════════════════════════

@router.get("/receivables")
def list_receivables(
    status: Optional[str] = None,
    skip:   int = 0,
    limit:  int = 100,
    db:     Session = Depends(get_db),
    current_user=Depends(require_permission("finance:receivables")),
):
    q = db.query(Receivable).filter_by(company_id=current_user.company_id)
    if status:
        q = q.filter(Receivable.status == status)
    return q.order_by(Receivable.due_date.asc()).offset(skip).limit(limit).all()


@router.post("/receivables", status_code=201)
def create_receivable(
    body: ReceivableCreate,
    db:   Session = Depends(get_db),
    current_user=Depends(require_permission("finance:receivables")),
):
    number = _next_number(db, Receivable, Receivable.company_id, "RCV", current_user.company_id)
    record = Receivable(
        company_id        = current_user.company_id,
        receivable_number = number,
        client_name       = body.client_name,
        client_id         = body.client_id,
        invoice_number    = body.invoice_number,
        ref_model         = body.ref_model,
        ref_id            = body.ref_id,
        ref_label         = body.ref_label,
        amount            = body.amount,
        paid_amount       = 0,
        balance_due       = body.amount,
        currency          = body.currency,
        exchange_rate     = body.exchange_rate,
        amount_base       = body.amount * body.exchange_rate,
        issue_date        = _parse_date(body.issue_date) or datetime.utcnow(),
        due_date          = _parse_date(body.due_date)   or datetime.utcnow(),
        status            = "draft",
        notes             = body.notes,
    )
    db.add(record)
    db.commit()
    db.refresh(record)
    return record


@router.patch("/receivables/{receivable_id}")
def update_receivable(
    receivable_id: int,
    body:          dict,
    db:            Session = Depends(get_db),
    current_user=Depends(require_permission("finance:receivables")),
):
    rec = db.query(Receivable).filter_by(id=receivable_id, company_id=current_user.company_id).first()
    if not rec:
        raise HTTPException(404, "Receivable not found")
    for k, v in body.items():
        if hasattr(rec, k):
            setattr(rec, k, v)
    rec.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(rec)
    return rec


@router.post("/receivables/{receivable_id}/collect")
def collect_receivable(
    receivable_id: int,
    body:          CollectPayment,
    db:            Session = Depends(get_db),
    current_user=Depends(require_permission("finance:receivables")),
):
    rec = db.query(Receivable).filter_by(id=receivable_id, company_id=current_user.company_id).first()
    if not rec:
        raise HTTPException(404, "Receivable not found")
    rec.paid_amount  = float(rec.paid_amount or 0) + body.amount
    rec.balance_due  = max(0, float(rec.amount) - float(rec.paid_amount))
    rec.status       = "collected" if rec.balance_due <= 0 else "partial"
    rec.updated_at   = datetime.utcnow()
    # Credit account
    acc = db.query(MoneyAccount).filter_by(id=body.money_account_id, company_id=current_user.company_id).first()
    if acc:
        acc.current_balance = float(acc.current_balance or 0) + body.amount
    db.commit()
    db.refresh(rec)
    return rec


@router.delete("/receivables/{receivable_id}", status_code=204)
def delete_receivable(
    receivable_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(require_permission("finance:receivables")),
):
    rec = db.query(Receivable).filter_by(id=receivable_id, company_id=current_user.company_id).first()
    if not rec:
        raise HTTPException(404, "Receivable not found")
    db.delete(rec)
    db.commit()


# ══════════════════════════════════════════════════════════════════════════════
# SUMMARY
# ══════════════════════════════════════════════════════════════════════════════

@router.get("/summary")
def finance_summary(
    period: str = "month",
    db:     Session = Depends(get_db),
    current_user=Depends(require_permission("finance:summary")),
):
    now = datetime.utcnow()

    def _filter_period(q, date_col):
        if period == "today":
            return q.filter(func.date(date_col) == now.date())
        elif period == "month":
            return q.filter(
                func.extract("year",  date_col) == now.year,
                func.extract("month", date_col) == now.month,
            )
        elif period == "year":
            return q.filter(func.extract("year", date_col) == now.year)
        return q

    cid = current_user.company_id

    income_q = db.query(func.coalesce(func.sum(IncomeRecord.amount_base), 0)).filter(
        IncomeRecord.company_id == cid,
        IncomeRecord.deleted_at.is_(None),
        IncomeRecord.status == "received",
    )
    total_income = float(_filter_period(income_q, IncomeRecord.date).scalar() or 0)

    expense_q = db.query(func.coalesce(func.sum(FinanceExpense.amount_base), 0)).filter(
        FinanceExpense.company_id == cid,
        FinanceExpense.deleted_at.is_(None),
        FinanceExpense.status == "paid",
    )
    total_expenses = float(_filter_period(expense_q, FinanceExpense.date).scalar() or 0)

    total_debt = float(
        db.query(func.coalesce(func.sum(Debt.outstanding), 0))
        .filter(Debt.company_id == cid, Debt.status != "paid_off")
        .scalar() or 0
    )
    overdue_debt = float(
        db.query(func.coalesce(func.sum(Debt.outstanding), 0))
        .filter(Debt.company_id == cid, Debt.status == "overdue")
        .scalar() or 0
    )

    total_receivable = float(
        db.query(func.coalesce(func.sum(Receivable.balance_due), 0))
        .filter(Receivable.company_id == cid, Receivable.status.notin_(["collected", "written_off"]))
        .scalar() or 0
    )
    overdue_receivable = float(
        db.query(func.coalesce(func.sum(Receivable.balance_due), 0))
        .filter(Receivable.company_id == cid, Receivable.status == "overdue")
        .scalar() or 0
    )

    return {
        "period":                period,
        "total_income":          total_income,
        "total_expenses":        total_expenses,
        "net_cash":              total_income - total_expenses,
        "total_debt_outstanding": total_debt,
        "total_receivable":      total_receivable,
        "overdue_debt":          overdue_debt,
        "overdue_receivable":    overdue_receivable,
        "currency":              "XAF",
    }


# ══════════════════════════════════════════════════════════════════════════════
# BUDGET
# ══════════════════════════════════════════════════════════════════════════════

class BudgetCreate(BaseModel):
    period_year:   int
    period_month:  Optional[int] = None
    category:      str
    label:         str
    budget_amount: float
    currency:      str = "XAF"
    notes:         Optional[str] = None


@router.get("/budget")
def list_budget(
    year:  Optional[int] = None,
    month: Optional[int] = None,
    db:    Session = Depends(get_db),
    current_user=Depends(require_permission("finance:budget")),
):
    q = db.query(BudgetLine).filter_by(company_id=current_user.company_id)
    if year:
        q = q.filter(BudgetLine.period_year == year)
    if month:
        q = q.filter(BudgetLine.period_month == month)
    return q.order_by(BudgetLine.period_year.desc(), BudgetLine.period_month.desc()).all()


@router.post("/budget", status_code=201)
def create_budget(
    body: BudgetCreate,
    db:   Session = Depends(get_db),
    current_user=Depends(require_permission("finance:budget")),
):
    line = BudgetLine(
        company_id    = current_user.company_id,
        period_year   = body.period_year,
        period_month  = body.period_month,
        category      = body.category,
        label         = body.label,
        budget_amount = body.budget_amount,
        spent_amount  = 0,
        currency      = body.currency,
        notes         = body.notes,
    )
    db.add(line)
    db.commit()
    db.refresh(line)
    return line


@router.patch("/budget/{budget_id}")
def update_budget(
    budget_id: int,
    body:      BudgetCreate,
    db:        Session = Depends(get_db),
    current_user=Depends(require_permission("finance:budget")),
):
    line = db.query(BudgetLine).filter_by(id=budget_id, company_id=current_user.company_id).first()
    if not line:
        raise HTTPException(404, "Budget line not found")
    for k, v in body.model_dump(exclude_unset=True).items():
        setattr(line, k, v)
    line.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(line)
    return line


@router.delete("/budget/{budget_id}", status_code=204)
def delete_budget(
    budget_id: int,
    db:        Session = Depends(get_db),
    current_user=Depends(require_permission("finance:budget")),
):
    line = db.query(BudgetLine).filter_by(id=budget_id, company_id=current_user.company_id).first()
    if not line:
        raise HTTPException(404, "Budget line not found")
    db.delete(line)
    db.commit()


# ── Append to app/modules/finance/extended_router.py ─────────────────────────
# Also add MoneyAccount to the import at the top of this file, e.g.:
#   from app.modules.finance.extended_models import Debt, DebtPayment, MoneyAccount

from app.modules.finance.extended_models import MoneyAccount


# ── Pydantic schemas ──────────────────────────────────────────────────────────

class MoneyAccountCreate(BaseModel):
    name:            str
    account_type:    str   = "cash"   # cash | bank | mobile_money | other
    currency:        str   = "XAF"
    opening_balance: float = 0.0
    notes:           Optional[str] = None


class MoneyAccountUpdate(BaseModel):
    name:         Optional[str]   = None
    type:         Optional[str]   = None
    currency:     Optional[str]   = None
    notes:        Optional[str]   = None


class MoneyAccountAdjust(BaseModel):
    new_balance: float
    notes:       str


# ── Helper ────────────────────────────────────────────────────────────────────

def _get_account_or_404(account_id: int, company_id: int, db: Session) -> MoneyAccount:
    acct = db.query(MoneyAccount).filter_by(
        id=account_id, company_id=company_id, is_active=True
    ).first()
    if not acct:
        raise HTTPException(404, "Money account not found")
    return acct


# ── Endpoints ─────────────────────────────────────────────────────────────────

@router.get("/accounts")
def list_money_accounts(
    db: Session = Depends(get_db),
    current_user=Depends(require_permission("finance:accounts")),
):
    accounts = (
        db.query(MoneyAccount)
        .filter_by(company_id=current_user.company_id, is_active=True)
        .order_by(MoneyAccount.type, MoneyAccount.name)
        .all()
    )

    summary: dict[str, float] = {
        "cash": 0.0, "bank": 0.0, "mobile_money": 0.0, "other": 0.0
    }
    for a in accounts:
        key = a.type if a.type in summary else "other"
        summary[key] += float(a.current_balance)

    return {
        "accounts": accounts,
        "summary": {
            "total_liquid": sum(summary.values()),
            **summary,
        },
    }


@router.post("/accounts", status_code=201)
def create_money_account(
    body: MoneyAccountCreate,
    db:   Session = Depends(get_db),
    current_user=Depends(require_permission("finance:accounts")),
):
    existing = db.query(MoneyAccount).filter_by(
        company_id=current_user.company_id,
        name=body.name,
        is_active=True,
    ).first()
    if existing:
        raise HTTPException(400, f"An account named '{body.name}' already exists")

    acct = MoneyAccount(
        company_id=current_user.company_id,
        name=body.name,
        type=body.account_type,
        currency=body.currency,
        opening_balance=body.opening_balance,
        current_balance=body.opening_balance,
        notes=body.notes,
    )
    db.add(acct)
    db.commit()
    db.refresh(acct)
    return acct


@router.get("/accounts/{account_id}")
def get_money_account(
    account_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(require_permission("finance:accounts")),
):
    return _get_account_or_404(account_id, current_user.company_id, db)


@router.patch("/accounts/{account_id}")
def update_money_account(
    account_id: int,
    body: MoneyAccountUpdate,
    db:   Session = Depends(get_db),
    current_user=Depends(require_permission("finance:accounts")),
):
    acct = _get_account_or_404(account_id, current_user.company_id, db)
    for k, v in body.model_dump(exclude_unset=True).items():
        setattr(acct, k, v)
    acct.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(acct)
    return acct


@router.post("/accounts/{account_id}/adjust")
def adjust_account_balance(
    account_id: int,
    body: MoneyAccountAdjust,
    db:   Session = Depends(get_db),
    current_user=Depends(require_permission("finance:accounts")),
):
    """Manual balance correction after physical cash count."""
    acct = _get_account_or_404(account_id, current_user.company_id, db)
    old = acct.current_balance
    acct.current_balance = body.new_balance
    acct.notes = (
        f"[Adjusted {datetime.utcnow().date()} by user {current_user.id}] "
        f"{old} → {body.new_balance}. {body.notes}\n"
        + (acct.notes or "")
    )
    acct.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(acct)
    return acct


@router.delete("/accounts/{account_id}", status_code=204)
def delete_money_account(
    account_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(require_permission("finance:accounts")),
):
    acct = _get_account_or_404(account_id, current_user.company_id, db)
    if acct.current_balance != 0:
        raise HTTPException(
            400,
            f"Cannot delete account with a non-zero balance "
            f"({acct.current_balance} {acct.currency}). Adjust to 0 first."
        )
    acct.is_active = False
    db.commit()