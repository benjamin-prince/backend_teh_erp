#!/usr/bin/env bash
# ═══════════════════════════════════════════════════════════════════════════════
#  TEHTEK ERP — Debt Module Installer (targeted)
#  Run from /opt/backend_erp:  sudo bash install_debt.sh
# ═══════════════════════════════════════════════════════════════════════════════
set -euo pipefail

PROJECT=/opt/backend_erp
cd "$PROJECT"

G='\033[0;32m' Y='\033[1;33m' B='\033[0;34m' W='\033[1m' N='\033[0m'
ok()   { printf "  ${G}✔${N}  %s\n" "$*"; }
inf()  { printf "  ${B}→${N}  %s\n" "$*"; }
skip() { printf "  ${Y}↷${N}  %s (already done)\n" "$*"; }
hdr()  { printf "\n${W}── %s${N}\n" "$*"; }

FINANCE_MODELS="$PROJECT/app/modules/finance/models.py"
FINANCE_ROUTER="$PROJECT/app/modules/finance/router.py"
MAIN_PY="$PROJECT/app/main.py"
ALEMBIC_VERS="$PROJECT/alembic/versions"

# ─────────────────────────────────────────────────────────────────────────────
# STEP 1 — Migration
# ─────────────────────────────────────────────────────────────────────────────
hdr "1/5  Writing Alembic migration"

MFILE="$ALEMBIC_VERS/a3f8c2d14e90_create_debt_tables.py"
if [ -f "$MFILE" ]; then
  skip "Migration"
else
cat > "$MFILE" << 'EOF'
"""create debt tables

Revision ID: a3f8c2d14e90
Revises: a1b2c3d4e5f6
Create Date: 2026-05-12
"""
from alembic import op
import sqlalchemy as sa

revision      = "a3f8c2d14e90"
down_revision = "a1b2c3d4e5f6"
branch_labels = None
depends_on    = None


