"""finance_extended

Revision ID: a1b2c3d4e5f6
Revises: <replace_with_your_last_revision_id>
Create Date: 2026-05-03 10:00:00.000000

Tables created:
  money_accounts, income, finance_expenses, locations,
  debts, debt_payments, receivables, receivable_payments,
  budget_lines, vehicles, autopark_records
"""
from alembic import op
import sqlalchemy as sa

# revision identifiers
revision = "a1b2c3d4e5f6"
down_revision = "ed56daa408ae"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ── containers ──────────────────────────────────────────────────────────

    op.create_table(
        "containers",
        sa.Column("id",         sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column("company_id", sa.BigInteger(), sa.ForeignKey("companies.id"), nullable=False),
        sa.Column("branch_id",  sa.BigInteger(), sa.ForeignKey("branches.id"),  nullable=True),
        sa.Column("created_by", sa.BigInteger(), sa.ForeignKey("users.id"),     nullable=True),
 
        # Identifiers
        sa.Column("container_number", sa.String(64),  nullable=False),  # internal, auto-generated
        sa.Column("tracking_number",  sa.String(128), nullable=True),   # carrier BL / AWB
        sa.Column("invoice_number",   sa.String(128), nullable=True),   # commercial invoice
 
        # Owner
        sa.Column("owner_name",    sa.String(255), nullable=True),
        sa.Column("owner_company", sa.String(255), nullable=True),
        sa.Column("owner_contact", sa.String(128), nullable=True),
 
        # Tracking link
        sa.Column("tracking_link", sa.String(512), nullable=True),
 
        # Broker
        sa.Column("broker_name",      sa.String(255), nullable=True),
        sa.Column("broker_company",   sa.String(255), nullable=True),
        sa.Column("broker_contact",   sa.String(128), nullable=True),
        sa.Column("broker_reference", sa.String(128), nullable=True),
 
        # Core
        sa.Column("type",           sa.String(32), nullable=False, server_default="sea"),
        sa.Column("status",         sa.String(32), nullable=False, server_default="preparing"),
        sa.Column("depart_from",    sa.String(255), nullable=True),
        sa.Column("destination",    sa.String(255), nullable=True),
        sa.Column("load_date",      sa.Date(), nullable=True),
        sa.Column("departure_date", sa.Date(), nullable=True),
        sa.Column("arrival_date",   sa.Date(), nullable=True),
 
        # Finance
        sa.Column("total_spent",      sa.Numeric(18, 2), nullable=False, server_default="0"),
        sa.Column("total_earned",     sa.Numeric(18, 2), nullable=False, server_default="0"),
        sa.Column("currency",         sa.String(8),      nullable=False, server_default="XAF"),
        sa.Column("packages_count",   sa.Integer(),      nullable=False, server_default="0"),
        sa.Column("customers_count",  sa.Integer(),      nullable=False, server_default="0"),
 
        sa.Column("notes",      sa.Text(),                  nullable=True),
        sa.Column("closed_at",  sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_containers_id",               "containers", ["id"],               unique=False)
    op.create_index("ix_containers_company_id",       "containers", ["company_id"],       unique=False)
    op.create_index("ix_containers_container_number", "containers", ["container_number"], unique=True)
    op.create_index("ix_containers_tracking_number",  "containers", ["tracking_number"],  unique=False)
    op.create_index("ix_containers_invoice_number",   "containers", ["invoice_number"],   unique=False)
 
    op.create_table(
        "container_shipments",
        sa.Column("id",           sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column("container_id", sa.BigInteger(), sa.ForeignKey("containers.id", ondelete="CASCADE"), nullable=False),
        sa.Column("shipment_id",  sa.BigInteger(), sa.ForeignKey("shipments.id",  ondelete="CASCADE"), nullable=False),
        sa.Column("added_at",     sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("added_by",     sa.BigInteger(), sa.ForeignKey("users.id"), nullable=True),
    )
    op.create_index("ix_cs_id",           "container_shipments", ["id"],           unique=False)
    op.create_index("ix_cs_container_id", "container_shipments", ["container_id"], unique=False)
    op.create_index("ix_cs_shipment_id",  "container_shipments", ["shipment_id"],  unique=False)
    op.create_unique_constraint("uq_container_shipment", "container_shipments", ["container_id", "shipment_id"])
 



    # ── locations ─────────────────────────────────────────────────────────────
    # Created first — referenced by money_accounts, finance_expenses, vehicles
    op.create_table(
        "locations",
        sa.Column("id",                      sa.Integer(),      primary_key=True),
        sa.Column("company_id",              sa.Integer(),      sa.ForeignKey("companies.id"), nullable=False),
        sa.Column("name",                    sa.String(150),    nullable=False),
        sa.Column("type",                    sa.String(30),     nullable=False),
        sa.Column("address",                 sa.String(300),    nullable=True),
        sa.Column("city",                    sa.String(100),    nullable=False),
        sa.Column("country",                 sa.String(100),    nullable=False, server_default="Cameroon"),
        sa.Column("rent_monthly",            sa.Numeric(14, 2), nullable=False, server_default="0"),
        sa.Column("electricity_monthly",     sa.Numeric(14, 2), nullable=False, server_default="0"),
        sa.Column("water_monthly",           sa.Numeric(14, 2), nullable=False, server_default="0"),
        sa.Column("internet_monthly",        sa.Numeric(14, 2), nullable=False, server_default="0"),
        sa.Column("other_utilities_monthly", sa.Numeric(14, 2), nullable=False, server_default="0"),
        sa.Column("lease_start",             sa.DateTime(),     nullable=True),
        sa.Column("lease_end",               sa.DateTime(),     nullable=True),
        sa.Column("next_payment_due",        sa.DateTime(),     nullable=True),
        sa.Column("landlord_name",           sa.String(200),    nullable=True),
        sa.Column("landlord_contact",        sa.String(100),    nullable=True),
        sa.Column("notes",                   sa.Text(),         nullable=True),
        sa.Column("status",                  sa.String(30),     nullable=False, server_default="active"),
        sa.Column("created_at",              sa.DateTime(),     nullable=False, server_default=sa.text("NOW()")),
        sa.Column("updated_at",              sa.DateTime(),     nullable=False, server_default=sa.text("NOW()")),
    )
    op.create_index("ix_location_company", "locations", ["company_id"])
    op.create_index("ix_location_status",  "locations", ["company_id", "status"])

    # ── money_accounts ────────────────────────────────────────────────────────
    op.create_table(
        "money_accounts",
        sa.Column("id",               sa.Integer(),      primary_key=True),
        sa.Column("company_id",       sa.Integer(),      sa.ForeignKey("companies.id"), nullable=False),
        sa.Column("name",             sa.String(150),    nullable=False),
        sa.Column("type",             sa.String(30),     nullable=False),
        sa.Column("currency",         sa.String(10),     nullable=False, server_default="XAF"),
        sa.Column("opening_balance",  sa.Numeric(16, 2), nullable=False, server_default="0"),
        sa.Column("current_balance",  sa.Numeric(16, 2), nullable=False, server_default="0"),
        sa.Column("location_id",      sa.Integer(),      sa.ForeignKey("locations.id"),  nullable=True),
        sa.Column("is_active",        sa.Boolean(),      nullable=False, server_default="true"),
        sa.Column("notes",            sa.Text(),         nullable=True),
        sa.Column("created_at",       sa.DateTime(),     nullable=False, server_default=sa.text("NOW()")),
        sa.Column("updated_at",       sa.DateTime(),     nullable=False, server_default=sa.text("NOW()")),
    )
    op.create_index("ix_money_account_company", "money_accounts", ["company_id"])
    op.create_index("ix_money_account_type",    "money_accounts", ["company_id", "type"])

    # ── income ────────────────────────────────────────────────────────────────
    op.create_table(
        "income",
        sa.Column("id",               sa.Integer(),       primary_key=True),
        sa.Column("company_id",       sa.Integer(),       sa.ForeignKey("companies.id"),      nullable=False),
        sa.Column("branch_id",        sa.Integer(),       sa.ForeignKey("branches.id"),       nullable=True),
        sa.Column("income_number",    sa.String(30),      unique=True,                        nullable=False),
        sa.Column("date",             sa.DateTime(),      nullable=False),
        sa.Column("description",      sa.Text(),          nullable=False),
        sa.Column("category",         sa.String(60),      nullable=False),
        sa.Column("ref_model",        sa.String(50),      nullable=True),
        sa.Column("ref_id",           sa.Integer(),       nullable=True),
        sa.Column("ref_label",        sa.String(200),     nullable=True),
        sa.Column("customer_id",      sa.Integer(),       sa.ForeignKey("customers.id"),      nullable=True),
        sa.Column("tracking_number",  sa.String(100),     nullable=True),
        sa.Column("container_id",     sa.Integer(),       nullable=True),
        sa.Column("amount",           sa.Numeric(16, 2),  nullable=False),
        sa.Column("currency",         sa.String(10),      nullable=False, server_default="XAF"),
        sa.Column("exchange_rate",    sa.Numeric(12, 6),  nullable=False, server_default="1"),
        sa.Column("amount_base",      sa.Numeric(16, 2),  nullable=False),
        sa.Column("payment_method",   sa.String(30),      nullable=False),
        sa.Column("money_account_id", sa.Integer(),       sa.ForeignKey("money_accounts.id"), nullable=True),
        sa.Column("status",           sa.String(30),      nullable=False, server_default="pending"),
        sa.Column("notes",            sa.Text(),          nullable=True),
        sa.Column("receipt_url",      sa.String(500),     nullable=True),
        sa.Column("created_by",       sa.Integer(),       sa.ForeignKey("users.id"),          nullable=False),
        sa.Column("created_at",       sa.DateTime(),      nullable=False, server_default=sa.text("NOW()")),
        sa.Column("updated_at",       sa.DateTime(),      nullable=False, server_default=sa.text("NOW()")),
        sa.Column("deleted_at",       sa.DateTime(),      nullable=True),
    )
    op.create_index("ix_income_company_date",     "income", ["company_id", "date"])
    op.create_index("ix_income_company_category", "income", ["company_id", "category"])
    op.create_index("ix_income_customer",         "income", ["customer_id"])
    op.create_index("ix_income_account",          "income", ["money_account_id"])
    op.create_index("ix_income_ref",              "income", ["ref_model", "ref_id"])

    # ── finance_expenses ──────────────────────────────────────────────────────
    op.create_table(
        "finance_expenses",
        sa.Column("id",               sa.Integer(),       primary_key=True),
        sa.Column("company_id",       sa.Integer(),       sa.ForeignKey("companies.id"),      nullable=False),
        sa.Column("branch_id",        sa.Integer(),       sa.ForeignKey("branches.id"),       nullable=True),
        sa.Column("expense_number",   sa.String(30),      unique=True,                        nullable=False),
        sa.Column("date",             sa.DateTime(),      nullable=False),
        sa.Column("description",      sa.Text(),          nullable=False),
        sa.Column("category",         sa.String(60),      nullable=False),
        sa.Column("ref_model",        sa.String(50),      nullable=False),   # REQUIRED
        sa.Column("ref_id",           sa.Integer(),       nullable=True),
        sa.Column("ref_label",        sa.String(200),     nullable=False),   # REQUIRED
        sa.Column("supplier_id",      sa.Integer(),       nullable=True),
        sa.Column("customer_id",      sa.Integer(),       sa.ForeignKey("customers.id"),      nullable=True),
        sa.Column("location_id",      sa.Integer(),       sa.ForeignKey("locations.id"),      nullable=True),
        sa.Column("amount",           sa.Numeric(16, 2),  nullable=False),
        sa.Column("currency",         sa.String(10),      nullable=False, server_default="XAF"),
        sa.Column("exchange_rate",    sa.Numeric(12, 6),  nullable=False, server_default="1"),
        sa.Column("amount_base",      sa.Numeric(16, 2),  nullable=False),
        sa.Column("payment_method",   sa.String(30),      nullable=True),
        sa.Column("money_account_id", sa.Integer(),       sa.ForeignKey("money_accounts.id"), nullable=True),
        sa.Column("status",           sa.String(30),      nullable=False, server_default="pending"),
        sa.Column("receipt_url",      sa.String(500),     nullable=True),
        sa.Column("notes",            sa.Text(),          nullable=True),
        sa.Column("created_by",       sa.Integer(),       sa.ForeignKey("users.id"),          nullable=False),
        sa.Column("approved_by",      sa.Integer(),       sa.ForeignKey("users.id"),          nullable=True),
        sa.Column("created_at",       sa.DateTime(),      nullable=False, server_default=sa.text("NOW()")),
        sa.Column("updated_at",       sa.DateTime(),      nullable=False, server_default=sa.text("NOW()")),
        sa.Column("deleted_at",       sa.DateTime(),      nullable=True),
    )
    op.create_index("ix_fin_expense_company_date",     "finance_expenses", ["company_id", "date"])
    op.create_index("ix_fin_expense_company_category", "finance_expenses", ["company_id", "category"])
    op.create_index("ix_fin_expense_location",         "finance_expenses", ["location_id"])
    op.create_index("ix_fin_expense_account",          "finance_expenses", ["money_account_id"])
    op.create_index("ix_fin_expense_ref",              "finance_expenses", ["ref_model", "ref_id"])

    # ── debts ─────────────────────────────────────────────────────────────────
    op.create_table(
        "debts",
        sa.Column("id",                  sa.Integer(),      primary_key=True),
        sa.Column("company_id",          sa.Integer(),      sa.ForeignKey("companies.id"), nullable=False),
        sa.Column("debt_number",         sa.String(30),     unique=True,                   nullable=False),
        sa.Column("creditor_name",       sa.String(200),    nullable=False),
        sa.Column("creditor_type",       sa.String(30),     nullable=False),
        sa.Column("purpose",             sa.Text(),         nullable=False),
        sa.Column("ref_model",           sa.String(50),     nullable=True),
        sa.Column("ref_id",              sa.Integer(),      nullable=True),
        sa.Column("ref_label",           sa.String(200),    nullable=True),
        sa.Column("principal",           sa.Numeric(16, 2), nullable=False),
        sa.Column("outstanding",         sa.Numeric(16, 2), nullable=False),
        sa.Column("monthly_payment",     sa.Numeric(14, 2), nullable=True),
        sa.Column("interest_rate",       sa.Numeric(6, 4),  nullable=True),
        sa.Column("interest_accrued",    sa.Numeric(14, 2), nullable=False, server_default="0"),
        sa.Column("start_date",          sa.DateTime(),     nullable=False),
        sa.Column("end_date",            sa.DateTime(),     nullable=True),
        sa.Column("next_due_date",       sa.DateTime(),     nullable=True),
        sa.Column("last_payment_date",   sa.DateTime(),     nullable=True),
        sa.Column("last_payment_amount", sa.Numeric(14, 2), nullable=True),
        sa.Column("currency",            sa.String(10),     nullable=False, server_default="XAF"),
        sa.Column("exchange_rate",       sa.Numeric(12, 6), nullable=False, server_default="1"),
        sa.Column("amount_base",         sa.Numeric(16, 2), nullable=False),
        sa.Column("status",              sa.String(30),     nullable=False, server_default="active"),
        sa.Column("notes",               sa.Text(),         nullable=True),
        sa.Column("created_at",          sa.DateTime(),     nullable=False, server_default=sa.text("NOW()")),
        sa.Column("updated_at",          sa.DateTime(),     nullable=False, server_default=sa.text("NOW()")),
    )
    op.create_index("ix_debt_company_status", "debts", ["company_id", "status"])

    # ── debt_payments ─────────────────────────────────────────────────────────
    op.create_table(
        "debt_payments",
        sa.Column("id",               sa.Integer(),      primary_key=True),
        sa.Column("company_id",       sa.Integer(),      sa.ForeignKey("companies.id"),      nullable=False),
        sa.Column("debt_id",          sa.Integer(),      sa.ForeignKey("debts.id"),          nullable=False),
        sa.Column("expense_id",       sa.Integer(),      sa.ForeignKey("finance_expenses.id"), nullable=True),
        sa.Column("amount",           sa.Numeric(14, 2), nullable=False),
        sa.Column("payment_date",     sa.DateTime(),     nullable=False),
        sa.Column("money_account_id", sa.Integer(),      sa.ForeignKey("money_accounts.id"), nullable=False),
        sa.Column("payment_method",   sa.String(30),     nullable=False),
        sa.Column("note",             sa.Text(),         nullable=True),
        sa.Column("created_by",       sa.Integer(),      sa.ForeignKey("users.id"),          nullable=False),
        sa.Column("created_at",       sa.DateTime(),     nullable=False, server_default=sa.text("NOW()")),
    )
    op.create_index("ix_debt_payment_debt", "debt_payments", ["debt_id"])

    # ── receivables ───────────────────────────────────────────────────────────
    op.create_table(
        "receivables",
        sa.Column("id",                sa.Integer(),      primary_key=True),
        sa.Column("company_id",        sa.Integer(),      sa.ForeignKey("companies.id"),  nullable=False),
        sa.Column("receivable_number", sa.String(30),     unique=True,                    nullable=False),
        sa.Column("client_name",       sa.String(200),    nullable=False),
        sa.Column("client_id",         sa.Integer(),      sa.ForeignKey("customers.id"),  nullable=True),
        sa.Column("invoice_number",    sa.String(30),     nullable=True),
        sa.Column("ref_model",         sa.String(50),     nullable=False),
        sa.Column("ref_id",            sa.Integer(),      nullable=True),
        sa.Column("ref_label",         sa.String(200),    nullable=False),
        sa.Column("amount",            sa.Numeric(16, 2), nullable=False),
        sa.Column("paid_amount",       sa.Numeric(16, 2), nullable=False, server_default="0"),
        sa.Column("balance_due",       sa.Numeric(16, 2), nullable=False),
        sa.Column("currency",          sa.String(10),     nullable=False, server_default="XAF"),
        sa.Column("exchange_rate",     sa.Numeric(12, 6), nullable=False, server_default="1"),
        sa.Column("amount_base",       sa.Numeric(16, 2), nullable=False),
        sa.Column("issue_date",        sa.DateTime(),     nullable=False),
        sa.Column("due_date",          sa.DateTime(),     nullable=False),
        sa.Column("status",            sa.String(30),     nullable=False, server_default="draft"),
        sa.Column("notes",             sa.Text(),         nullable=True),
        sa.Column("created_at",        sa.DateTime(),     nullable=False, server_default=sa.text("NOW()")),
        sa.Column("updated_at",        sa.DateTime(),     nullable=False, server_default=sa.text("NOW()")),
    )
    op.create_index("ix_receivable_company_status", "receivables", ["company_id", "status"])
    op.create_index("ix_receivable_client",         "receivables", ["client_id"])
    op.create_index("ix_receivable_due_date",       "receivables", ["due_date"])

    # ── receivable_payments ───────────────────────────────────────────────────
    op.create_table(
        "receivable_payments",
        sa.Column("id",               sa.Integer(),      primary_key=True),
        sa.Column("company_id",       sa.Integer(),      sa.ForeignKey("companies.id"),      nullable=False),
        sa.Column("receivable_id",    sa.Integer(),      sa.ForeignKey("receivables.id"),    nullable=False),
        sa.Column("income_id",        sa.Integer(),      sa.ForeignKey("income.id"),         nullable=True),
        sa.Column("client_id",        sa.Integer(),      sa.ForeignKey("customers.id"),      nullable=True),
        sa.Column("amount",           sa.Numeric(14, 2), nullable=False),
        sa.Column("payment_date",     sa.DateTime(),     nullable=False),
        sa.Column("payment_method",   sa.String(30),     nullable=False),
        sa.Column("money_account_id", sa.Integer(),      sa.ForeignKey("money_accounts.id"), nullable=False),
        sa.Column("receipt_url",      sa.String(500),    nullable=True),
        sa.Column("note",             sa.Text(),         nullable=True),
        sa.Column("collected_by",     sa.Integer(),      sa.ForeignKey("users.id"),          nullable=False),
        sa.Column("created_at",       sa.DateTime(),     nullable=False, server_default=sa.text("NOW()")),
    )
    op.create_index("ix_rec_payment_receivable", "receivable_payments", ["receivable_id"])
    op.create_index("ix_rec_payment_client",     "receivable_payments", ["client_id"])

    # ── budget_lines ──────────────────────────────────────────────────────────
    op.create_table(
        "budget_lines",
        sa.Column("id",             sa.Integer(),      primary_key=True),
        sa.Column("company_id",     sa.Integer(),      sa.ForeignKey("companies.id"), nullable=False),
        sa.Column("period_year",    sa.Integer(),      nullable=False),
        sa.Column("period_month",   sa.Integer(),      nullable=True),
        sa.Column("category",       sa.String(60),     nullable=False),
        sa.Column("label",          sa.String(150),    nullable=False),
        sa.Column("budget_amount",  sa.Numeric(14, 2), nullable=False),
        sa.Column("spent_amount",   sa.Numeric(14, 2), nullable=False, server_default="0"),
        sa.Column("income_amount",  sa.Numeric(14, 2), nullable=False, server_default="0"),
        sa.Column("variance",       sa.Numeric(14, 2), nullable=False, server_default="0"),
        sa.Column("variance_pct",   sa.Numeric(8, 4),  nullable=False, server_default="0"),
        sa.Column("currency",       sa.String(10),     nullable=False, server_default="XAF"),
        sa.Column("notes",          sa.Text(),         nullable=True),
        sa.Column("created_at",     sa.DateTime(),     nullable=False, server_default=sa.text("NOW()")),
        sa.Column("updated_at",     sa.DateTime(),     nullable=False, server_default=sa.text("NOW()")),
    )
    op.create_index(
        "ix_budget_company_period", "budget_lines",
        ["company_id", "period_year", "period_month"],
    )
    op.create_unique_constraint(
        "uq_budget_period_category", "budget_lines",
        ["company_id", "period_year", "period_month", "category"],
    )

    # ── vehicles ──────────────────────────────────────────────────────────────
    op.create_table(
        "vehicles",
        sa.Column("id",           sa.Integer(),  primary_key=True),
        sa.Column("company_id",   sa.Integer(),  sa.ForeignKey("companies.id"),  nullable=False),
        sa.Column("plate_number", sa.String(30), nullable=False),
        sa.Column("vin",          sa.String(50), unique=True,                    nullable=True),
        sa.Column("brand",        sa.String(80), nullable=False),
        sa.Column("model",        sa.String(80), nullable=False),
        sa.Column("year",         sa.Integer(),  nullable=True),
        sa.Column("color",        sa.String(40), nullable=True),
        sa.Column("vehicle_type", sa.String(30), nullable=False, server_default="sedan"),
        sa.Column("owner_type",   sa.String(30), nullable=False, server_default="customer"),
        sa.Column("customer_id",  sa.Integer(),  sa.ForeignKey("customers.id"), nullable=True),
        sa.Column("location_id",  sa.Integer(),  sa.ForeignKey("locations.id"), nullable=True),
        sa.Column("status",       sa.String(30), nullable=False, server_default="parked"),
        sa.Column("notes",        sa.Text(),     nullable=True),
        sa.Column("created_at",   sa.DateTime(), nullable=False, server_default=sa.text("NOW()")),
        sa.Column("updated_at",   sa.DateTime(), nullable=False, server_default=sa.text("NOW()")),
    )
    op.create_index("ix_vehicle_company", "vehicles", ["company_id"])
    op.create_unique_constraint(
        "uq_vehicle_plate_company", "vehicles", ["company_id", "plate_number"]
    )

    # ── autopark_records ──────────────────────────────────────────────────────
    op.create_table(
        "autopark_records",
        sa.Column("id",             sa.Integer(),      primary_key=True),
        sa.Column("company_id",     sa.Integer(),      sa.ForeignKey("companies.id"),  nullable=False),
        sa.Column("record_number",  sa.String(30),     unique=True,                    nullable=False),
        sa.Column("vehicle_id",     sa.Integer(),      sa.ForeignKey("vehicles.id"),   nullable=False),
        sa.Column("customer_id",    sa.Integer(),      sa.ForeignKey("customers.id"),  nullable=False),
        sa.Column("location_id",    sa.Integer(),      sa.ForeignKey("locations.id"),  nullable=False),
        sa.Column("entry_date",     sa.DateTime(),     nullable=False),
        sa.Column("exit_date",      sa.DateTime(),     nullable=True),
        sa.Column("duration_days",  sa.Numeric(8, 2),  nullable=True),
        sa.Column("parking_rate",   sa.Numeric(12, 2), nullable=False),
        sa.Column("total_amount",   sa.Numeric(14, 2), nullable=True),
        sa.Column("paid_amount",    sa.Numeric(14, 2), nullable=False, server_default="0"),
        sa.Column("balance_due",    sa.Numeric(14, 2), nullable=True),
        sa.Column("receivable_id",  sa.Integer(),      sa.ForeignKey("receivables.id"), nullable=True),
        sa.Column("status",         sa.String(30),     nullable=False, server_default="active"),
        sa.Column("notes",          sa.Text(),         nullable=True),
        sa.Column("created_at",     sa.DateTime(),     nullable=False, server_default=sa.text("NOW()")),
        sa.Column("updated_at",     sa.DateTime(),     nullable=False, server_default=sa.text("NOW()")),
    )
    op.create_index("ix_autopark_company_status", "autopark_records", ["company_id", "status"])
    op.create_index("ix_autopark_vehicle",        "autopark_records", ["vehicle_id"])
    op.create_index("ix_autopark_customer",       "autopark_records", ["customer_id"])


def downgrade() -> None:
    # Drop in reverse dependency order
    op.drop_table("autopark_records")
    op.drop_table("vehicles")
    op.drop_table("budget_lines")
    op.drop_table("receivable_payments")
    op.drop_table("receivables")
    op.drop_table("debt_payments")
    op.drop_table("debts")
    op.drop_table("finance_expenses")
    op.drop_table("income")
    op.drop_table("money_accounts")
    op.drop_table("locations")
    op.drop_table("container_shipments")
    op.drop_table("containers")
