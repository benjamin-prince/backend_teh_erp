"""
TEHTEK — Seed ERP Roles & Permissions
Run once: docker exec tehtek_backend python seed_roles.py

Creates:
  1. All permission keys in the permissions table
  2. 7 predefined roles with the right permission sets
"""
import sys
import os
sys.path.insert(0, "/app")

from app.core.database import SessionLocal
from app.modules.users.models import Permission, Role, RolePermission
from app.modules.companies.models import Company

# ── All permissions ───────────────────────────────────────────────────────────

ALL_PERMISSIONS = [
    # Users
    ("users:create",          "users",    "Create new users"),
    ("users:read",            "users",    "View users"),
    ("users:update",          "users",    "Edit users"),
    ("users:delete",          "users",    "Delete users"),
    ("roles:manage",          "users",    "Manage roles and permissions"),
    ("audit:read",            "users",    "View audit logs"),
    # Customers
    ("customers:create",      "customers","Create customers"),
    ("customers:read",        "customers","View customers"),
    ("customers:update",      "customers","Edit customers"),
    ("customers:delete",      "customers","Delete customers"),
    ("customers:kyc_verify",  "customers","Verify customer KYC"),
    ("customers:blacklist",   "customers","Blacklist customers"),
    ("customers:vip_grant",   "customers","Grant VIP status"),
    # Cargo & Shipments
    ("cargo:create",          "cargo",    "Create shipments"),
    ("cargo:read",            "cargo",    "View shipments"),
    ("cargo:update",          "cargo",    "Edit shipments"),
    ("cargo:tracking_update", "cargo",    "Update tracking checkpoints"),
    ("cargo:bags",            "cargo",    "Manage bags"),
    ("cargo:travelers",       "cargo",    "Manage travelers"),
    # Orders
    ("orders:create",         "orders",   "Create orders"),
    ("orders:read",           "orders",   "View orders"),
    ("orders:update",         "orders",   "Edit orders"),
    ("orders:approve",        "orders",   "Approve orders"),
    # Finance
    ("finance:invoices",      "finance",  "View and create invoices"),
    ("finance:payments",      "finance",  "Record payments"),
    ("finance:cancel_invoice","finance",  "Cancel invoices"),
    ("finance:cash_sessions", "finance",  "Manage cash sessions"),
    ("finance:expenses",      "finance",  "View and record expenses"),
    ("finance:income",        "finance",  "View and record income"),
    ("finance:accounts",      "finance",  "View money accounts"),
    ("finance:receivables",   "finance",  "Manage receivables"),
    ("finance:debt",          "finance",  "Manage debts"),
    ("finance:locations",     "finance",  "Manage locations"),
    ("finance:budget",        "finance",  "Manage budget"),
    ("finance:summary",       "finance",  "View finance summary/reports"),
    # POS
    ("pos:cash_session",      "pos",      "Open/close cash sessions"),
    # Stock
    ("stock:read",            "stock",    "View stock"),
    ("stock:adjust",          "stock",    "Adjust stock levels"),
    ("stock:receive",         "stock",    "Receive stock"),
    # Services
    ("it_services:create",    "services", "Create IT/security projects"),
    ("it_services:read",      "services", "View IT/security projects"),
    ("it_services:update",    "services", "Edit IT/security projects"),
    ("solar:create",          "services", "Create solar projects"),
    ("solar:read",            "services", "View solar projects"),
    ("solar:update",          "services", "Edit solar projects"),
    # Commissions
    ("commissions:read",      "commissions","View commissions"),
    ("commissions:manage",    "commissions","Manage commissions"),
    ("commissions:approve",   "commissions","Approve commission payouts"),
    # Other
    ("approvals:read",        "approvals","View approval queue"),
    ("approvals:approve",     "approvals","Approve/reject actions"),
    ("exceptions:read",       "exceptions","View exceptions"),
    ("exceptions:resolve",    "exceptions","Resolve exceptions"),
    ("procurement:create",    "procurement","Create purchase orders"),
    ("procurement:read",      "procurement","View procurement"),
    ("settings:manage",       "settings", "Manage system settings"),
]

# ── Role definitions ──────────────────────────────────────────────────────────

