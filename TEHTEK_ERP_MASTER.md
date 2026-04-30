# TEHTEK ERP — Master Project Context
# Version: 1.0 | April 2026
# Owner: Benjamin Boule Fogang
# Purpose: Paste into Claude at the start of every session.
# End every session with: "Update the master file."

---

## 🎯 STRATEGIC PRINCIPLE

> **Revenue First → Control Second → Scale Third**
> Build software for where cash ALREADY enters the account.
> Current focus: **TEHTEK OPERATING CORE** = Retail + Cargo + Infrastructure Services

**Operational flow:**
Procurement → Stock → Order → Invoice → Cargo/Service → Delivery → Payment → Customer

---

## 👤 OWNER & BOARD

| Role | Person |
|---|---|
| Founder / Super Admin | Benjamin Boule Fogang |
| CEO | Group Operations |
| COO | Daily execution |
| CFO | Finance + strategy |
| CTO | ERP + systems + AI |
| CLO | Legal + compliance |
| CCO | Sales + growth |
| CHRO | People + hiring |

- Admin email: admin@tehtek.com
- Docker Hub: boulaz2002

---

## 🏢 ACTIVE CASH FLOW BUSINESSES (Build These First)

### 1. Retail Store ✅ ACTIVE
Electronics, Computers, Accessories, General products, B2B supply

### 2. Cargo & Shipping ✅ ACTIVE
Air Express (traveler model — checked baggage), Air Cargo, Sea Freight
Routes: USA / Europe / China ↔ Cameroon + local delivery

### 3. Infrastructure, Security & Energy Systems ✅ ACTIVE
- **IT Infrastructure:** Server, network, router, firewall, WiFi, cloud, backup, cybersecurity
- **Security Systems:** CCTV, access control, biometric, smart locks, alarms, electric fence, fire systems
- **Smart Systems:** Smart home, smart office, hotel access, Airbnb locks, IoT, building automation
- **Solar & Energy:** Solar installation, battery backup, inverter, UPS, hybrid systems, energy audits, AMC

---

## 🏢 FULL GROUP STRUCTURE

| # | Company | Status |
|---|---|---|
| 1 | TEHTEK IT Services | Parent / Technology |
| 2 | Retail Store | ✅ Active |
| 3 | Cargo & Shipping | ✅ Active |
| 4 | Local Delivery | ✅ Active |
| 5 | Infrastructure, Security & Energy | ✅ Active |
| 6 | Car Division | Future |
| 7 | Real Estate | Future |
| 8 | Finance & Admin | Internal |
| 9 | Executive Management | Group oversight |
| 10 | TehMoney | Future |

| Branch | Location |
|---|---|
| Yaoundé HQ | Cameroon |
| Douala Cargo Hub | Cameroon |
| China Procurement Office | China |
| USA Warehouse | USA |
| Europe Partner Hub | Europe |

---

## 🖥️ INFRASTRUCTURE

### ⚠️ TWO BACKENDS EXIST — Understand the difference

#### OLD Backend — Currently Live on VPS 1
- **URL pattern:** `https://api.tehtek.com/api/api/v1/...` (double /api/)
- **Server path:** /opt/tehtek_erp_backend
- **Status:** Running in production, serving the current frontend
- **Has:** users, auth, roles, referrals (old commission system)
- **Will be:** replaced by the new backend when it is ready and tested

#### NEW Backend — Under Development (Not Yet Deployed)
- **URL pattern:** `https://api.tehtek.com/api/v1/...` (clean, no double /api/)
- **Status:** Being built from scratch — NOT deployed to any server yet
- **Has built:** companies module (Week 1) + customers module (Week 2)
- **Stack:** FastAPI + SQLAlchemy 2.0 sync + PostgreSQL 16 + Docker + Caddy
- **⚠️ Auth note:** companies and customers routers currently use `_PLACEHOLDER_ACTOR`.
  These routers MUST have `dependencies=[Depends(get_current_user)]` added the moment
  the users module is built. No module ships to production without auth on its router.

