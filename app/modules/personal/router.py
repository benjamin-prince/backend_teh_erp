from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import func, extract
from typing import List, Optional
from datetime import date, datetime, timedelta
from app.core.database import get_db
from app.core.dependencies import get_current_user
from . import models, schemas

router = APIRouter(prefix="/api/v1/personal", tags=["Personal Life"])


# ── Dashboard ─────────────────────────────────────────────────────────────────

@router.get("/dashboard", response_model=schemas.PersonalDashboardStats)
def get_dashboard(
    period: str = Query("month", enum=["week", "month", "year"]),
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    today = date.today()
    if period == "week":
        start = today - timedelta(days=7)
        label = "Cette semaine"
    elif period == "month":
        start = today.replace(day=1)
        label = today.strftime("%B %Y")
    else:
        start = today.replace(month=1, day=1)
        label = str(today.year)

    expenses = db.query(func.coalesce(func.sum(models.PersonalExpense.amount), 0)).filter(
        models.PersonalExpense.date >= start
    ).scalar()

    income = db.query(func.coalesce(func.sum(models.PersonalIncome.amount), 0)).filter(
        models.PersonalIncome.date >= start
    ).scalar()

    sport_sessions = db.query(func.count(models.SportActivity.id)).filter(
        models.SportActivity.date >= start
    ).scalar()

    sport_minutes = db.query(func.coalesce(func.sum(models.SportActivity.duration_minutes), 0)).filter(
        models.SportActivity.date >= start
    ).scalar()

    calories_burned = db.query(func.coalesce(func.sum(models.SportActivity.calories_burned), 0)).filter(
        models.SportActivity.date >= start
    ).scalar()

    meals_count = db.query(func.count(models.Meal.id)).filter(
        models.Meal.date >= start
    ).scalar()

    avg_calories = db.query(func.avg(models.Meal.calories)).filter(
        models.Meal.date >= start,
        models.Meal.calories.isnot(None)
    ).scalar()

    active_goals = db.query(func.count(models.PersonalGoal.id)).filter(
        models.PersonalGoal.status == models.GoalStatus.ACTIVE
    ).scalar()

    avg_sleep = db.query(func.avg(models.DailySummary.sleep_hours)).filter(
        models.DailySummary.date >= start,
        models.DailySummary.sleep_hours.isnot(None)
    ).scalar()

    avg_mood = db.query(func.avg(models.DailySummary.mood)).filter(
        models.DailySummary.date >= start,
        models.DailySummary.mood.isnot(None)
    ).scalar()

    return schemas.PersonalDashboardStats(
        period_label=label,
        total_expenses=float(expenses),
        total_income=float(income),
        balance=float(income) - float(expenses),
        sport_sessions=sport_sessions,
        total_sport_minutes=int(sport_minutes),
        total_calories_burned=int(calories_burned),
        meals_logged=meals_count,
        avg_daily_calories=float(avg_calories) if avg_calories else None,
        active_goals=active_goals,
        avg_sleep=float(avg_sleep) if avg_sleep else None,
        avg_mood=float(avg_mood) if avg_mood else None,
    )


# ── Expenses ──────────────────────────────────────────────────────────────────

@router.get("/expenses", response_model=List[schemas.PersonalExpenseOut])
def list_expenses(
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
    category: Optional[models.ExpenseCategory] = None,
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    q = db.query(models.PersonalExpense)
    if start_date:
        q = q.filter(models.PersonalExpense.date >= start_date)
    if end_date:
        q = q.filter(models.PersonalExpense.date <= end_date)
    if category:
        q = q.filter(models.PersonalExpense.category == category)
    return q.order_by(models.PersonalExpense.date.desc()).offset(skip).limit(limit).all()


@router.post("/expenses", response_model=schemas.PersonalExpenseOut, status_code=201)
def create_expense(
    data: schemas.PersonalExpenseCreate,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    obj = models.PersonalExpense(**data.dict())
    db.add(obj)
    db.commit()
    db.refresh(obj)
    return obj


@router.put("/expenses/{expense_id}", response_model=schemas.PersonalExpenseOut)
def update_expense(
    expense_id: int,
    data: schemas.PersonalExpenseUpdate,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    obj = db.query(models.PersonalExpense).filter(models.PersonalExpense.id == expense_id).first()
    if not obj:
        raise HTTPException(status_code=404, detail="Expense not found")
    for k, v in data.dict(exclude_unset=True).items():
        setattr(obj, k, v)
    db.commit()
    db.refresh(obj)
    return obj


@router.delete("/expenses/{expense_id}", status_code=204)
def delete_expense(
    expense_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    obj = db.query(models.PersonalExpense).filter(models.PersonalExpense.id == expense_id).first()
    if not obj:
        raise HTTPException(status_code=404, detail="Expense not found")
    db.delete(obj)
    db.commit()


# ── Income ────────────────────────────────────────────────────────────────────

@router.get("/income", response_model=List[schemas.PersonalIncomeOut])
def list_income(
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    q = db.query(models.PersonalIncome)
    if start_date:
        q = q.filter(models.PersonalIncome.date >= start_date)
    if end_date:
        q = q.filter(models.PersonalIncome.date <= end_date)
    return q.order_by(models.PersonalIncome.date.desc()).offset(skip).limit(limit).all()


@router.post("/income", response_model=schemas.PersonalIncomeOut, status_code=201)
def create_income(
    data: schemas.PersonalIncomeCreate,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    obj = models.PersonalIncome(**data.dict())
    db.add(obj)
    db.commit()
    db.refresh(obj)
    return obj


@router.put("/income/{income_id}", response_model=schemas.PersonalIncomeOut)
def update_income(
    income_id: int,
    data: schemas.PersonalIncomeUpdate,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    obj = db.query(models.PersonalIncome).filter(models.PersonalIncome.id == income_id).first()
    if not obj:
        raise HTTPException(status_code=404, detail="Income not found")
    for k, v in data.dict(exclude_unset=True).items():
        setattr(obj, k, v)
    db.commit()
    db.refresh(obj)
    return obj


@router.delete("/income/{income_id}", status_code=204)
def delete_income(
    income_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    obj = db.query(models.PersonalIncome).filter(models.PersonalIncome.id == income_id).first()
    if not obj:
        raise HTTPException(status_code=404, detail="Income not found")
    db.delete(obj)
    db.commit()


# ── Sport ─────────────────────────────────────────────────────────────────────

@router.get("/sport", response_model=List[schemas.SportActivityOut])
def list_sport(
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
    activity_type: Optional[str] = None,
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    q = db.query(models.SportActivity)
    if start_date:
        q = q.filter(models.SportActivity.date >= start_date)
    if end_date:
        q = q.filter(models.SportActivity.date <= end_date)
    if activity_type:
        q = q.filter(models.SportActivity.activity_type.ilike(f"%{activity_type}%"))
    return q.order_by(models.SportActivity.date.desc()).offset(skip).limit(limit).all()


@router.post("/sport", response_model=schemas.SportActivityOut, status_code=201)
def create_sport(
    data: schemas.SportActivityCreate,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    obj = models.SportActivity(**data.dict())
    db.add(obj)
    db.commit()
    db.refresh(obj)
    return obj


@router.put("/sport/{activity_id}", response_model=schemas.SportActivityOut)
def update_sport(
    activity_id: int,
    data: schemas.SportActivityUpdate,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    obj = db.query(models.SportActivity).filter(models.SportActivity.id == activity_id).first()
    if not obj:
        raise HTTPException(status_code=404, detail="Activity not found")
    for k, v in data.dict(exclude_unset=True).items():
        setattr(obj, k, v)
    db.commit()
    db.refresh(obj)
    return obj


@router.delete("/sport/{activity_id}", status_code=204)
def delete_sport(
    activity_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    obj = db.query(models.SportActivity).filter(models.SportActivity.id == activity_id).first()
    if not obj:
        raise HTTPException(status_code=404, detail="Activity not found")
    db.delete(obj)
    db.commit()


# ── Nutrition / Meals ─────────────────────────────────────────────────────────

@router.get("/meals", response_model=List[schemas.MealOut])
def list_meals(
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
    meal_type: Optional[models.MealType] = None,
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    q = db.query(models.Meal)
    if start_date:
        q = q.filter(models.Meal.date >= start_date)
    if end_date:
        q = q.filter(models.Meal.date <= end_date)
    if meal_type:
        q = q.filter(models.Meal.meal_type == meal_type)
    return q.order_by(models.Meal.date.desc()).offset(skip).limit(limit).all()


@router.post("/meals", response_model=schemas.MealOut, status_code=201)
def create_meal(
    data: schemas.MealCreate,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    obj = models.Meal(**data.dict())
    db.add(obj)
    db.commit()
    db.refresh(obj)
    return obj


@router.delete("/meals/{meal_id}", status_code=204)
def delete_meal(
    meal_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    obj = db.query(models.Meal).filter(models.Meal.id == meal_id).first()
    if not obj:
        raise HTTPException(status_code=404, detail="Meal not found")
    db.delete(obj)
    db.commit()


# ── Goals ─────────────────────────────────────────────────────────────────────

@router.get("/goals", response_model=List[schemas.PersonalGoalOut])
def list_goals(
    status: Optional[models.GoalStatus] = None,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    q = db.query(models.PersonalGoal)
    if status:
        q = q.filter(models.PersonalGoal.status == status)
    return q.order_by(models.PersonalGoal.created_at.desc()).all()


@router.post("/goals", response_model=schemas.PersonalGoalOut, status_code=201)
def create_goal(
    data: schemas.PersonalGoalCreate,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    obj = models.PersonalGoal(**data.dict())
    db.add(obj)
    db.commit()
    db.refresh(obj)
    return obj


@router.put("/goals/{goal_id}", response_model=schemas.PersonalGoalOut)
def update_goal(
    goal_id: int,
    data: schemas.PersonalGoalUpdate,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    obj = db.query(models.PersonalGoal).filter(models.PersonalGoal.id == goal_id).first()
    if not obj:
        raise HTTPException(status_code=404, detail="Goal not found")
    for k, v in data.dict(exclude_unset=True).items():
        setattr(obj, k, v)
    db.commit()
    db.refresh(obj)
    return obj


@router.delete("/goals/{goal_id}", status_code=204)
def delete_goal(
    goal_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    obj = db.query(models.PersonalGoal).filter(models.PersonalGoal.id == goal_id).first()
    if not obj:
        raise HTTPException(status_code=404, detail="Goal not found")
    db.delete(obj)
    db.commit()


# ── Daily Summary ─────────────────────────────────────────────────────────────

@router.get("/daily", response_model=List[schemas.DailySummaryOut])
def list_daily(
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    q = db.query(models.DailySummary)
    if start_date:
        q = q.filter(models.DailySummary.date >= start_date)
    if end_date:
        q = q.filter(models.DailySummary.date <= end_date)
    return q.order_by(models.DailySummary.date.desc()).all()


@router.post("/daily", response_model=schemas.DailySummaryOut, status_code=201)
def upsert_daily(
    data: schemas.DailySummaryCreate,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    existing = db.query(models.DailySummary).filter(models.DailySummary.date == data.date).first()
    if existing:
        for k, v in data.dict(exclude_unset=True).items():
            setattr(existing, k, v)
        db.commit()
        db.refresh(existing)
        return existing
    obj = models.DailySummary(**data.dict())
    db.add(obj)
    db.commit()
    db.refresh(obj)
    return obj


# ── Purchase Commitments ──────────────────────────────────────────────────────

@router.get("/purchases", response_model=List[schemas.PurchaseCommitmentOut])
def list_purchases(
    status: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    q = db.query(models.PurchaseCommitment)
    if status:
        q = q.filter(models.PurchaseCommitment.status == status)
    return q.order_by(models.PurchaseCommitment.created_at.desc()).all()


def _income_tag(purchase_id: int) -> str:
    return f"[purchase:{purchase_id}]"

def _expense_tag(purchase_id: int) -> str:
    return f"[achat:{purchase_id}]"

def _sync_purchase_income(db, obj):
    """Replace the single income record for this purchase with the current total."""
    tag = _income_tag(obj.id)
    db.query(models.PersonalIncome).filter(
        models.PersonalIncome.description.like(f"%{tag}%")
    ).delete(synchronize_session=False)

    is_gift = obj.reason.lower().startswith("cadeau")
    received = obj.amount_received or 0.0
    if received > 0 and not is_gift:
        db.add(models.PersonalIncome(
            date=date.today(),
            source=models.IncomeSource.OTHER,
            amount=received,
            currency=obj.currency,
            description=f"Remboursement: {obj.item_name} ({obj.person_name}) {tag}",
        ))

def _sync_purchase_expense(db, obj):
    """Replace the single expense record for this purchase with current price (or remove it)."""
    tag = _expense_tag(obj.id)
    db.query(models.PersonalExpense).filter(
        models.PersonalExpense.description.like(f"%{tag}%")
    ).delete(synchronize_session=False)

    if obj.status == "bought" and obj.price:
        db.add(models.PersonalExpense(
            date=date.today(),
            category=models.ExpenseCategory.SHOPPING,
            amount=obj.price,
            currency=obj.price_currency or obj.currency,
            description=f"Achat: {obj.item_name} pour {obj.person_name} {tag}",
        ))


@router.post("/purchases", response_model=schemas.PurchaseCommitmentOut, status_code=201)
def create_purchase(
    data: schemas.PurchaseCommitmentCreate,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    obj = models.PurchaseCommitment(**data.dict())
    db.add(obj)
    db.flush()  # get obj.id before commit

    _sync_purchase_income(db, obj)
    _sync_purchase_expense(db, obj)

    db.commit()
    db.refresh(obj)
    return obj


@router.patch("/purchases/{purchase_id}", response_model=schemas.PurchaseCommitmentOut)
def update_purchase(
    purchase_id: int,
    data: schemas.PurchaseCommitmentUpdate,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    obj = db.query(models.PurchaseCommitment).filter(models.PurchaseCommitment.id == purchase_id).first()
    if not obj:
        raise HTTPException(404, "Purchase commitment not found")

    for k, v in data.dict(exclude_unset=True).items():
        setattr(obj, k, v)

    # Always replace income and expense records with the current truth
    _sync_purchase_income(db, obj)
    _sync_purchase_expense(db, obj)

    db.commit()
    db.refresh(obj)
    return obj


@router.delete("/purchases/{purchase_id}", status_code=204)
def delete_purchase(
    purchase_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    obj = db.query(models.PurchaseCommitment).filter(models.PurchaseCommitment.id == purchase_id).first()
    if not obj:
        raise HTTPException(404, "Purchase commitment not found")
    db.delete(obj)
    db.commit()


# ── Personal Debts ────────────────────────────────────────────────────────────

def _compute_interest(amount: float, rate: float | None, period: str | None, start: date) -> float:
    """Simple interest: amount × rate% × n_periods elapsed since start."""
    if not rate or not period:
        return 0.0
    today = date.today()
    days = (today - start).days
    if days <= 0:
        return 0.0
    periods_per_year = {"daily": 365, "weekly": 52, "monthly": 12, "yearly": 1}.get(period, 1)
    n_periods = days / (365 / periods_per_year)
    return round(amount * (rate / 100) * n_periods, 2)


def _debt_out(obj: models.PersonalDebt) -> schemas.PersonalDebtOut:
    """Enrich a PersonalDebt ORM object with paid_amount and total_with_interest."""
    paid_amount = sum(p.amount for p in obj.payments if p.currency == obj.currency)
    interest = _compute_interest(obj.amount, obj.interest_rate, obj.interest_period, obj.borrowed_date)
    return schemas.PersonalDebtOut(
        id=obj.id, creditor=obj.creditor, debt_type=obj.debt_type or "personal",
        amount=obj.amount, currency=obj.currency,
        reason=obj.reason, borrowed_date=obj.borrowed_date, due_date=obj.due_date,
        is_paid=obj.is_paid, paid_date=obj.paid_date, notes=obj.notes,
        interest_rate=obj.interest_rate, interest_period=obj.interest_period,
        priority=obj.priority,
        plan_amount=obj.plan_amount, plan_frequency=obj.plan_frequency,
        plan_start_date=obj.plan_start_date, plan_notes=obj.plan_notes,
        created_at=obj.created_at, paid_amount=round(paid_amount, 2),
        total_with_interest=round(obj.amount + interest, 2),
        payments=[schemas.DebtPaymentOut.model_validate(p) for p in obj.payments],
    )


@router.get("/debts", response_model=List[schemas.PersonalDebtOut])
def list_debts(
    status: Optional[str] = Query("active", pattern="^(active|paid|all)$"),
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """List debts. status=active (default) | paid | all"""
    q = db.query(models.PersonalDebt)
    if status == "active":
        q = q.filter(models.PersonalDebt.is_paid == False)
    elif status == "paid":
        q = q.filter(models.PersonalDebt.is_paid == True)
    items = q.order_by(
        models.PersonalDebt.priority.desc().nulls_last(),
        models.PersonalDebt.due_date.asc().nulls_last(),
        models.PersonalDebt.borrowed_date.desc(),
    ).all()
    return [_debt_out(d) for d in items]


@router.post("/debts", response_model=schemas.PersonalDebtOut, status_code=201)
def create_debt(
    data: schemas.PersonalDebtCreate,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    obj = models.PersonalDebt(**data.model_dump())
    db.add(obj)
    db.commit()
    db.refresh(obj)
    return _debt_out(obj)


@router.patch("/debts/{debt_id}", response_model=schemas.PersonalDebtOut)
def update_debt(
    debt_id: int,
    data: schemas.PersonalDebtUpdate,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    obj = db.query(models.PersonalDebt).filter(models.PersonalDebt.id == debt_id).first()
    if not obj:
        raise HTTPException(404, "Debt not found")
    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(obj, field, value)
    # auto-set paid_date when marking paid if not provided
    if data.is_paid and not obj.paid_date:
        obj.paid_date = date.today()
    db.commit()
    db.refresh(obj)
    return _debt_out(obj)


@router.delete("/debts/{debt_id}", status_code=204)
def delete_debt(
    debt_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    obj = db.query(models.PersonalDebt).filter(models.PersonalDebt.id == debt_id).first()
    if not obj:
        raise HTTPException(404, "Debt not found")
    db.delete(obj)
    db.commit()


# ── Debt Payments (repayment plan tracking) ───────────────────────────────────

@router.get("/debts/{debt_id}/payments", response_model=List[schemas.DebtPaymentOut])
def list_payments(
    debt_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    debt = db.query(models.PersonalDebt).filter(models.PersonalDebt.id == debt_id).first()
    if not debt:
        raise HTTPException(404, "Debt not found")
    return debt.payments


@router.post("/debts/{debt_id}/payments", response_model=schemas.DebtPaymentOut, status_code=201)
def add_payment(
    debt_id: int,
    data: schemas.DebtPaymentCreate,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    debt = db.query(models.PersonalDebt).filter(models.PersonalDebt.id == debt_id).first()
    if not debt:
        raise HTTPException(404, "Debt not found")
    payment = models.PersonalDebtPayment(debt_id=debt_id, **data.model_dump())
    db.add(payment)
    # auto-mark debt as paid if total paid_amount >= debt.amount (same currency)
    db.flush()
    total_paid = sum(
        p.amount for p in debt.payments
        if p.currency == debt.currency
    ) + (data.amount if data.currency == debt.currency else 0)
    if total_paid >= debt.amount and not debt.is_paid:
        debt.is_paid = True
        debt.paid_date = data.payment_date
    db.commit()
    db.refresh(payment)
    return payment


@router.delete("/debts/{debt_id}/payments/{payment_id}", status_code=204)
def delete_payment(
    debt_id: int,
    payment_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    payment = db.query(models.PersonalDebtPayment).filter(
        models.PersonalDebtPayment.id == payment_id,
        models.PersonalDebtPayment.debt_id == debt_id,
    ).first()
    if not payment:
        raise HTTPException(404, "Payment not found")
    db.delete(payment)
    db.commit()