ROLES = {
    "Super Admin": {
        "description": "Full access to everything — Founder/CTO only",
        "permissions": [p[0] for p in ALL_PERMISSIONS],  # all
    },
    "General Manager": {
        "description": "Full operational view, approvals, staff supervision",
        "permissions": [
            "users:read","customers:read","customers:update","customers:kyc_verify",
            "cargo:create","cargo:read","cargo:update","cargo:tracking_update","cargo:bags",
            "orders:create","orders:read","orders:update","orders:approve",
            "finance:invoices","finance:payments","finance:expenses","finance:income",
            "finance:accounts","finance:receivables","finance:debt","finance:summary",
            "finance:budget","finance:locations",
            "stock:read","stock:adjust","stock:receive",
            "it_services:create","it_services:read","it_services:update",
            "solar:create","solar:read","solar:update",
            "commissions:read","commissions:manage","commissions:approve",
            "approvals:read","approvals:approve","exceptions:read","exceptions:resolve",
            "procurement:read","procurement:create","audit:read",
        ],
    },
    "Finance Manager": {
        "description": "Full finance access — invoices, payments, reports, debt, receivables",
        "permissions": [
            "finance:invoices","finance:payments","finance:cancel_invoice",
            "finance:cash_sessions","finance:expenses","finance:income",
            "finance:accounts","finance:receivables","finance:debt",
            "finance:locations","finance:budget","finance:summary",
            "customers:read","orders:read","audit:read",
            "commissions:read","commissions:approve",
            "approvals:read","approvals:approve",
        ],
    },
    "Finance Officer": {
        "description": "Record payments, manage income/expenses, view reports",
        "permissions": [
            "finance:invoices","finance:payments","finance:expenses","finance:income",
            "finance:accounts","finance:receivables","finance:debt","finance:summary",
            "customers:read","orders:read",
        ],
    },
    "Cargo Officer": {
        "description": "Manage shipments, containers, tracking, orders",
        "permissions": [
            "cargo:create","cargo:read","cargo:update","cargo:tracking_update",
            "cargo:bags","cargo:travelers",
            "orders:create","orders:read","orders:update",
            "customers:read","customers:create",
            "finance:invoices","finance:payments","stock:read",
        ],
    },
    "IT & Services Officer": {
        "description": "Manage IT/security and solar service projects",
        "permissions": [
            "it_services:create","it_services:read","it_services:update",
            "solar:create","solar:read","solar:update",
            "customers:read","customers:create","customers:update",
            "finance:invoices","finance:payments","orders:read",
        ],
    },
    "Cashier / POS": {
        "description": "POS operations — cash sessions, payments, receipts",
        "permissions": [
            "pos:cash_session","finance:payments","finance:invoices",
            "customers:read","orders:read","stock:read",
        ],
    },
    "Viewer": {
        "description": "Read-only access to core operational data",
        "permissions": [
            "cargo:read","orders:read","customers:read",
            "finance:invoices","stock:read","it_services:read","solar:read",
        ],
    },
}

# ── Seed function ─────────────────────────────────────────────────────────────

def seed():
    db = SessionLocal()
    try:
        # Get company id
        company = db.query(Company).filter_by(code="TEHTEK").first()
        if not company:
            company = db.query(Company).first()
        if not company:
            print("ERROR: No company found. Run app first.")
            return
        company_id = company.id
        print(f"Seeding for company_id={company_id} ({company.name})")

        # 1. Seed permissions
        perm_map = {}
        created_perms = 0
        for key, module, desc in ALL_PERMISSIONS:
            existing = db.query(Permission).filter_by(key=key).first()
            if not existing:
                p = Permission(key=key, module=module, description=desc)
                db.add(p)
                db.flush()
                perm_map[key] = p.id
                created_perms += 1
            else:
                perm_map[key] = existing.id
        print(f"  Permissions: {created_perms} created, {len(ALL_PERMISSIONS)-created_perms} existing")

        # 2. Seed roles
        created_roles = 0
        for role_name, config in ROLES.items():
            existing_role = db.query(Role).filter_by(
                company_id=company_id, name=role_name, deleted_at=None
            ).first()

            if not existing_role:
                role = Role(
                    company_id=company_id,
                    name=role_name,
                    description=config["description"],
                    is_system=True,
                )
                db.add(role)
                db.flush()
                role_id = role.id
                created_roles += 1
            else:
                role_id = existing_role.id
                print(f"  Role '{role_name}' already exists (id={role_id}) — syncing permissions")

            # 3. Assign permissions to role
            added_perms = 0
            for perm_key in config["permissions"]:
                perm_id = perm_map.get(perm_key)
                if not perm_id:
                    print(f"    WARNING: permission '{perm_key}' not found")
                    continue
                existing_rp = db.query(RolePermission).filter_by(
                    role_id=role_id, permission_id=perm_id
                ).first()
                if not existing_rp:
                    rp = RolePermission(role_id=role_id, permission_id=perm_id)
                    db.add(rp)
                    added_perms += 1
            print(f"  Role '{role_name}' (id={role_id}): +{added_perms} permissions")

        db.commit()
        print(f"\nDone. {created_roles} roles created.")

        # Print summary
        print("\n── Roles in DB ──")
        for r in db.query(Role).filter_by(company_id=company_id, deleted_at=None).all():
            count = db.query(RolePermission).filter_by(role_id=r.id).count()
            print(f"  [{r.id}] {r.name} — {count} permissions")

    except Exception as e:
        db.rollback()
        print(f"ERROR: {e}")
        raise
    finally:
        db.close()

if __name__ == "__main__":
    seed()