#### Frontend (VPS 2) — Currently Pointing to OLD Backend
- **Staff app:** app.tehtek.com
- **Customer portal:** customer.tehtek.com (planned — separate app, Week 10)
- **Docker image:** boulaz2002/tehtek-frontend:latest
- Will be updated to point to new backend when it is deployed and stable

### Local Dev Machine
- OS: Ubuntu (benjamin@benjamin-Lenovo-Slim-7)
- Frontend: ~/teh_frontend | Node: v20 (nvm)
- New backend: local development folder

---

## 🔗 USER ↔ CUSTOMER ARCHITECTURE

```
users table     → anyone who can LOG IN to any TEHTEK application
customers table → anyone who does BUSINESS with TEHTEK

customers.user_id → nullable FK to users
  NULL = staff-managed customer (no portal login — most walk-in/cargo customers)
  SET  = customer has a portal login account on customer.tehtek.com
```

| Person | user record? | customer record? |
|---|---|---|
| Staff member (cargo agent, cashier) | ✅ Yes | ❌ No |
| Walk-in retail buyer (no portal) | ❌ No | ✅ Yes |
| Shipping customer with portal login | ✅ Yes | ✅ Yes — linked via user_id |
| Commission partner with portal | ✅ Yes | ❌ No (separate relationship) |
| Super Admin (Benjamin) | ✅ Yes | ❌ No |

---

## 🛠️ TECH STACK

### New Backend (being built)
- Python 3.12 / FastAPI — SYNC only (`Session`, NEVER `AsyncSession`)
- SQLAlchemy 2.0 sync | PostgreSQL 16 | JWT | bcrypt | pydantic-settings
- All enums in: `app/core/enums.py` — single source of truth
- Module pattern: `app/modules/{name}/models+schemas+controller+router`

### Frontend
- Next.js 14 App Router / TypeScript
- Tailwind CSS v3 (NOT v4) | lucide-react | clsx
- `output: standalone` (required for Docker)
- JWT stored in localStorage → sent as Bearer token

---

## 📁 NEW BACKEND — BUILD STATUS

