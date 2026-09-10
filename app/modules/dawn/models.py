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
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class DawnSet(Base):
    """One logged set. Append-only: the history is the progression."""
    __tablename__ = "dawn_sets"

    id         = Column(Integer, primary_key=True)
    user_id    = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    lift_id    = Column(String(40), nullable=False, index=True)
    lift_name  = Column(String(120), nullable=True)
    day        = Column(String(10), nullable=False)
    weight     = Column(Numeric(8, 2), nullable=False)
    reps       = Column(Integer, nullable=False)
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
