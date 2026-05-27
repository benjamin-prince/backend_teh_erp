from sqlalchemy import Column, Integer, String, Float, Date, DateTime, Text, Enum, ForeignKey, Boolean
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import enum
from app.core.database import Base


class ExpenseCategory(str, enum.Enum):
    FOOD = "food"
    TRANSPORT = "transport"
    HEALTH = "health"
    ENTERTAINMENT = "entertainment"
    SHOPPING = "shopping"
    BILLS = "bills"
    EDUCATION = "education"
    SPORT = "sport"
    TRAVEL = "travel"
    OTHER = "other"


class IncomeSource(str, enum.Enum):
    SALARY = "salary"
    FREELANCE = "freelance"
    INVESTMENT = "investment"
    GIFT = "gift"
    BONUS = "bonus"
    RENTAL = "rental"
    OTHER = "other"


class SportIntensity(str, enum.Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    EXTREME = "extreme"


class MealType(str, enum.Enum):
    BREAKFAST = "breakfast"
    LUNCH = "lunch"
    DINNER = "dinner"
    SNACK = "snack"


class GoalType(str, enum.Enum):
    WEIGHT = "weight"
    SAVINGS = "savings"
    SPORT = "sport"
    NUTRITION = "nutrition"
    CUSTOM = "custom"


class GoalStatus(str, enum.Enum):
    ACTIVE = "active"
    COMPLETED = "completed"
    ABANDONED = "abandoned"


class PaymentMethod(str, enum.Enum):
    CASH = "cash"
    CARD = "card"
    MOBILE_MONEY = "mobile_money"
    TRANSFER = "transfer"
    OTHER = "other"


class PersonalExpense(Base):
    __tablename__ = "personal_expenses"

    id = Column(Integer, primary_key=True, index=True)
    date = Column(Date, nullable=False)
    category = Column(Enum(ExpenseCategory), nullable=False, default=ExpenseCategory.OTHER)
    amount = Column(Float, nullable=False)
    currency = Column(String(10), nullable=False, default="XAF")
    description = Column(String(255), nullable=True)
    payment_method = Column(Enum(PaymentMethod), default=PaymentMethod.CASH)
    is_recurring = Column(Boolean, default=False)
    tags = Column(String(500), nullable=True)  # comma-separated
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())


class PersonalIncome(Base):
    __tablename__ = "personal_income"

    id = Column(Integer, primary_key=True, index=True)
    date = Column(Date, nullable=False)
    source = Column(Enum(IncomeSource), nullable=False, default=IncomeSource.OTHER)
    amount = Column(Float, nullable=False)
    currency = Column(String(10), nullable=False, default="XAF")
    description = Column(String(255), nullable=True)
    is_recurring = Column(Boolean, default=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())


class SportActivity(Base):
    __tablename__ = "sport_activities"

    id = Column(Integer, primary_key=True, index=True)
    date = Column(Date, nullable=False)
    activity_type = Column(String(100), nullable=False)  # running, gym, football, etc.
    duration_minutes = Column(Integer, nullable=False)
    calories_burned = Column(Integer, nullable=True)
    distance_km = Column(Float, nullable=True)
    intensity = Column(Enum(SportIntensity), default=SportIntensity.MEDIUM)
    heart_rate_avg = Column(Integer, nullable=True)
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())


class Meal(Base):
    __tablename__ = "personal_meals"

    id = Column(Integer, primary_key=True, index=True)
    date = Column(Date, nullable=False)
    meal_type = Column(Enum(MealType), nullable=False)
    description = Column(String(500), nullable=False)  # foods eaten
    calories = Column(Integer, nullable=True)
    proteins_g = Column(Float, nullable=True)
    carbs_g = Column(Float, nullable=True)
    fats_g = Column(Float, nullable=True)
    water_ml = Column(Integer, nullable=True)
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class PersonalGoal(Base):
    __tablename__ = "personal_goals"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(200), nullable=False)
    goal_type = Column(Enum(GoalType), nullable=False)
    description = Column(Text, nullable=True)
    target_value = Column(Float, nullable=True)
    current_value = Column(Float, nullable=True, default=0)
    unit = Column(String(50), nullable=True)  # kg, FCFA, sessions, etc.
    start_date = Column(Date, nullable=False)
    target_date = Column(Date, nullable=True)
    status = Column(Enum(GoalStatus), default=GoalStatus.ACTIVE)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())


class PurchaseCommitmentStatus(str, enum.Enum):
    PENDING   = "pending"    # not yet bought
    BOUGHT    = "bought"     # purchased
    CANCELLED = "cancelled"  # decided not to buy


class PurchaseCommitment(Base):
    """Things I committed to buy for someone."""
    __tablename__ = "purchase_commitments"

    id          = Column(Integer, primary_key=True, index=True)
    item_name   = Column(String(255), nullable=False)
    link        = Column(String(1000), nullable=True)
    price          = Column(Float, nullable=True)         # what I pay to buy the item
    price_currency = Column(String(10), nullable=True, default="XAF")  # XAF / CNY / USD / EUR
    price_asked    = Column(Float, nullable=True)         # what the other party pays me back
    currency       = Column(String(10), nullable=False, default="XAF")  # selling currency: XAF / EUR
    person_name = Column(String(200), nullable=False)
    reason      = Column(String(500), nullable=False)  # gift, will pay back, promise…
    status           = Column(String(20), nullable=False, default=PurchaseCommitmentStatus.PENDING)
    priority         = Column(Integer, nullable=False, default=3)  # 1=green … 5=red; gift always 1
    amount_received  = Column(Float, nullable=False, default=0)
    due_date         = Column(Date, nullable=True)
    notes            = Column(Text, nullable=True)
    purchase_location = Column(String(20), nullable=True)   # "online" | "physical"
    can_repurchase    = Column(Boolean, nullable=True)       # can buy again at same price?
    created_at       = Column(DateTime(timezone=True), server_default=func.now())
    updated_at       = Column(DateTime(timezone=True), onupdate=func.now())


class PersonalDebt(Base):
    """Money I owe to someone."""
    __tablename__ = "personal_debts"

    id            = Column(Integer, primary_key=True, index=True)
    creditor      = Column(String(200), nullable=False)          # who I owe money to
    amount        = Column(Float, nullable=False)                # original amount borrowed
    currency      = Column(String(10), nullable=False, default="XAF")
    reason        = Column(String(500), nullable=True)           # why I borrowed
    borrowed_date = Column(Date, nullable=False)
    due_date      = Column(Date, nullable=True)                  # deadline to repay
    is_paid       = Column(Boolean, nullable=False, default=False)
    paid_date     = Column(Date, nullable=True)
    notes         = Column(Text, nullable=True)
    created_at    = Column(DateTime(timezone=True), server_default=func.now())
    updated_at    = Column(DateTime(timezone=True), onupdate=func.now())


class DailySummary(Base):
    """Auto-computed or manually enriched daily note"""
    __tablename__ = "personal_daily_summary"

    id = Column(Integer, primary_key=True, index=True)
    date = Column(Date, nullable=False, unique=True)
    mood = Column(Integer, nullable=True)  # 1-5
    energy_level = Column(Integer, nullable=True)  # 1-5
    sleep_hours = Column(Float, nullable=True)
    weight_kg = Column(Float, nullable=True)
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