```
tehtek_backend/
├── app/
│   ├── main.py                          ✅ built — no users dependency
│   │                                    ⚠️ ADD: startup route audit on boot (ACC-007)
│   ├── core/
│   │   ├── config.py                    ✅ built — minimal, no admin fields
│   │   ├── database.py                  ✅ built — sync engine + SessionLocal
│   │   ├── enums.py                     ✅ built — ALL enums, single source
│   │   ├── security.py                  ✅ built — JWT + bcrypt helpers
│   │   │                                ⚠️ ADD: refresh token rotation + replay detection (UR-008, UR-009)
│   │   └── dependencies.py              ❌ NEXT — get_current_user, check_permission,
│   │                                              company_scope enforcement
│   └── modules/
│       ├── companies/                   ✅ WEEK 1 — COMPLETE
│       │   ├── models.py                (sequence_registry, companies, branches,
│       │   │                             departments, teams, permission_flags,
│       │   │                             approval_workflows)
│       │   ├── schemas.py
│       │   ├── controller.py            (all 12 sequence generators)
│       │   ├── router.py                (25 endpoints)
│       │   │                            ⚠️ ADD auth dependency after users module built
│       │   └── seeds.py                 (sequences seeded first on every startup)
│       │
│       ├── customers/                   ✅ WEEK 2 — COMPLETE
│       │   ├── models.py                (Customer, CustomerKYC, CustomerContact,
│       │   │                             CustomerNote, Supplier, SupplierContact)
│       │   ├── schemas.py
│       │   ├── controller.py            (CR-001→CR-005 enforced,
│       │   │                             validate_for_transaction())
│       │   └── router.py                (25+ endpoints)
│       │                                ⚠️ ADD auth dependency after users module built
│       │   NOTE: customers.user_id FK added after users module is built
│       │
│       ├── users/                       ❌ BUILD NEXT (before cargo/orders)
│       │   (User, Role, Permission, UserRole, RolePermission, UserAuditLog)
│       │   (auth endpoints, JWT middleware, dependencies.py)
│       │   (refresh_tokens table: token_hash, user_id, is_used, expires_at, ip_address)
│       │   IMPORTANT: After users built → immediately retrofit auth on companies + customers routers
│       │
│       ├── cargo/                       ❌ WEEK 4
│       │   (shipments, packages, tracking_events, bags, bag_packages,
│       │    travelers, carrier_assignments, pickup_requests)
│       │
│       ├── stock/                       ❌ WEEK 4
│       │   (products, warehouses, stock_items, stock_movements, reservations)
│       │
│       ├── orders/                      ❌ WEEK 5
│       │   (orders, order_items, exceptions)
│       │
│       ├── infrastructure_services/     ❌ WEEK 5
│       │   (service_tickets, service_contracts, service_visits, client_assets,
│       │    technician_assignments, solar_projects, installed_systems,
│       │    warranty_records, maintenance_schedules, security_devices)
│       │
│       ├── commissions/                 ❌ WEEK 5
│       │   (commission_partners, commission_leads, commission_rules,
│       │    commission_records, commission_payouts, commission_disputes)
│       │
│       ├── finance/                     ❌ WEEK 9
│       │   (invoices, payments, cash_sessions)
│       │
│       ├── notifications/               ❌ WEEK 12
│       ├── analytics/                   ❌ WEEK 13
│       ├── hr/                          ❌ after go-live
│       ├── cars/                        ❌ after go-live
│       ├── realestate/                  ❌ after go-live
│       └── tehmoney/                    ❌ after go-live
│
├── requirements.txt                     ✅
├── Dockerfile                           ✅
└── .env.example                         ✅ (never commit .env)
```

---

## 🗄️ DATABASE TABLES

### ✅ Built in New Backend

| Table | Module | Description |
|---|---|---|
| sequence_registry | companies | Atomic number generation — seeded FIRST |
| companies | companies | Multi-company architecture |
| branches | companies | Physical locations per company |
| departments | companies | Per-company divisions |
| teams | companies | Sub-groups within departments |
| permission_flags | companies | Per-user granular permission overrides |
| approval_workflows | companies | Multi-step approval engine |
| customers | customers | All customer types + VIP + blacklist + balance |
| customer_kyc | customers | KYC documents + review workflow |
| customer_contacts | customers | Multiple contacts per customer |
| customer_notes | customers | Internal staff notes (never shown to customer) |
| suppliers | customers | Supplier profiles |
| supplier_contacts | customers | Multiple contacts per supplier |

### ❌ To Be Built — In Order

| Table | Module | Week |
|---|---|---|
| users | users | **NEXT** |
| roles | users | **NEXT** |
| permissions | users | **NEXT** |
| role_permissions | users | **NEXT** |
| user_roles | users | **NEXT** |
| user_audit_logs | users | **NEXT** |
| refresh_tokens | users | **NEXT** ← NEW: token_hash, user_id, is_used, expires_at, ip_address |
| *(add user_id FK to customers)* | customers | after users |
| *(add auth dependency to companies router)* | companies | after users |
| *(add auth dependency to customers router)* | customers | after users |
| shipments | cargo | 4 |
| packages | cargo | 4 |
| tracking_events | cargo | 4 |
| bags | cargo | 4 |
| bag_packages | cargo | 4 |
| travelers | cargo | 4 |
| carrier_assignments | cargo | 4 |
| pickup_requests | cargo | 4 |
| products | stock | 4 |
| warehouses | stock | 4 |
| stock_items | stock | 4 |
| stock_movements | stock | 4 |
| reservations | stock | 4 |
| orders | orders | 5 |
| order_items | orders | 5 |
| exceptions | orders | 5 |
| service_tickets | infra | 5 |
| service_contracts | infra | 5 |
| service_visits | infra | 5 |
| client_assets | infra | 5 |
| technician_assignments | infra | 5 |
| solar_projects | infra | 5 |
| installed_systems | infra | 5 |
| warranty_records | infra | 5 |
| maintenance_schedules | infra | 5 |
| security_devices | infra | 5 |
| commission_partners | commissions | 5 |
| commission_leads | commissions | 5 |
| commission_rules | commissions | 5 |
| commission_records | commissions | 5 |
| commission_payouts | commissions | 5 |
| commission_disputes | commissions | 5 |
| invoices | finance | 9 |
| payments | finance | 9 |
| cash_sessions | finance | 9 |
| notifications | notifications | 12 |
| employees | hr | after go-live |
| vehicles | cars | after go-live |
| properties | realestate | after go-live |
| wallets | tehmoney | after go-live |

