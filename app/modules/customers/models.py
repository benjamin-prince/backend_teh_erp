"""TEHTEK — Customers Module Models. Rules: CR-001 to CR-005."""
from datetime import datetime
from sqlalchemy import (
    Boolean, Column, DateTime, ForeignKey, Integer,
    Numeric, String, Text, Index
)
from sqlalchemy.orm import relationship
from app.core.database import Base
from app.core.enums import (
    CustomerType, CustomerRiskLevel, CustomerStatus, KYCStatus, KYCLevel
)


class Customer(Base):
    __tablename__ = "customers"

    id               = Column(Integer, primary_key=True)
    company_id       = Column(Integer, ForeignKey("companies.id"), nullable=False)
    customer_code    = Column(String(20), unique=True, nullable=False)  # CUS-000001
    user_id          = Column(Integer, ForeignKey("users.id"), nullable=True)  # nullable — portal login

    first_name       = Column(String(100), nullable=False)
    last_name        = Column(String(100), nullable=False)
    company_name     = Column(String(200), nullable=True)
    email            = Column(String(255), nullable=True)
    phone            = Column(String(30), nullable=True)
    whatsapp         = Column(String(30), nullable=True)
    address          = Column(Text, nullable=True)
    city             = Column(String(100), nullable=True)
    country          = Column(String(100), default="Cameroon")

    customer_type    = Column(String(30), nullable=False, default=CustomerType.retail)
    status           = Column(String(30), nullable=False, default=CustomerStatus.active)
    risk_level       = Column(String(30), nullable=False, default=CustomerRiskLevel.low)

    kyc_status       = Column(String(30), nullable=False, default=KYCStatus.not_submitted)
    kyc_level        = Column(String(30), nullable=False, default=KYCLevel.basic)

    # VIP (CR-005)
    is_vip           = Column(Boolean, default=False)
    vip_granted_by   = Column(Integer, nullable=True)
    vip_granted_at   = Column(DateTime, nullable=True)

    # Blacklist (CR-001)
    blacklisted_by   = Column(Integer, nullable=True)
    blacklist_reason = Column(Text, nullable=True)
    blacklisted_at   = Column(DateTime, nullable=True)

    # Financial
    credit_balance      = Column(Numeric(14, 2), default=0)
    outstanding_balance = Column(Numeric(14, 2), default=0)

    notes       = Column(Text, nullable=True)
    created_by  = Column(Integer, nullable=True)
    created_at  = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at  = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    deleted_at  = Column(DateTime, nullable=True)

    kyc_docs = relationship("CustomerKYC", back_populates="customer", lazy="select")
    contacts = relationship("CustomerContact", back_populates="customer", lazy="select")
    customer_notes = relationship("CustomerNote", back_populates="customer", lazy="select")

    __table_args__ = (
        Index("ix_customer_company_id", "company_id"),
        Index("ix_customer_status", "status"),
        Index("ix_customer_code", "customer_code"),
    )

    @property
    def full_name(self) -> str:
        return f"{self.first_name} {self.last_name}"


class CustomerKYC(Base):
    __tablename__ = "customer_kyc"

    id             = Column(Integer, primary_key=True)
    customer_id    = Column(Integer, ForeignKey("customers.id"), nullable=False)
    document_type  = Column(String(50), nullable=False)  # national_id, passport, etc.
    document_number = Column(String(100), nullable=True)
    document_url   = Column(String(500), nullable=False)
    status         = Column(String(30), default=KYCStatus.pending)
    reviewed_by    = Column(Integer, nullable=True)
    review_note    = Column(Text, nullable=True)
    expires_at     = Column(DateTime, nullable=True)
    submitted_at   = Column(DateTime, default=datetime.utcnow)
    reviewed_at    = Column(DateTime, nullable=True)

    customer = relationship("Customer", back_populates="kyc_docs")


class CustomerContact(Base):
    __tablename__ = "customer_contacts"

    id          = Column(Integer, primary_key=True)
    customer_id = Column(Integer, ForeignKey("customers.id"), nullable=False)
    name        = Column(String(200), nullable=False)
    role        = Column(String(100), nullable=True)
    phone       = Column(String(30), nullable=True)
    email       = Column(String(255), nullable=True)
    is_primary  = Column(Boolean, default=False)
    created_at  = Column(DateTime, default=datetime.utcnow)

    customer = relationship("Customer", back_populates="contacts")


class CustomerNote(Base):
    __tablename__ = "customer_notes"

    id          = Column(Integer, primary_key=True)
    customer_id = Column(Integer, ForeignKey("customers.id"), nullable=False)
    content     = Column(Text, nullable=False)
    created_by  = Column(Integer, nullable=False)
    created_at  = Column(DateTime, default=datetime.utcnow)

    customer = relationship("Customer", back_populates="customer_notes")


class Supplier(Base):
    __tablename__ = "suppliers"

    id           = Column(Integer, primary_key=True)
    company_id   = Column(Integer, ForeignKey("companies.id"), nullable=False)
    name         = Column(String(200), nullable=False)
    code         = Column(String(30), nullable=True)
    email        = Column(String(255), nullable=True)
    phone        = Column(String(30), nullable=True)
    address      = Column(Text, nullable=True)
    city         = Column(String(100), nullable=True)
    country      = Column(String(100), nullable=True)
    currency     = Column(String(10), default="XAF")
    payment_terms = Column(Integer, default=30)  # days
    notes        = Column(Text, nullable=True)
    is_active    = Column(Boolean, default=True)
    created_by   = Column(Integer, nullable=True)
    created_at   = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at   = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    deleted_at   = Column(DateTime, nullable=True)

    contacts = relationship("SupplierContact", back_populates="supplier", lazy="select")


class SupplierContact(Base):
    __tablename__ = "supplier_contacts"

    id          = Column(Integer, primary_key=True)
    supplier_id = Column(Integer, ForeignKey("suppliers.id"), nullable=False)
    name        = Column(String(200), nullable=False)
    role        = Column(String(100), nullable=True)
    phone       = Column(String(30), nullable=True)
    email       = Column(String(255), nullable=True)
    is_primary  = Column(Boolean, default=False)
    created_at  = Column(DateTime, default=datetime.utcnow)

    supplier = relationship("Supplier", back_populates="contacts")