def upgrade() -> None:
    op.create_table(
        "debts",
        sa.Column("id",           sa.Integer(),      primary_key=True),
        sa.Column("company_id",   sa.Integer(),      sa.ForeignKey("companies.id"), nullable=False),
        sa.Column("debt_number",  sa.String(30),     unique=True, nullable=False),   # DBT-2026-0001
        sa.Column("creditor_name",sa.String(255),    nullable=False),
        sa.Column("creditor_type",sa.String(50),     nullable=False),
        sa.Column("purpose",      sa.Text(),         nullable=False),
        sa.Column("ref_model",    sa.String(100),    nullable=True),
        sa.Column("ref_id",       sa.Integer(),      nullable=True),
        sa.Column("ref_label",    sa.String(255),    nullable=True),
        sa.Column("principal",          sa.Numeric(15, 2), nullable=False),
        sa.Column("outstanding",        sa.Numeric(15, 2), nullable=False),
        sa.Column("total_paid",         sa.Numeric(15, 2), nullable=False, server_default="0"),
        sa.Column("installment_amount", sa.Numeric(15, 2), nullable=False, server_default="0"),
        sa.Column("interest_rate",      sa.Numeric(5,  2), nullable=True),
        sa.Column("currency",           sa.String(10),     nullable=False, server_default="XAF"),
        sa.Column("repayment_frequency",sa.String(50),     nullable=False, server_default="monthly"),
        sa.Column("start_date",         sa.DateTime(),     nullable=False),
        sa.Column("deadline_date",      sa.DateTime(),     nullable=False),
        sa.Column("end_date",           sa.DateTime(),     nullable=True),
        sa.Column("next_due_date",      sa.DateTime(),     nullable=True),
        sa.Column("last_payment_date",  sa.DateTime(),     nullable=True),
        sa.Column("status",    sa.String(50),  nullable=False, server_default="active"),
        sa.Column("notes",     sa.Text(),      nullable=True),
        sa.Column("created_by",sa.Integer(),   nullable=True),
        sa.Column("created_at",sa.DateTime(),  nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at",sa.DateTime(),  nullable=True),
        sa.Column("deleted_at",sa.DateTime(),  nullable=True),
    )
    op.create_index("ix_debt_company_status",   "debts", ["company_id", "status"])
    op.create_index("ix_debt_next_due_date",    "debts", ["company_id", "next_due_date"])
    op.create_index("ix_debt_deleted_at",       "debts", ["deleted_at"])

    op.create_table(
        "debt_payments",
        sa.Column("id",                 sa.Integer(),      primary_key=True),
        sa.Column("debt_id",            sa.Integer(),      sa.ForeignKey("debts.id"), nullable=False),
        sa.Column("payment_date",       sa.DateTime(),     nullable=False),
        sa.Column("amount",             sa.Numeric(15, 2), nullable=False),
        sa.Column("payment_method",     sa.String(50),     nullable=False, server_default="bank_transfer"),
        sa.Column("money_account_id",   sa.Integer(),      nullable=True),
        sa.Column("money_account_name", sa.String(255),    nullable=True),
        sa.Column("reference",          sa.String(255),    nullable=True),
        sa.Column("notes",              sa.Text(),         nullable=True),
        sa.Column("created_by",         sa.Integer(),      nullable=True),
        sa.Column("created_at",         sa.DateTime(),     nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_debt_payment_debt_id", "debt_payments", ["debt_id"])


def downgrade() -> None:
    op.drop_index("ix_debt_payment_debt_id",  table_name="debt_payments")
    op.drop_table("debt_payments")
    op.drop_index("ix_debt_deleted_at",       table_name="debts")
    op.drop_index("ix_debt_next_due_date",    table_name="debts")
    op.drop_index("ix_debt_company_status",   table_name="debts")
    op.drop_table("debts")
EOF
  ok "Migration written → $MFILE"
fi

# ─────────────────────────────────────────────────────────────────────────────
# STEP 2 — Append models
# ─────────────────────────────────────────────────────────────────────────────
hdr "2/5  Appending Debt models to finance/models.py"

if grep -q "class Debt(" "$FINANCE_MODELS" 2>/dev/null; then
  skip "Debt model"
else
cat >> "$FINANCE_MODELS" << 'EOF'


# ── Debt (added by install_debt.sh) ──────────────────────────────────────────

class Debt(Base):
    __tablename__ = "debts"

    id            = Column(Integer, primary_key=True)
    company_id    = Column(Integer, ForeignKey("companies.id"), nullable=False)
    debt_number   = Column(String(30), unique=True, nullable=False)  # DBT-2026-0001
    creditor_name = Column(String(255), nullable=False)
    creditor_type = Column(String(50),  nullable=False)  # bank|supplier|landlord|individual|other
    purpose       = Column(Text,        nullable=False)
    ref_model     = Column(String(100), nullable=True)
    ref_id        = Column(Integer,     nullable=True)
    ref_label     = Column(String(255), nullable=True)

    principal           = Column(Numeric(15, 2), nullable=False)
    outstanding         = Column(Numeric(15, 2), nullable=False)
    total_paid          = Column(Numeric(15, 2), nullable=False, default=0)
    installment_amount  = Column(Numeric(15, 2), nullable=False, default=0)
    interest_rate       = Column(Numeric(5,  2), nullable=True)
    currency            = Column(String(10),     nullable=False, default="XAF")

    repayment_frequency = Column(String(50),  nullable=False, default="monthly")
    start_date          = Column(DateTime,    nullable=False)
    deadline_date       = Column(DateTime,    nullable=False)
    end_date            = Column(DateTime,    nullable=True)
    next_due_date       = Column(DateTime,    nullable=True)
    last_payment_date   = Column(DateTime,    nullable=True)

    status     = Column(String(50), nullable=False, default="active")
    notes      = Column(Text,       nullable=True)
    created_by = Column(Integer,    nullable=True)
    created_at = Column(DateTime,   default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime,   default=datetime.utcnow, onupdate=datetime.utcnow)
    deleted_at = Column(DateTime,   nullable=True)

    debt_payments = relationship("DebtPayment", back_populates="debt", cascade="all, delete-orphan")

    __table_args__ = (
        Index("ix_debt_company_status", "company_id", "status"),
        Index("ix_debt_next_due_date",  "company_id", "next_due_date"),
    )


class DebtPayment(Base):
    __tablename__ = "debt_payments"

    id                  = Column(Integer,      primary_key=True)
    debt_id             = Column(Integer,      ForeignKey("debts.id"), nullable=False)
    payment_date        = Column(DateTime,     nullable=False)
    amount              = Column(Numeric(15, 2), nullable=False)
    payment_method      = Column(String(50),   nullable=False, default="bank_transfer")
    money_account_id    = Column(Integer,      nullable=True)
    money_account_name  = Column(String(255),  nullable=True)
    reference           = Column(String(255),  nullable=True)
    notes               = Column(Text,         nullable=True)
    created_by          = Column(Integer,      nullable=True)
    created_at          = Column(DateTime,     default=datetime.utcnow, nullable=False)

    debt = relationship("Debt", back_populates="debt_payments")

    __table_args__ = (Index("ix_debt_payment_debt_id", "debt_id"),)
EOF
  ok "Debt + DebtPayment appended to models.py"
fi

# ─────────────────────────────────────────────────────────────────────────────
# STEP 3 — Append router endpoints
# ─────────────────────────────────────────────────────────────────────────────
hdr "3/5  Appending debt endpoints to finance/router.py"

if grep -q '"/debt"' "$FINANCE_ROUTER" 2>/dev/null; then
  skip "Debt routes"
else
cat >> "$FINANCE_ROUTER" << 'EOF'


# ── Debt (added by install_debt.sh) ──────────────────────────────────────────

from app.modules.finance.models import Debt, DebtPayment


class DebtCreate(BaseModel):
    creditor_name:       str
    creditor_type:       str                    # bank|supplier|landlord|individual|other
    purpose:             str
    ref_model:           Optional[str]  = None
    ref_id:              Optional[int]  = None
    ref_label:           Optional[str]  = None
    principal:           float
    outstanding:         Optional[float] = None
    monthly_payment:     Optional[float] = None  # frontend alias → installment_amount
    installment_amount:  Optional[float] = None
    interest_rate:       Optional[float] = None
    currency:            str             = "XAF"
    repayment_frequency: str             = "monthly"
    start_date:          datetime
    end_date:            Optional[datetime] = None  # frontend alias → deadline_date
    deadline_date:       Optional[datetime] = None
    next_due_date:       Optional[datetime] = None
    status:              str             = "active"
    notes:               Optional[str]   = None


class DebtUpdate(BaseModel):
    creditor_name:       Optional[str]      = None
    creditor_type:       Optional[str]      = None
    purpose:             Optional[str]      = None
    ref_model:           Optional[str]      = None
    ref_label:           Optional[str]      = None
    outstanding:         Optional[float]    = None
    monthly_payment:     Optional[float]    = None
    installment_amount:  Optional[float]    = None
    interest_rate:       Optional[float]    = None
    repayment_frequency: Optional[str]      = None
    end_date:            Optional[datetime] = None
    deadline_date:       Optional[datetime] = None
    next_due_date:       Optional[datetime] = None
    status:              Optional[str]      = None
    notes:               Optional[str]      = None


class DebtPaymentCreate(BaseModel):
    amount:         float
    notes:          Optional[str] = None
    payment_method: str           = "bank_transfer"
    reference:      Optional[str] = None


def _debt_number(db: Session) -> str:
    from sqlalchemy import extract
    from sqlalchemy import func as _f
    year = datetime.utcnow().year
    n = db.query(_f.count(Debt.id)).filter(
        extract("year", Debt.created_at) == year
    ).scalar() or 0
    return f"DBT-{year}-{str(n + 1).zfill(4)}"


@router.get("/debt")
def list_debts(
    status: Optional[str] = None,
    skip:   int = 0,
    limit:  int = 100,
    db:     Session = Depends(get_db),
    current_user=Depends(require_permission("finance:debt")),
):
    q = db.query(Debt).filter(
        Debt.company_id == current_user.company_id,
        Debt.deleted_at.is_(None),
    )
    if status:
        q = q.filter(Debt.status == status)
    return (
        q.order_by(Debt.next_due_date.asc().nulls_last(), Debt.created_at.desc())
        .offset(skip).limit(limit).all()
    )


@router.post("/debt", status_code=201)
def create_debt(
    body: DebtCreate,
    db:   Session = Depends(get_db),
    current_user=Depends(require_permission("finance:debt")),
):
    installment = body.installment_amount or body.monthly_payment or 0
    deadline    = body.deadline_date or body.end_date
    if not deadline:
        raise HTTPException(400, "deadline_date (or end_date) is required")
    outstanding = body.outstanding if body.outstanding is not None else body.principal
    d = Debt(
        company_id=current_user.company_id,
        debt_number=_debt_number(db),
        creditor_name=body.creditor_name,
        creditor_type=body.creditor_type,
        purpose=body.purpose,
        ref_model=body.ref_model,
        ref_id=body.ref_id,
        ref_label=body.ref_label,
        principal=body.principal,
        outstanding=outstanding,
        total_paid=0,
        installment_amount=installment,
        interest_rate=body.interest_rate,
        currency=body.currency,
        repayment_frequency=body.repayment_frequency,
        start_date=body.start_date,
        deadline_date=deadline,
        end_date=body.end_date,
        next_due_date=body.next_due_date,
        status=body.status,
        notes=body.notes,
        created_by=current_user.id,
    )
    db.add(d)
    db.commit()
    db.refresh(d)
    return d


@router.get("/debt/{debt_id}")
def get_debt(
    debt_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(require_permission("finance:debt")),
):
    d = db.query(Debt).filter_by(
        id=debt_id, company_id=current_user.company_id, deleted_at=None
    ).first()
    if not d:
        raise HTTPException(404, "Debt not found")
    return d


@router.patch("/debt/{debt_id}")
def update_debt(
    debt_id: int,
    body: DebtUpdate,
    db:   Session = Depends(get_db),
    current_user=Depends(require_permission("finance:debt")),
):
    d = db.query(Debt).filter_by(
        id=debt_id, company_id=current_user.company_id, deleted_at=None
    ).first()
    if not d:
        raise HTTPException(404, "Debt not found")
    patch = body.model_dump(exclude_unset=True)
    # Resolve aliases
    if "monthly_payment" in patch and "installment_amount" not in patch:
        patch["installment_amount"] = patch.pop("monthly_payment")
    else:
        patch.pop("monthly_payment", None)
    if "end_date" in patch and "deadline_date" not in patch:
        patch["deadline_date"] = patch.pop("end_date")
    for k, v in patch.items():
        if hasattr(d, k):
            setattr(d, k, v)
    d.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(d)
    return d


@router.delete("/debt/{debt_id}", status_code=204)
def delete_debt(
    debt_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(require_permission("finance:debt")),
):
    d = db.query(Debt).filter_by(
        id=debt_id, company_id=current_user.company_id, deleted_at=None
    ).first()
    if not d:
        raise HTTPException(404, "Debt not found")
    d.deleted_at = datetime.utcnow()
    db.commit()


@router.post("/debt/{debt_id}/payment")
def record_debt_payment(
    debt_id: int,
    body: DebtPaymentCreate,
    db:   Session = Depends(get_db),
    current_user=Depends(require_permission("finance:debt")),
):
    d = db.query(Debt).filter_by(
        id=debt_id, company_id=current_user.company_id, deleted_at=None
    ).first()
    if not d:
        raise HTTPException(404, "Debt not found")
    pay = DebtPayment(
        debt_id=d.id,
        payment_date=datetime.utcnow(),
        amount=body.amount,
        payment_method=body.payment_method,
        reference=body.reference,
        notes=body.notes,
        created_by=current_user.id,
    )
    db.add(pay)
    d.outstanding       = max(0, float(d.outstanding) - body.amount)
    d.total_paid        = float(d.total_paid or 0) + body.amount
    d.last_payment_date = datetime.utcnow()
    if d.outstanding <= 0:
        d.status = "paid_off"
    d.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(d)
    return d


@router.get("/debt/{debt_id}/payments")
def list_debt_payments(
    debt_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(require_permission("finance:debt")),
):
    d = db.query(Debt).filter_by(
        id=debt_id, company_id=current_user.company_id, deleted_at=None
    ).first()
    if not d:
        raise HTTPException(404, "Debt not found")
    return (
        db.query(DebtPayment)
        .filter_by(debt_id=d.id)
        .order_by(DebtPayment.payment_date.desc())
        .all()
    )
EOF
  ok "Debt endpoints appended to router.py"
fi

# ─────────────────────────────────────────────────────────────────────────────
# STEP 4 — Patch main.py: add Debt, DebtPayment to finance import
# ─────────────────────────────────────────────────────────────────────────────
hdr "4/5  Patching app/main.py"

python3 - << 'PY'
import re, sys

path = "/opt/backend_erp/app/main.py"
text = open(path).read()

if "Debt," in text or "DebtPayment" in text:
    print("  \033[1;33m↷\033[0m  main.py already imports Debt/DebtPayment")
    sys.exit(0)

# Replace the finance models import line to add Debt + DebtPayment
old = "from app.modules.finance.models import (  # noqa: F401\n    Invoice, Payment, CashSession, Expense\n)"
new = "from app.modules.finance.models import (  # noqa: F401\n    Invoice, Payment, CashSession, Expense, Debt, DebtPayment\n)"

if old in text:
    text = text.replace(old, new)
    open(path, "w").write(text)
    print("  \033[0;32m✔\033[0m  Debt, DebtPayment added to main.py finance import")
else:
    # Fallback: find any finance.models import and append
    patched = re.sub(
        r'(from app\.modules\.finance\.models import[^)]+)(Expense)(\s*\))',
        r'\1Expense, Debt, DebtPayment\3',
        text,
    )
    if patched != text:
        open(path, "w").write(patched)
        print("  \033[0;32m✔\033[0m  Debt, DebtPayment added to main.py (regex fallback)")
    else:
        print("  \033[1;33m⚠\033[0m  Could not auto-patch main.py — add manually:")
        print("        from app.modules.finance.models import (  # noqa: F401")
        print("            Invoice, Payment, CashSession, Expense, Debt, DebtPayment")
        print("        )")
PY

# ─────────────────────────────────────────────────────────────────────────────
# STEP 5 — Run migration & restart
# ─────────────────────────────────────────────────────────────────────────────
hdr "5/5  Running migration"

cd "$PROJECT"
inf "Running alembic inside container …"
docker compose exec backend alembic upgrade head
ok "Migration complete"

inf "Restarting backend container …"
docker compose restart backend
ok "tehtek_backend restarted"

# ─────────────────────────────────────────────────────────────────────────────
printf "\n${W}═══════════════════════════════════════════${N}\n"
printf "${G}  Debt module installed successfully ✔${N}\n"
printf "${W}═══════════════════════════════════════════${N}\n\n"
printf "  Live endpoints:\n"
printf "    GET    /api/v1/finance/debt\n"
printf "    POST   /api/v1/finance/debt\n"
printf "    GET    /api/v1/finance/debt/{id}\n"
printf "    PATCH  /api/v1/finance/debt/{id}\n"
printf "    DELETE /api/v1/finance/debt/{id}\n"
printf "    POST   /api/v1/finance/debt/{id}/payment\n"
printf "    GET    /api/v1/finance/debt/{id}/payments\n\n"
printf "  Permission required: ${Y}finance:debt${N}\n\n"