### User model — exact fields (NEVER deviate)
```python
id, email, phone, hashed_password,
first_name, last_name,        # full_name = @property, NEVER a DB column
user_type, status,            # is_active = @property, NEVER a DB column
company_id, branch_id,        # multi-company scoping — in JWT token
department, job_title, avatar_url,
is_superadmin,
last_login, failed_login_count, locked_until,
mfa_enabled, mfa_secret,
reset_token, reset_token_expiry,
created_by, created_at, updated_at, deleted_at
```

### Refresh Token model — exact fields
```python
id, token_hash,               # store hash of token, never plaintext
user_id,                      # FK to users
is_used,                      # bool — True after first use (replay detection)
ip_address,                   # IP that created this token
user_agent,                   # browser/app that created this token
expires_at,                   # 7 days staff / 3 days portal
created_at, revoked_at        # revoked_at set when all sessions invalidated
```

### Customer model — key additional field (after users built)
```python
user_id   # nullable FK → users.id
          # NULL = staff-managed (no portal login)
          # SET  = has portal login on customer.tehtek.com
```

---

## 📋 OPERATIONAL DOCUMENTS (All Current)

| Document | File | Version | Status |
|---|---|---|---|
| Master Context | TEHTEK_ERP_MASTER.md | 2.2 | ✅ Current |
| Master Enums | TEHTEK_ENUMS.md | 1.4 | ✅ Current |
| Business Rules | TEHTEK_RULES.md | 1.4 | ✅ Current |
| Exception Matrix | TEHTEK_EXCEPTIONS.md | 1.3 | ✅ Current |
| Prohibited Items | TEHTEK_PROHIBITED_ITEMS.md | 1.0 | ✅ Current |
| Dashboard Access Matrix | TEHTEK_ACCESS_MATRIX.md | 1.1 | ✅ Current |

### Critical Number Formats (SEQ-004)
```
Tracking:   TRK-[ROUTE]-[YEAR]-[000000]    e.g. TRK-CNACM-2026-000142
Invoice:    INV-[YEAR]-[MM]-[000000]        e.g. INV-2026-04-000089
Customer:   CUS-[000000]                    e.g. CUS-000034
Order:      ORD-[YEAR]-[000000]             e.g. ORD-2026-000201
Receipt:    RCP-[YEAR]-[MM]-[000000]        e.g. RCP-2026-04-000055
Pickup:     PKP-[YEAR]-[000000]             e.g. PKP-2026-000018
Bag:        BAG-[TYPE]-[YEAR]-[0000]        e.g. BAG-AIR-2026-0012
Service:    SVC-[YEAR]-[000000]             e.g. SVC-2026-000045
Project:    PRJ-[YEAR]-[000000]             e.g. PRJ-2026-000007
Contract:   CNT-[YEAR]-[000000]             e.g. CNT-2026-000003
Commission: COM-[YEAR]-[000000]             e.g. COM-2026-000019
Payout:     PAY-[YEAR]-[MM]-[000000]        e.g. PAY-2026-04-000008
```

