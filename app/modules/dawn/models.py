"""TEHTEK — Dawn Block: the 3am morning routine, training log and product board.

Personal to each user, so every row carries user_id and every query filters on
it. Tables are created by create_all, like the rest of the recent modules.
"""
from datetime import datetime

from sqlalchemy import Column, DateTime, ForeignKey, Integer, Numeric, String, Text, UniqueConstraint

from app.core.database import Base


class DawnDay(Base):
    """Which morning blocks were ticked on a given day."""
    __tablename__ = "dawn_days"
    __table_args__ = (UniqueConstraint("user_id", "day", name="uq_dawn_day_user"),)

    id         = Column(Integer, primary_key=True)
    user_id    = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    day        = Column(String(10), nullable=False)          # YYYY-MM-DD
    blocks     = Column(Text, nullable=False, default="[]")  # JSON list of block ids
    wake_time  = Column(String(5),  nullable=True)   # HH:MM actually out of bed
    drink      = Column(String(20), nullable=True)   # water | tea | coffee | none
    read_note  = Column(Text,       nullable=True)   # what was read, if anything
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class DawnSet(Base):
    """One logged set. Append-only: the history is the progression."""
    __tablename__ = "dawn_sets"

    id         = Column(Integer, primary_key=True)
    user_id    = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    lift_id    = Column(String(40), nullable=False, index=True)
    lift_name  = Column(String(120), nullable=True)
    day        = Column(String(10), nullable=False)
    # A set is either weight x reps, or a duration. Cardio, planks and
    # stretching have no weight to record; asking for one is the bug.
    weight     = Column(Numeric(8, 2), nullable=True)
    reps       = Column(Integer, nullable=True)
    minutes    = Column(Integer, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)


class DawnCandidate(Base):
    """A product idea on the research board."""
    __tablename__ = "dawn_candidates"

    id         = Column(Integer, primary_key=True)
    user_id    = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    name       = Column(String(200), nullable=False)
    category   = Column(String(60), nullable=False, default="Other")
    stage      = Column(Integer, nullable=False, default=0)   # index into STAGES
    notes      = Column(Text, nullable=True)
    killed_at  = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class DawnResearch(Base):
    """What the research hour actually produced, one entry per session."""
    __tablename__ = "dawn_research"

    id           = Column(Integer, primary_key=True)
    user_id      = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    day          = Column(String(10), nullable=False, index=True)
    focus        = Column(String(60), nullable=True)   # Demand scan, Sourcing, …
    candidate_id = Column(Integer, ForeignKey("dawn_candidates.id"), nullable=True)
    minutes      = Column(Integer, nullable=True)
    findings     = Column(Text, nullable=True)
    created_at   = Column(DateTime, default=datetime.utcnow, nullable=False)


class DawnProfile(Base):
    """Bodyweight and the targets that follow from it."""
    __tablename__ = "dawn_profile"

    user_id       = Column(Integer, ForeignKey("users.id"), primary_key=True)
    bodyweight_kg = Column(Numeric(6, 2), nullable=False, default=90)
    goal_kg       = Column(Numeric(6, 2), nullable=False, default=100)
    # Left NULL to follow bodyweight; set to pin your own numbers.
    protein_target_g = Column(Integer, nullable=True)
    kcal_target      = Column(Integer, nullable=True)
    updated_at    = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class DawnPlanItem(Base):
    """One exercise of the training plan, editable per weekday."""
    __tablename__ = "dawn_plan_items"

    id       = Column(Integer, primary_key=True)
    user_id  = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    dow      = Column(Integer, nullable=False)          # 0 Sunday … 6 Saturday
    position = Column(Integer, nullable=False, default=0)
    lift_id  = Column(String(40), nullable=False)
    name     = Column(String(120), nullable=False)
    scheme   = Column(String(40), nullable=True)        # "4 × 6–8"
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)


class DawnMeal(Base):
    """What was actually eaten, so the intake target is measurable."""
    __tablename__ = "dawn_meals"

    id         = Column(Integer, primary_key=True)
    user_id    = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    day        = Column(String(10), nullable=False, index=True)
    slot       = Column(String(20), nullable=False)     # fuel | breakfast | lunch | dinner | snack
    text       = Column(Text, nullable=False)
    kcal       = Column(Integer, nullable=True)
    protein_g  = Column(Integer, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)


class DawnWeight(Base):
    """Morning bodyweight. One reading per day — the last one wins."""
    __tablename__ = "dawn_weights"
    __table_args__ = (UniqueConstraint("user_id", "day", name="uq_dawn_weight_user"),)

    id         = Column(Integer, primary_key=True)
    user_id    = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    day        = Column(String(10), nullable=False)
    kg         = Column(Numeric(6, 2), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
