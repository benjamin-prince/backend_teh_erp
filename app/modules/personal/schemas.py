from pydantic import BaseModel, Field
from typing import Optional
from datetime import date, datetime
from .models import (
    ExpenseCategory, IncomeSource, SportIntensity,
    MealType, GoalType, GoalStatus, PaymentMethod
)


# ── Personal Expense ─────────────────────────────────────────────────────────

class PersonalExpenseCreate(BaseModel):
    date: date
    category: ExpenseCategory = ExpenseCategory.OTHER
    amount: float = Field(..., gt=0)
    currency: str = "XAF"
    description: Optional[str] = None
    payment_method: PaymentMethod = PaymentMethod.CASH
    is_recurring: bool = False
    tags: Optional[str] = None


class PersonalExpenseUpdate(BaseModel):
    date: Optional[date] = None
    category: Optional[ExpenseCategory] = None
    amount: Optional[float] = Field(None, gt=0)
    currency: Optional[str] = None
    description: Optional[str] = None
    payment_method: Optional[PaymentMethod] = None
    is_recurring: Optional[bool] = None
    tags: Optional[str] = None


class PersonalExpenseOut(BaseModel):
    id: int
    date: date
    category: ExpenseCategory
    amount: float
    currency: str
    description: Optional[str]
    payment_method: PaymentMethod
    is_recurring: bool
    tags: Optional[str]
    created_at: datetime

    class Config:
        from_attributes = True


# ── Personal Income ───────────────────────────────────────────────────────────

class PersonalIncomeCreate(BaseModel):
    date: date
    source: IncomeSource = IncomeSource.OTHER
    amount: float = Field(..., gt=0)
    currency: str = "XAF"
    description: Optional[str] = None
    is_recurring: bool = False


class PersonalIncomeUpdate(BaseModel):
    date: Optional[date] = None
    source: Optional[IncomeSource] = None
    amount: Optional[float] = Field(None, gt=0)
    currency: Optional[str] = None
    description: Optional[str] = None
    is_recurring: Optional[bool] = None


class PersonalIncomeOut(BaseModel):
    id: int
    date: date
    source: IncomeSource
    amount: float
    currency: str
    description: Optional[str]
    is_recurring: bool
    created_at: datetime

    class Config:
        from_attributes = True


# ── Sport Activity ─────────────────────────────────────────────────────────────

class SportActivityCreate(BaseModel):
    date: date
    activity_type: str
    duration_minutes: int = Field(..., gt=0)
    calories_burned: Optional[int] = None
    distance_km: Optional[float] = None
    intensity: SportIntensity = SportIntensity.MEDIUM
    heart_rate_avg: Optional[int] = None
    notes: Optional[str] = None


class SportActivityUpdate(BaseModel):
    date: Optional[date] = None
    activity_type: Optional[str] = None
    duration_minutes: Optional[int] = Field(None, gt=0)
    calories_burned: Optional[int] = None
    distance_km: Optional[float] = None
    intensity: Optional[SportIntensity] = None
    heart_rate_avg: Optional[int] = None
    notes: Optional[str] = None


class SportActivityOut(BaseModel):
    id: int
    date: date
    activity_type: str
    duration_minutes: int
    calories_burned: Optional[int]
    distance_km: Optional[float]
    intensity: SportIntensity
    heart_rate_avg: Optional[int]
    notes: Optional[str]
    created_at: datetime

    class Config:
        from_attributes = True


# ── Meal ──────────────────────────────────────────────────────────────────────

class MealCreate(BaseModel):
    date: date
    meal_type: MealType
    description: str
    calories: Optional[int] = None
    proteins_g: Optional[float] = None
    carbs_g: Optional[float] = None
    fats_g: Optional[float] = None
    water_ml: Optional[int] = None
    notes: Optional[str] = None