### Top 15 Non-Negotiable Rules
```
SR-002: Every shipment gets a tracking number via sequence_registry — immutable
SR-003: No shipment released if invoice unpaid — DB + backend + frontend + audit
SR-008: Customer accepts liability declaration before any shipment is confirmed
SR-009: Prohibited item screening mandatory at every warehouse intake
ST-001: Free storage 3 days standard / 7 days VIP — then fees apply
ST-003: Day 28 after arrival → abandoned → Owner decision mandatory
STK-005: Unpaid stock reservations expire automatically after 24 hours
STK-007: Special orders require minimum 50% deposit before procurement starts
ISR-003: Completed service job requires signed customer acceptance — no exceptions
ISR-004: Every completed service job generates a service report
ESR-001: No solar project starts without a completed site survey
ESR-003: No solar installation without signed quotation + minimum 50% deposit
COM-002: Commission status → payable only after TEHTEK receives payment
COM-007: No commission payout before TEHTEK receives money — Founder only can override
CASH-002: Every cashier closes daily cash session before end of shift
ACC-007: No API router without authentication — every router needs get_current_user dependency ★ NEW
```

---

## 📅 90-DAY EXECUTION PLAN (Corrected Build Order)

### ✅ WEEK 0 — PRE-BUILD
Locked all operational documents · Defined business structure and roles
Decided: customer portal = customer.tehtek.com (separate app, separate auth)
WhatsApp Business API: start Meta verification immediately

### ✅ WEEK 1 — CORE FOUNDATION (New Backend)
Built: sequence_registry (first) · companies · branches · departments · teams
       permission_flags · approval_workflows · seeds (auto-run on startup)
Endpoints: 25 endpoints live
⚠️ Note: companies router has no auth yet — will be retrofitted after users module

### ✅ WEEK 2 — CRM (New Backend)
Built: customers · customer_kyc · customer_contacts · customer_notes
       suppliers · supplier_contacts
Business rules enforced: CR-001 to CR-005
Endpoints: 25+ endpoints live
NOTE: customers.user_id FK will be added after users module is built
⚠️ Note: customers router has no auth yet — will be retrofitted after users module

### ❌ WEEK 3 — USERS MODULE (Build Next — Required for Security)
Build: users · roles · permissions · role_permissions · user_roles
       user_audit_logs · refresh_tokens
       auth endpoints (login, refresh, logout, /me, password reset)
       dependencies.py (get_current_user, check_permission, company_scope)
AUTH RETROFIT (mandatory immediately after users module works):
  → Add `dependencies=[Depends(get_current_user)]` to companies router
  → Add `dependencies=[Depends(get_current_user)]` to customers router
  → Add startup route audit to main.py (logs all routes missing auth dependency)
  → Add user_id nullable FK to customers table

### ❌ WEEK 4 — CARGO + STOCK MODELS
Build: shipments · packages · tracking_events · bags · bag_packages
       travelers · carrier_assignments · pickup_requests
       products · warehouses · stock_items · stock_movements · reservations
All new routers: `dependencies=[Depends(get_current_user)]` from day one

### ❌ WEEK 5 — TRANSACTION APIs + INFRASTRUCTURE + COMMISSIONS
Build: All cargo APIs · All stock/order APIs
       service_tickets · service_contracts · service_visits · client_assets
       technician_assignments · solar_projects · installed_systems
       warranty_records · maintenance_schedules · security_devices
       commission_partners · commission_leads · commission_rules
       commission_records · commission_payouts · commission_disputes
All new routers: `dependencies=[Depends(get_current_user)]` from day one

### ❌ WEEK 6-7 — FRONTEND — STAFF DASHBOARDS
Build: Staff app (app.tehtek.com) connected to new backend
       Cargo dashboard · Retail dashboard · Infrastructure dashboard
       Customer management · Company/branch management
       Commission management UI

