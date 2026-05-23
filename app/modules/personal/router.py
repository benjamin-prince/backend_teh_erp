from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import func, extract
from typing import List, Optional
from datetime import date, datetime, timedelta
from app.core.database import get_db
from app.core.dependencies import get_current_user
from . import models, schemas

router = APIRouter(prefix="/personal", tags=["Personal Life"])


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


@router.post("/purchases", response_model=schemas.PurchaseCommitmentOut, status_code=201)
def create_purchase(
    data: schemas.PurchaseCommitmentCreate,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    obj = models.PurchaseCommitment(**data.dict())
    db.add(obj)
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
