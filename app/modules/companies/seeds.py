"""
TEHTEK — Companies Seeds
sequence_registry is seeded FIRST on every startup (SEQ-001).
Idempotent — safe to run on every restart.
"""
from sqlalchemy.orm import Session
from app.modules.companies.models import SequenceRegistry, Company, Branch
from app.core.enums import CompanyType, BranchType, SequenceType


SEQUENCES = [
    # (type, prefix, pad_length, year_scoped, month_scoped, route_scoped)
    (SequenceType.tracking_number,   "TRK",  6, True,  False, True),
    (SequenceType.invoice_number,    "INV",  6, True,  True,  False),
    (SequenceType.customer_code,     "CUS",  6, False, False, False),
    (SequenceType.order_number,      "ORD",  6, True,  False, False),
    (SequenceType.receipt_number,    "RCP",  6, True,  True,  False),
    (SequenceType.pickup_number,     "PKP",  6, True,  False, False),
    (SequenceType.bag_number,        "BAG",  4, True,  False, False),
    (SequenceType.service_ticket,    "SVC",  6, True,  False, False),
    (SequenceType.project_number,    "PRJ",  6, True,  False, False),
    (SequenceType.contract_number,   "CNT",  6, True,  False, False),
    (SequenceType.commission_record, "COM",  6, True,  False, False),
    (SequenceType.payout_number,     "PAY",  6, True,  True,  False),
]


def seed_sequences(db: Session) -> None:
    """Seed sequence_registry rows. Skips already-existing types."""
    for seq_type, prefix, pad_length, year_scoped, month_scoped, route_scoped in SEQUENCES:
        exists = db.query(SequenceRegistry).filter_by(sequence_type=seq_type).first()
        if not exists:
            db.add(SequenceRegistry(
                sequence_type=seq_type,
                prefix=prefix,
                pad_length=pad_length,
                year_scoped=year_scoped,
                month_scoped=month_scoped,
                route_scoped=route_scoped,
                current_value=0,
            ))
    db.commit()


def seed_parent_company(db: Session) -> Company:
    """Seed the TEHTEK parent company if it doesn't exist."""
    company = db.query(Company).filter_by(code="TEHTEK").first()
    if not company:
        company = Company(
            name="TEHTEK IT Services",
            code="TEHTEK",
            company_type=CompanyType.parent,
            country="Cameroon",
            currency="XAF",
        )
        db.add(company)
        db.flush()

        hq = Branch(
            company_id=company.id,
            name="Yaoundé HQ",
            code="YDE-HQ",
            branch_type=BranchType.headquarters,
            city="Yaoundé",
            country="Cameroon",
        )
        douala = Branch(
            company_id=company.id,
            name="Douala Cargo Hub",
            code="DLA-HUB",
            branch_type=BranchType.cargo_hub,
            city="Douala",
            country="Cameroon",
        )
        db.add_all([hq, douala])
        db.commit()
        db.refresh(company)

    return company


def run_all_seeds(db: Session) -> None:
    """Called from main.py on startup. Order matters — sequences first."""
    seed_sequences(db)
    seed_parent_company(db)
