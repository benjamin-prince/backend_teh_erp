"""TEHTEK — Companies Module Models"""
from datetime import datetime
from sqlalchemy import (
    Boolean, Column, DateTime, ForeignKey, Integer,
    Numeric, String, Text, UniqueConstraint, Index
)
from sqlalchemy.orm import relationship
from app.core.database import Base
from app.core.enums import (
    CompanyType, BranchType, DepartmentType,
    ApprovalStatus, ApprovalType, SequenceType
)


class SequenceRegistry(Base):
    """
    SEQ-001: Atomic number generation. SELECT FOR UPDATE — no app-level generation.
    Seeded FIRST on every startup before any other seed.
    """
    __tablename__ = "sequence_registry"

    id           = Column(Integer, primary_key=True)
    sequence_type = Column(String(50), unique=True, nullable=False)
    prefix       = Column(String(20), nullable=False)
    current_value = Column(Integer, default=0, nullable=False)
    pad_length   = Column(Integer, default=6, nullable=False)
    year_scoped  = Column(Boolean, default=True)   # resets each Jan 1
    month_scoped = Column(Boolean, default=False)
    route_scoped = Column(Boolean, default=False)  # tracking numbers only
    created_at   = Column(DateTime, default=datetime.utcnow)
    updated_at   = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class Company(Base):
    __tablename__ = "companies"

    id          = Column(Integer, primary_key=True)
    name        = Column(String(200), nullable=False)
    code        = Column(String(20), unique=True, nullable=False)
    company_type = Column(String(30), nullable=False, default=CompanyType.subsidiary)
    parent_id   = Column(Integer, ForeignKey("companies.id"), nullable=True)
    country     = Column(String(100), default="Cameroon")
    currency    = Column(String(10), default="XAF")
    is_active   = Column(Boolean, default=True, nullable=False)
    created_by  = Column(Integer, nullable=True)
    created_at  = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at  = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    deleted_at  = Column(DateTime, nullable=True)

    branches    = relationship("Branch", back_populates="company", lazy="select")
    departments = relationship("Department", back_populates="company", lazy="select")


class Branch(Base):
    __tablename__ = "branches"

    id          = Column(Integer, primary_key=True)
    company_id  = Column(Integer, ForeignKey("companies.id"), nullable=False)
    name        = Column(String(200), nullable=False)
    code        = Column(String(20), nullable=False)
    branch_type = Column(String(30), nullable=False, default=BranchType.headquarters)
    address     = Column(Text, nullable=True)
    city        = Column(String(100), nullable=True)
    country     = Column(String(100), default="Cameroon")
    phone       = Column(String(30), nullable=True)
    email       = Column(String(255), nullable=True)
    is_active   = Column(Boolean, default=True, nullable=False)
    created_by  = Column(Integer, nullable=True)
    created_at  = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at  = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    deleted_at  = Column(DateTime, nullable=True)

    __table_args__ = (
        UniqueConstraint("company_id", "code", name="uq_branch_code_per_company"),
    )

    company = relationship("Company", back_populates="branches")


class Department(Base):
    __tablename__ = "departments"

    id              = Column(Integer, primary_key=True)
    company_id      = Column(Integer, ForeignKey("companies.id"), nullable=False)
    name            = Column(String(200), nullable=False)
    department_type = Column(String(50), nullable=False, default=DepartmentType.operations)
    manager_id      = Column(Integer, nullable=True)
    created_at      = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at      = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    deleted_at      = Column(DateTime, nullable=True)

    company = relationship("Company", back_populates="departments")
    teams   = relationship("Team", back_populates="department", lazy="select")


class Team(Base):
    __tablename__ = "teams"

    id            = Column(Integer, primary_key=True)
    department_id = Column(Integer, ForeignKey("departments.id"), nullable=False)
    name          = Column(String(200), nullable=False)
    lead_id       = Column(Integer, nullable=True)
    created_at    = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at    = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    deleted_at    = Column(DateTime, nullable=True)

    department = relationship("Department", back_populates="teams")


class PermissionFlag(Base):
    """
    Per-user granular overrides. Can ADD or RESTRICT beyond role permissions.
    Reference: TEHTEK_ACCESS_MATRIX.md — Individual Permission Flags.
    """
    __tablename__ = "permission_flags"

    id             = Column(Integer, primary_key=True)
    user_id        = Column(Integer, nullable=False)   # FK added after users module
    company_id     = Column(Integer, ForeignKey("companies.id"), nullable=False)
    permission_key = Column(String(100), nullable=False)
    granted        = Column(Boolean, default=True, nullable=False)  # False = restrict
    granted_by     = Column(Integer, nullable=True)
    reason         = Column(Text, nullable=True)
    expires_at     = Column(DateTime, nullable=True)
    created_at     = Column(DateTime, default=datetime.utcnow, nullable=False)

    __table_args__ = (
        UniqueConstraint("user_id", "permission_key", name="uq_flag_per_user"),
    )


class ApprovalWorkflow(Base):
    """Multi-step approval engine. Used by all override/exception processes."""
    __tablename__ = "approval_workflows"

    id              = Column(Integer, primary_key=True)
    company_id      = Column(Integer, ForeignKey("companies.id"), nullable=False)
    approval_type   = Column(String(50), nullable=False)
    status          = Column(String(30), default=ApprovalStatus.pending, nullable=False)
    requested_by    = Column(Integer, nullable=False)
    approved_by     = Column(Integer, nullable=True)
    reason          = Column(Text, nullable=False)
    decision_reason = Column(Text, nullable=True)
    # Polymorphic reference — links to the thing being approved
    ref_model       = Column(String(50), nullable=True)   # e.g. "shipment"
    ref_id          = Column(Integer, nullable=True)
    amount          = Column(Numeric(14, 2), nullable=True)
    expires_at      = Column(DateTime, nullable=True)
    created_at      = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at      = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    __table_args__ = (
        Index("ix_approval_company_status", "company_id", "status"),
    )
