"""
Dream Tracker ("North Star") — Brian Tracy goal-setting method.

DreamState  : singleton (id=1) — major definite purpose, today's frog + ABCDE,
              daily-action streak.
Dream       : one goal (the 10-goal exercise) with life area, deadline, progress,
              and the Tracy detail fields (why / obstacles / skills / people).
DreamStep   : action-plan steps under a Dream; completing them drives progress.
"""
from datetime import datetime

from sqlalchemy import (
    Boolean, Column, Date, DateTime, ForeignKey, Integer, String, Text,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import relationship

from app.core.database import Base


class DreamState(Base):
    __tablename__ = "dream_state"

    id           = Column(Integer, primary_key=True, default=1)
    mdp          = Column(Text, nullable=True)          # major definite purpose (present tense)
    mdp_date     = Column(Date, nullable=True)          # its deadline
    frog         = Column(Text, nullable=True)          # today's #1 task
    frog_date    = Column(Date, nullable=True)
    abcde        = Column(JSONB, nullable=False, server_default="[]")  # [{g,t,done}]
    streak       = Column(Integer, nullable=False, default=0)
    last_commit  = Column(Date, nullable=True)          # last day an action was logged
    last_rewrite = Column(Date, nullable=True)          # last morning the MDP was rewritten
    # Napoleon Hill — Think and Grow Rich
    give_in_return = Column(Text, nullable=True)        # what you intend to give in return (step 2)
    read_morning   = Column(Date, nullable=True)        # last morning the statement was read aloud
    read_evening   = Column(Date, nullable=True)        # last evening the statement was read aloud
    vision         = Column(Text, nullable=True)        # the life you are building (imagination)
    mastermind     = Column(JSONB, nullable=False, server_default="[]")  # [{name, role}]
    updated_at   = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class DreamHabit(Base):
    """Daily keystone disciplines that compound into success (Tracy)."""
    __tablename__ = "dream_habits"

    id         = Column(Integer, primary_key=True)
    name       = Column(Text, nullable=False, server_default="")
    position   = Column(Integer, nullable=False, server_default="0")
    streak     = Column(Integer, nullable=False, default=0)
    last_done  = Column(Date, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)


class DreamJournal(Base):
    """Evening review — one entry per day."""
    __tablename__ = "dream_journal"

    id            = Column(Integer, primary_key=True)
    entry_date    = Column(Date, unique=True, nullable=False)
    wins          = Column(Text, nullable=True)         # 3 victories today
    lesson        = Column(Text, nullable=True)         # what I learned
    gratitude     = Column(Text, nullable=True)         # what I'm grateful for
    tomorrow_frog = Column(Text, nullable=True)         # tomorrow's #1 task (plan the day in advance)
    created_at    = Column(DateTime, default=datetime.utcnow, nullable=False)


class Dream(Base):
    __tablename__ = "dreams"

    id                = Column(Integer, primary_key=True)
    title             = Column(Text, nullable=False, server_default="")
    life_area         = Column(String(30), nullable=False, server_default="business")
    is_major_purpose  = Column(Boolean, nullable=False, server_default="false")
    target_date       = Column(Date, nullable=True)
    progress          = Column(Integer, nullable=False, server_default="0")
    status            = Column(String(20), nullable=False, server_default="active")  # active|completed|abandoned
    why               = Column(Text, nullable=True)
    obstacles         = Column(Text, nullable=True)
    skills            = Column(Text, nullable=True)
    people            = Column(Text, nullable=True)
    position          = Column(Integer, nullable=False, server_default="0")
    created_at        = Column(DateTime, default=datetime.utcnow, nullable=False)

    steps = relationship("DreamStep", back_populates="dream", cascade="all, delete-orphan",
                         order_by="DreamStep.position")


class DreamStep(Base):
    __tablename__ = "dream_steps"

    id        = Column(Integer, primary_key=True)
    dream_id  = Column(Integer, ForeignKey("dreams.id", ondelete="CASCADE"), nullable=False)
    text      = Column(Text, nullable=False, server_default="")
    done      = Column(Boolean, nullable=False, server_default="false")
    position  = Column(Integer, nullable=False, server_default="0")

    dream = relationship("Dream", back_populates="steps")
