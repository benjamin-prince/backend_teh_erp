"""TEHTEK — Customers Controller. Rules: CR-001 to CR-005."""
from datetime import datetime
from typing import Optional

from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.modules.companies.controller import next_sequence
from app.modules.customers.models import (
    Customer, CustomerContact, CustomerKYC, CustomerNote, Supplier, SupplierContact
)
from app.core.enums import CustomerStatus, CustomerRiskLevel, KYCStatus, SequenceType


def validate_for_transaction(customer: Customer) -> dict:
    """CR-001, CR-002, CR-003: called before any transaction."""
    if customer.status == CustomerStatus.blacklisted:
        raise HTTPException(403, f"Customer {customer.customer_code} is blacklisted")
    warnings = []
    if float(customer.outstanding_balance or 0) > 0:
        warnings.append(f"Outstanding balance: {customer.outstanding_balance} XAF")
    return {"valid": True, "warnings": warnings}


def create_customer(db: Session, data: dict, actor_id: int) -> Customer:
    code = next_sequence(db, SequenceType.customer_code)
    customer = Customer(**data, customer_code=code, created_by=actor_id)
    db.add(customer)
    db.commit()
    db.refresh(customer)
    return customer


def list_customers(db: Session, company_id: int, skip: int = 0, limit: int = 50):
    return (
        db.query(Customer)
        .filter(Customer.company_id == company_id, Customer.deleted_at.is_(None))
        .offset(skip).limit(limit).all()
    )


def get_customer(db: Session, customer_id: int) -> Optional[Customer]:
    return db.query(Customer).filter(
        Customer.id == customer_id, Customer.deleted_at.is_(None)
    ).first()


def get_by_code(db: Session, code: str) -> Optional[Customer]:
    return db.query(Customer).filter(
        Customer.customer_code == code, Customer.deleted_at.is_(None)
    ).first()


def update_customer(db: Session, customer: Customer, data: dict) -> Customer:
    for k, v in data.items():
        setattr(customer, k, v)
    customer.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(customer)
    return customer


def blacklist_customer(db: Session, customer: Customer, reason: str, actor_id: int) -> Customer:
    customer.status = CustomerStatus.blacklisted
    customer.risk_level = CustomerRiskLevel.blacklisted
    customer.blacklisted_by = actor_id
    customer.blacklist_reason = reason
    customer.blacklisted_at = datetime.utcnow()
    db.commit()
    return customer


def remove_blacklist(db: Session, customer: Customer, actor_id: int) -> Customer:
    customer.status = CustomerStatus.active
    customer.risk_level = CustomerRiskLevel.medium
    customer.blacklisted_by = None
    customer.blacklist_reason = None
    customer.blacklisted_at = None
    db.commit()
    return customer


def grant_vip(db: Session, customer: Customer, actor_id: int) -> Customer:
    customer.is_vip = True
    customer.vip_granted_by = actor_id
    customer.vip_granted_at = datetime.utcnow()
    db.commit()
    return customer


def revoke_vip(db: Session, customer: Customer) -> Customer:
    customer.is_vip = False
    customer.vip_granted_by = None
    customer.vip_granted_at = None
    db.commit()
    return customer


def soft_delete_customer(db: Session, customer: Customer) -> None:
    customer.deleted_at = datetime.utcnow()
    db.commit()


# ── KYC ──────────────────────────────────────────────────────────────────────

def submit_kyc(db: Session, customer_id: int, data: dict) -> CustomerKYC:
    kyc = CustomerKYC(customer_id=customer_id, **data)
    db.add(kyc)
    db.commit()
    db.refresh(kyc)
    return kyc


def review_kyc(db: Session, kyc: CustomerKYC, decision: str, reviewer_id: int, note: str = None) -> CustomerKYC:
    kyc.status = decision
    kyc.reviewed_by = reviewer_id
    kyc.review_note = note
    kyc.reviewed_at = datetime.utcnow()
    db.commit()
    return kyc


# ── Contacts & Notes ─────────────────────────────────────────────────────────

def add_contact(db: Session, customer_id: int, data: dict) -> CustomerContact:
    c = CustomerContact(customer_id=customer_id, **data)
    db.add(c)
    db.commit()
    db.refresh(c)
    return c


def add_note(db: Session, customer_id: int, content: str, actor_id: int) -> CustomerNote:
    note = CustomerNote(customer_id=customer_id, content=content, created_by=actor_id)
    db.add(note)
    db.commit()
    db.refresh(note)
    return note


# ── Suppliers ─────────────────────────────────────────────────────────────────

def create_supplier(db: Session, data: dict, actor_id: int) -> Supplier:
    s = Supplier(**data, created_by=actor_id)
    db.add(s)
    db.commit()
    db.refresh(s)
    return s


def list_suppliers(db: Session, company_id: int):
    return db.query(Supplier).filter(
        Supplier.company_id == company_id, Supplier.deleted_at.is_(None)
    ).all()


def get_supplier(db: Session, supplier_id: int) -> Optional[Supplier]:
    return db.query(Supplier).filter(
        Supplier.id == supplier_id, Supplier.deleted_at.is_(None)
    ).first()
