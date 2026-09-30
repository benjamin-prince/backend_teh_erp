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
    # The shape of the day: 03:30 to 21:00 in 30-minute blocks.
    day_start    = Column(String(5), nullable=False, default="03:30")
    day_end      = Column(String(5), nullable=False, default="21:00")
    slot_minutes = Column(Integer, nullable=False, default=30)
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


class DawnTask(Base):
    """One thing to do, with a kind and a deadline.

    Deliberately separate from Reminder: that one is company-scoped and pushes
    to customers over WhatsApp. This is personal — buy, call, do, ads, admin —
    and belongs to the user, like everything else in this module.
    """
    __tablename__ = "dawn_tasks"

    id         = Column(Integer, primary_key=True)
    user_id    = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    title      = Column(String(300), nullable=False)
    # buy | pay | call | do | ads | admin | health | collect
    kind       = Column(String(20), nullable=False, default="do")
    due_date   = Column(String(10), nullable=True, index=True)   # YYYY-MM-DD
    # Which 30-minute block of the day this sits in, HH:MM. NULL = unscheduled.
    slot       = Column(String(5), nullable=True)
    slots      = Column(Integer, nullable=False, default=1)      # blocks it occupies
    # none | daily | weekly — a repeating task reappears once ticked.
    repeat     = Column(String(10), nullable=False, default="none")
    priority   = Column(Integer, nullable=False, default=1)       # 0 high, 1 normal, 2 low
    notes      = Column(Text, nullable=True)
    done_at    = Column(DateTime, nullable=True)
    last_done  = Column(String(10), nullable=True)   # for repeating tasks
    # 1 when the task was added on the day it was due, after that day was
    # locked. Kept so the habit of improvising is measurable.
    unplanned  = Column(Integer, nullable=False, default=0)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)


class DawnDayPlan(Base):
    """A day that was planned in advance, and locked.

    The point of locking is behavioural: once tomorrow is planned, anything
    added *during* that day is visible as unplanned instead of quietly slipping
    into the list. Nothing is forbidden — it is counted.
    """
    __tablename__ = "dawn_day_plans"
    __table_args__ = (UniqueConstraint("user_id", "day", name="uq_dawn_day_plan_user"),)

    id         = Column(Integer, primary_key=True)
    user_id    = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    day        = Column(String(10), nullable=False)   # the day being planned
    locked_at  = Column(DateTime, nullable=True)      # set when the plan is closed
    intention  = Column(Text, nullable=True)          # the one thing that matters tomorrow
    review     = Column(Text, nullable=True)          # written at the end of the day
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class DawnTracker(Base):
    """Anything worth counting once a day.

    Money in, money saved, litres of water, vitamins taken, ads posted, sex,
    prayer, screen time — the app should not need a new table for each one. A
    tracker is a name, a unit, a shape and a daily target; the numbers live in
    DawnLog. `private` keeps a tracker out of shared views and summaries.
    """
    __tablename__ = "dawn_trackers"

    id        = Column(Integer, primary_key=True)
    user_id   = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    name      = Column(String(80), nullable=False)
    # amount (money) | count | minutes | yesno | scale (1-5) | note
    shape     = Column(String(10), nullable=False, default="count")
    unit      = Column(String(20), nullable=True)      # USD, XAF, L, g, reps…
    target    = Column(Numeric(12, 2), nullable=True)  # the daily minimum
    # floor  → hitting target or more is a win (income, water, protein)
    # ceiling → staying at or under target is a win (screen time, spending)
    direction = Column(String(8), nullable=False, default="floor")
    group     = Column(String(20), nullable=False, default="life")  # money | body | work | life
    private   = Column(Integer, nullable=False, default=0)   # 1 = hide from summaries
    archived  = Column(Integer, nullable=False, default=0)
    position  = Column(Integer, nullable=False, default=0)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)


class DawnLog(Base):
    """One day's value for one tracker. Last write wins."""
    __tablename__ = "dawn_logs"
    __table_args__ = (UniqueConstraint("user_id", "tracker_id", "day", name="uq_dawn_log_day"),)

    id         = Column(Integer, primary_key=True)
    user_id    = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    tracker_id = Column(Integer, ForeignKey("dawn_trackers.id"), nullable=False, index=True)
    day        = Column(String(10), nullable=False, index=True)
    # What actually happened…
    value      = Column(Numeric(12, 2), nullable=True)   # amount/count/minutes/scale, 1|0 for yesno
    # …and what was planned for it the evening before. Money is planned, not
    # discovered at the end of the day.
    planned    = Column(Numeric(12, 2), nullable=True)
    note       = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class DawnAccount(Base):
    """A bank account with a number to reach.

    The three that matter: 1 000 000 000 XAF in the Cameroon business account,
    1 000 000 USD in the United Bank business account, 100 000 CAD personal in
    Canada. "How" is arithmetic once the target, the balance and a deadline are
    all written down — see the /accounts endpoint.
    """
    __tablename__ = "dawn_accounts"

    id        = Column(Integer, primary_key=True)
    user_id   = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    name      = Column(String(120), nullable=False)
    bank      = Column(String(120), nullable=True)
    country   = Column(String(60), nullable=True)
    currency  = Column(String(6), nullable=False, default="USD")
    target    = Column(Numeric(20, 2), nullable=False)
    balance   = Column(Numeric(20, 2), nullable=False, default=0)
    deadline  = Column(String(10), nullable=True)   # YYYY-MM-DD, optional
    kind      = Column(String(12), nullable=False, default="business")
    position  = Column(Integer, nullable=False, default=0)
    archived  = Column(Integer, nullable=False, default=0)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class DawnBalance(Base):
    """A balance reading, so progress is history rather than a single number."""
    __tablename__ = "dawn_balances"
    __table_args__ = (UniqueConstraint("user_id", "account_id", "day",
                                      name="uq_dawn_balance_day"),)

    id         = Column(Integer, primary_key=True)
    user_id    = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    account_id = Column(Integer, ForeignKey("dawn_accounts.id"), nullable=False, index=True)
    day        = Column(String(10), nullable=False)
    amount     = Column(Numeric(20, 2), nullable=False)
    note       = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