### ❌ WEEK 8 — FRONTEND — OPERATIONAL PAGES
Build: Shipment creation · Tracking pages · Bag/Traveler management
       Product catalog · Order creation · Service ticket creation
       Pickup scheduling · Warehouse intake · Dispatch planning

### ❌ WEEK 9 — MONEY CONTROL
Build: invoices · payments · cash_sessions
       Auto invoice generation (from shipments, orders, services)
       Payment proof upload · Cashier cash sessions
       Storage fee invoicing · Commission payout approvals
       RULE ENFORCED: SR-003 (no release if unpaid) + COM-007 (no payout before receipt)

### ❌ WEEK 10 — CUSTOMER PORTAL (customer.tehtek.com)
Build: Separate Next.js app · Separate auth (customer login via users.user_id)
       Place order · Track shipment · View invoices · Upload payment proof
       View service tickets · Commission partner section
       Separate auth middleware with 30-min token lifetime + 3-day refresh tokens

### ❌ WEEK 11 — PUBLIC EXPERIENCE
Build: Public tracking page (DHL-style, no login required)
       Public product catalog · Quotation request form
       NOTE: These are the ONLY non-auth routes beyond /auth/* and /health

### ❌ WEEK 12 — TRUST ENGINE
Build: WhatsApp Business API integration · SMS notifications
       Email invoices and reminders · Delivery confirmations
       Overdue reminders · Storage fee warnings

### ❌ WEEK 13 — GO LIVE PREPARATION
Hardening · Security audit · Access review · Backup validation
SOP documentation finalized · Staff training · Go live checklist
Run startup route audit — confirm zero unprotected routes outside whitelist
Switch frontend from old backend URL to new backend URL

### ❌ DO NOT BUILD UNTIL AFTER WEEK 13
Payroll · Full HR · Car Division · Real Estate · TehMoney · AI dashboards
Advanced analytics · Full BI engine

---

## 🔐 ROLES (Full List)

### System-Wide
Super Admin · Group Admin · CFO · Finance Manager · Finance Officer
Accountant · Cashier · Auditor

### Cargo
Shipping Manager · Warehouse Officer · Pickup Agent · Driver/Rider
Customs Officer · International Coordinator · Cargo Sales Agent · Dispatch Officer

### Retail
Store Manager · Sales Agent · Cashier (Retail POS) · Inventory Officer
Procurement Officer · Purchase Officer

### Infrastructure, Security & Solar
Infrastructure Services Manager · Technical Sales Engineer · Network Engineer
System Administrator · Field Technician · CCTV Technician
Security Systems Engineer · Access Control Specialist · Solar Engineer
Electrical Engineer · Site Survey Technician · Energy Consultant
Installation Technician · Maintenance Coordinator · Backup & Recovery Specialist
Helpdesk Agent · Safety Compliance Officer · Project Supervisor · Smart Building Technician

### CRM & Support
Customer Support Agent · VIP Client Manager · Corporate Account Manager
Supplier Relationship Officer

### Commission
Commission Manager · Commission Partner (external — portal access only)

---

## 🔌 API ENDPOINTS

### NEW Backend (under development — not yet deployed)
Base URL: `https://api.tehtek.com/api/v1`

#### ✅ Companies Module (Week 1)
```
GET    /api/v1/sequences
POST   /api/v1/companies         GET /api/v1/companies
GET    /api/v1/companies/{id}    PATCH /api/v1/companies/{id}    DELETE /api/v1/companies/{id}
POST   /api/v1/branches          GET /api/v1/companies/{id}/branches
GET    /api/v1/branches/{id}     PATCH /api/v1/branches/{id}
POST   /api/v1/departments       GET /api/v1/companies/{id}/departments
GET    /api/v1/departments/{id}  PATCH /api/v1/departments/{id}
POST   /api/v1/teams             GET /api/v1/departments/{id}/teams
PATCH  /api/v1/teams/{id}
POST   /api/v1/permission-flags
GET    /api/v1/users/{id}/permission-flags
DELETE /api/v1/users/{id}/permission-flags/{flag}
POST   /api/v1/approvals         GET /api/v1/approvals
GET    /api/v1/approvals/{id}
POST   /api/v1/approvals/{id}/decide
POST   /api/v1/approvals/{id}/escalate
```
⚠️ All above to have `dependencies=[Depends(get_current_user)]` after users module.

#### ✅ Customers Module (Week 2)
```
POST   /api/v1/customers                      GET /api/v1/customers
GET    /api/v1/customers/{id}                 PATCH /api/v1/customers/{id}
DELETE /api/v1/customers/{id}
GET    /api/v1/customers/by-code/{code}
GET    /api/v1/customers/{id}/validate
POST   /api/v1/customers/{id}/blacklist
POST   /api/v1/customers/{id}/remove-blacklist
POST   /api/v1/customers/{id}/grant-vip
POST   /api/v1/customers/{id}/revoke-vip
POST   /api/v1/customers/{id}/kyc             GET /api/v1/customers/{id}/kyc
POST   /api/v1/kyc/{id}/review
POST   /api/v1/customers/{id}/contacts        GET /api/v1/customers/{id}/contacts
DELETE /api/v1/customers/{id}/contacts/{id}
POST   /api/v1/customers/{id}/notes           GET /api/v1/customers/{id}/notes
POST   /api/v1/suppliers                      GET /api/v1/suppliers
GET    /api/v1/suppliers/{id}                 PATCH /api/v1/suppliers/{id}
DELETE /api/v1/suppliers/{id}
POST   /api/v1/suppliers/{id}/contacts
```
⚠️ All above to have `dependencies=[Depends(get_current_user)]` after users module.

#### ❌ Users Module (NEXT — Week 3)
```
# Public routes (no auth required — ACC-008 whitelist)
POST   /api/v1/auth/login
POST   /api/v1/auth/refresh
POST   /api/v1/auth/password-reset/request
POST   /api/v1/auth/password-reset/confirm

# Protected routes (require JWT)
POST   /api/v1/auth/logout
GET    /api/v1/auth/me
PATCH  /api/v1/auth/me/password
POST   /api/v1/users                GET /api/v1/users
GET    /api/v1/users/{id}           PATCH /api/v1/users/{id}
DELETE /api/v1/users/{id}
PUT    /api/v1/users/{id}/roles
GET    /api/v1/users/{id}/audit-log
POST   /api/v1/roles                GET /api/v1/roles
DELETE /api/v1/roles/{id}
```

#### Public endpoints (no auth — Week 11)
```
GET    /api/v1/tracking/{tracking_number}   ← read-only, no PII
GET    /api/v1/health
```

### OLD Backend (currently live)
Base URL: `https://api.tehtek.com/api/api/v1` (double /api/ — legacy)
Has: auth, users, roles, referrals (old system) — serving current frontend

---

## 🚀 DEPLOY WORKFLOW

### Old Backend update (VPS 1 — currently live)
```bash
cd /opt/tehtek_erp_backend
git pull origin main
docker compose restart backend
docker compose logs backend --tail 20
```

### Frontend update (local → Docker Hub → VPS 2)
```bash
# Build locally
cd ~/teh_frontend
docker build \
  --build-arg NEXT_PUBLIC_API_URL=https://api.tehtek.com/api/api/v1 \
  -t boulaz2002/tehtek-frontend:latest .
docker push boulaz2002/tehtek-frontend:latest

# On VPS 2
cd ~ && docker compose pull && docker compose up -d
```

### New Backend (when ready to deploy to VPS 1)
```bash
# Before deploying: verify startup route audit shows zero unprotected routes
# Stop old backend, deploy new backend
# Change NEXT_PUBLIC_API_URL to https://api.tehtek.com/api/v1 (no double /api/)
# Update frontend build and redeploy
```

---

## 📌 CLAUDE RULES (Read Every Session)

### Architecture
1. Backend SYNC SQLAlchemy — `Session`, NEVER `AsyncSession`
2. NEVER use `username`, `full_name`, `is_active`, `is_verified`, `role` as DB columns
3. `full_name` and `is_active` are `@property` — computed, NEVER stored in DB
4. All enums live in `app/core/enums.py` — never define enums in any other file
5. All secrets in `.env` — never hardcoded anywhere
6. Tailwind v3 ONLY — never v4
7. Next.js 14 App Router — `"use client"` where needed
8. `output: standalone` in next.config.ts — required for Docker

### Data & Security
9. Every DB query scoped by `company_id` + `branch_id` (except Super Admin)
10. `customers.user_id` is nullable FK — NULL = staff-managed, SET = has portal login
11. User model has `company_id` + `branch_id` — included in JWT token payload
12. sequence_registry is always seeded FIRST on startup — before any other seed
13. Soft delete only — `deleted_at` on all critical tables, filter `WHERE deleted_at IS NULL`

### Documents — Check Before Coding
14. Check `TEHTEK_ENUMS.md` before adding any new enum to code
15. Check `TEHTEK_RULES.md` before implementing any business logic
16. Check `TEHTEK_EXCEPTIONS.md` before building any exception handling
17. Check `TEHTEK_PROHIBITED_ITEMS.md` for cargo intake validation logic
18. Check `TEHTEK_ACCESS_MATRIX.md` before building any UI page permissions

### Business Rules
19. SR-003: No shipment released if invoice unpaid — enforce at DB + backend + frontend + audit
20. Air Express = traveler model (checked baggage) — never airline cargo
21. Bags/cartons/containers group packages — always linked to a carrier
22. COM-007: No commission payout before TEHTEK receives money — Founder only for exception
23. One staff dashboard shell — permission-based sidebar — never hardcode by role label
24. Customer portal = separate app on customer.tehtek.com — NEVER mix with staff app
25. Infrastructure Services module covers IT + Security + Smart Systems + Solar/Energy together

### Build Order
26. Users module must be built before: cargo, orders, infrastructure, commissions, finance
27. After users module: add `user_id` nullable FK to customers table
28. New backend URL = `/api/v1/...` — old backend URL = `/api/api/v1/...`
29. Frontend stays on old backend URL until new backend is deployed and fully tested
30. `_PLACEHOLDER_ACTOR` in current controllers will be replaced with real auth once users module is built

### Authentication — No Router Without Auth ★ NEW
31. Every `APIRouter` is instantiated with `dependencies=[Depends(get_current_user)]`.
    NEVER apply auth per-endpoint. Always at router level. No exceptions.
    ```python
    router = APIRouter(prefix="/resource", dependencies=[Depends(get_current_user)])
    ```
32. The ONLY routes without auth are the public whitelist in ACC-008:
    login, refresh, password-reset/request, password-reset/confirm, /health, and /tracking/{id}
33. Refresh tokens are single-use. Store `token_hash` (never plaintext). Mark `is_used=True`
    on first use. Presenting a used token → invalidate ALL sessions for that user → alert CTO.
34. On every app startup, log all routes missing `get_current_user` dependency.
    Any route outside the whitelist that appears in this log = critical bug, fix before deploy.

---

## 💬 HOW TO USE THIS FILE

**Start of session:**
> "Here is my TEHTEK ERP master context. Read it carefully.
> Today I want to build [X]. When we finish, give me the updated master file."

**End of session:**
> "Update the master file to reflect everything we built today."

```bash
git add TEHTEK_ERP_MASTER.md TEHTEK_ENUMS.md TEHTEK_RULES.md \
        TEHTEK_EXCEPTIONS.md TEHTEK_PROHIBITED_ITEMS.md TEHTEK_ACCESS_MATRIX.md
git commit -m "docs: v2.2 - auth rules, no router without auth, token rotation"
git push
```