class MealUpdate(BaseModel):
    date: Optional[date] = None
    meal_type: Optional[MealType] = None
    description: Optional[str] = None
    calories: Optional[int] = None
    proteins_g: Optional[float] = None
    carbs_g: Optional[float] = None
    fats_g: Optional[float] = None
    water_ml: Optional[int] = None
    notes: Optional[str] = None


class MealOut(BaseModel):
    id: int
    date: date
    meal_type: MealType
    description: str
    calories: Optional[int]
    proteins_g: Optional[float]
    carbs_g: Optional[float]
    fats_g: Optional[float]
    water_ml: Optional[int]
    notes: Optional[str]
    created_at: datetime

    class Config:
        from_attributes = True


# ── Personal Goal ─────────────────────────────────────────────────────────────

class PersonalGoalCreate(BaseModel):
    title: str
    goal_type: GoalType
    description: Optional[str] = None
    target_value: Optional[float] = None
    current_value: float = 0
    unit: Optional[str] = None
    start_date: date
    target_date: Optional[date] = None


class PersonalGoalUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    target_value: Optional[float] = None
    current_value: Optional[float] = None
    unit: Optional[str] = None
    target_date: Optional[date] = None
    status: Optional[GoalStatus] = None


class PersonalGoalOut(BaseModel):
    id: int
    title: str
    goal_type: GoalType
    description: Optional[str]
    target_value: Optional[float]
    current_value: Optional[float]
    unit: Optional[str]
    start_date: date
    target_date: Optional[date]
    status: GoalStatus
    created_at: datetime

    class Config:
        from_attributes = True


# ── Daily Summary ─────────────────────────────────────────────────────────────

class DailySummaryCreate(BaseModel):
    date: date
    mood: Optional[int] = Field(None, ge=1, le=5)
    energy_level: Optional[int] = Field(None, ge=1, le=5)
    sleep_hours: Optional[float] = None
    weight_kg: Optional[float] = None
    notes: Optional[str] = None


class DailySummaryUpdate(BaseModel):
    mood: Optional[int] = Field(None, ge=1, le=5)
    energy_level: Optional[int] = Field(None, ge=1, le=5)
    sleep_hours: Optional[float] = None
    weight_kg: Optional[float] = None
    notes: Optional[str] = None


class DailySummaryOut(BaseModel):
    id: int
    date: date
    mood: Optional[int]
    energy_level: Optional[int]
    sleep_hours: Optional[float]
    weight_kg: Optional[float]
    notes: Optional[str]
    created_at: datetime

    class Config:
        from_attributes = True


# ── Purchase Commitment ───────────────────────────────────────────────────────

class PurchaseCommitmentCreate(BaseModel):
    item_name:   str
    link:        Optional[str] = None
    price:       Optional[float] = None
    currency:    str = "XAF"
    person_name: str
    reason:      str
    due_date:    Optional[date] = None
    notes:       Optional[str] = None


class PurchaseCommitmentUpdate(BaseModel):
    item_name:        Optional[str] = None
    link:             Optional[str] = None
    price:            Optional[float] = None
    currency:         Optional[str] = None
    person_name:      Optional[str] = None
    reason:           Optional[str] = None
    status:           Optional[str] = None
    amount_received:  Optional[float] = None
    due_date:         Optional[date] = None
    notes:            Optional[str] = None


class PurchaseCommitmentOut(BaseModel):
    id:               int
    item_name:        str
    link:             Optional[str]
    price:            Optional[float]
    currency:         str
    person_name:      str
    reason:           str
    status:           str
    amount_received:  float
    due_date:         Optional[date]
    notes:            Optional[str]
    created_at:       datetime

    class Config:
        from_attributes = True


# ── Dashboard Stats ───────────────────────────────────────────────────────────

class PersonalDashboardStats(BaseModel):
    period_label: str
    total_expenses: float
    total_income: float
    balance: float
    sport_sessions: int
    total_sport_minutes: int
    total_calories_burned: int
    meals_logged: int
    avg_daily_calories: Optional[float]
    active_goals: int
    avg_sleep: Optional[float]
    avg_mood: Optional[float]
