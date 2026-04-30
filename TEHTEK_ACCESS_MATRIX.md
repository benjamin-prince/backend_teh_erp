# TEHTEK — Dashboard Access Matrix
# Version: 1.2 | April 2026
# Owner: Benjamin Boule Fogang
# Purpose: Define who sees what in the staff app and customer portal.
# Reference: TEHTEK_RULES.md Section 15 (ACC-001 to ACC-008)
# Changelog v1.2: Added forced password change flow (UR-011). Token behaviour updated.
# Changelog v1.1: Added authentication requirements section, public route whitelist,
#                 ACC-007 and ACC-008 references, route audit guidance.

---

## CORE PRINCIPLES

1. One staff dashboard shell. Permission-based menus. Never hardcode visibility by role name.
2. Role → Role Permissions + Individual Permission Flags → Visible menu items and actions.
3. A user may have multiple roles. The union of all role permissions applies.
4. Permission flags can ADD capabilities a role does not have, or RESTRICT what a role grants.
5. Company and branch scope always applied — every query filtered by user.company_id + user.branch_id.
6. Super Admin is the ONLY role that bypasses company/branch scope.
7. Frontend visibility is NOT security. Backend must check permissions on every API call.
8. Triple enforcement: Frontend hides UI → Backend checks permission → Database enforces constraint → Audit logs attempt.
9. **No router without auth. Every endpoint requires JWT except the public whitelist.** ← NEW

---

## TWO SEPARATE APPLICATIONS

### Staff App — app.tehtek.com
Who uses it: Founder, all management, all staff, finance, cargo team,
retail team, infrastructure/solar/security team, support, procurement, commission managers.

### Customer Portal — customer.tehtek.com
Who uses it: Retail customers, shipping customers, corporate clients,
IT/solar service clients, VIP customers, commission partners (portal section).
Rule: Customer portal users see ONLY their own data. Never other customers. Never internal data.
Rule: Customer portal is a completely separate Next.js app with separate authentication.

---

## AUTHENTICATION REQUIREMENTS ★ NEW

### Rule: No router without auth (ACC-007)
Every API router in both the staff app backend and the customer portal backend must be
instantiated with the `get_current_user` dependency. There are NO unprotected routers
except those serving the public route whitelist below.

**Implementation pattern (FastAPI):**
```python
# CORRECT — auth applied at router level
router = APIRouter(
    prefix="/shipments",
    tags=["shipments"],
    dependencies=[Depends(get_current_user)]
)

# WRONG — never do this (easy to miss on new endpoints)
@router.get("/shipments/{id}")
async def get_shipment(id: int, current_user = Depends(get_current_user)):
    ...
```

**Startup route audit:**
On every app startup, `main.py` logs all registered routes that do NOT have the
`get_current_user` dependency. Any such route not in the whitelist below triggers
a WARNING in the logs and an alert to the CTO.

### Public Route Whitelist (no JWT required)

Staff Backend (api.tehtek.com/api/v1):
```
POST  /api/v1/auth/login
POST  /api/v1/auth/refresh
POST  /api/v1/auth/password-reset/request
POST  /api/v1/auth/password-reset/confirm
GET   /api/v1/health
```

Customer Portal Backend:
```
POST  /api/v1/portal/auth/login
POST  /api/v1/portal/auth/refresh
POST  /api/v1/portal/auth/password-reset/request
POST  /api/v1/portal/auth/password-reset/confirm
GET   /api/v1/tracking/{tracking_number}    ← read-only, no PII exposed
GET   /api/v1/health
```

Any new public route requires Owner approval, written justification, and audit log entry.

### Token Behaviour
- Staff access token lifetime: 60 minutes
- Customer portal access token lifetime: 30 minutes
- Refresh token lifetime: 7 days (staff) / 3 days (portal)
- Refresh tokens are single-use — rotation on every use (UR-008)
- Replayed refresh tokens invalidate ALL user sessions (UR-009)

### Forced Password Change on First Login (UR-011)
The login response always includes a `must_change_password` boolean field.

```json
{
  "access_token": "...",
  "refresh_token": "...",
  "token_type": "bearer",
  "must_change_password": true
}
```

**If `must_change_password: true`:**
- Frontend redirects immediately to `/change-password`
- No other page or API action is accessible until password is changed
- User calls `PATCH /api/v1/auth/me/password` with current + new password
- Backend sets `must_change_password = false` on success
- Next login returns `must_change_password: false` — normal access granted

**Who gets `must_change_password: true` set:**
- Superadmin seeded by system on first launch
- Any user whose account is created with the flag explicitly set by their creator

**Frontend enforcement:**
```
Login → must_change_password: true → /change-password (no back, no skip)
                                          ↓
                               PATCH /auth/me/password
                                          ↓
                               must_change_password: false
                                          ↓
                               Redirect to dashboard
```

---

## STAFF APP — DASHBOARD SECTIONS

```
Overview (CEO/management)    Customers              Retail & POS
Cargo & Shipping             Infrastructure         Security Systems
Solar Projects               Stock / Inventory      Orders
Invoices                     Payments               Cash Sessions
Pickup & Delivery            Warehouse              Procurement
Suppliers                    Approvals              Exceptions
Commissions                  Reports                Audit Logs
Users & Roles                Settings
```

---

## ACCESS MATRIX BY ROLE

---

### SUPER ADMIN / FOUNDER

**Sees:** Everything across all companies, branches, departments.
All operational dashboards, all financial data, CEO dashboard, all reports,
all audit logs, all users, all customers, all commission data, system settings.

**Does:** Everything. Create/edit/delete users, assign roles, set permission flags,
override business rules, approve any action, view executive financial reports.

**No restrictions** except actions blocked by law or compliance policy.

---

### GROUP ADMIN / GENERAL MANAGER

**Sees:** All operational dashboards for assigned companies/branches.
Staff performance, approval queue, business KPIs, cargo status, retail status, services status.

**Does:** Supervise departments, approve operational actions, review exceptions,
assign managers, view operational reports.

**Cannot see (unless granted):** Owner-only settings, secret keys, system security config,
payroll, salary data, full audit logs, sensitive financial controls.

---

### CFO / FINANCE MANAGER

**Sees:** Invoices, payments, expenses, customer/supplier balances, cashier sessions,
refunds, credit notes, revenue by division, overdue invoices, financial approvals,
commission payout queue, commission disputes.

**Does:** Approve refunds, write-offs, payment extensions, release with unpaid balance (if flag granted),
reconcile payments, cancel invoices, approve commission payouts above threshold.

**Cannot see (unless granted):** Technical system settings, staff HR private data,
non-financial confidential operations.

---

### ACCOUNTANT / FINANCE OFFICER

**Sees:** Invoices, payments, receipts, cashier sessions, customer balances for their transactions,
unpaid orders, commission payment records.

**Does:** Record payments, print receipts, upload payment proof, reconcile transactions,
assist with cash session review.

**Cannot see:** Full company profit/loss, payroll, executive reports, audit logs,
bank account administration, supplier cost strategy, commission rules.

---

### CASHIER (RETAIL POS)

**Sees:** POS checkout screen, payments, receipts, today's cash session, unpaid retail orders.

**Does:** Record cash and mobile money payments, print receipts, close daily cash session,
confirm cash received, apply customer credit balance.

**Cannot see:** Stock cost price, supplier information, profit dashboard,
audit logs, full customer financial history, commission data.

---

### SHIPPING MANAGER

**Sees:** All cargo shipments (scoped to company/branch), packages, tracking events,
pickup requests, warehouse cargo, customs status, delivery status,
invoice payment status for cargo, cargo exceptions, assigned staff performance.

**Does:** Approve shipment corrections, approve delivery retry, approve warehouse release (if paid),
handle customs exceptions, assign cargo staff, review cargo reports.

**Cannot see (unless granted):** Retail profit reports, full finance dashboard, payroll, owner-only reports.

---

### WAREHOUSE OFFICER (CARGO)

**Sees:** Packages received, warehouse cargo, package photos, weight/dimensions,
tracking labels, tracking update screen, warehouse pickup queue, prohibited item checklist.

**Does:** Receive packages, upload package photos, record weight and dimensions,
print tracking labels, update tracking events, mark package condition,
confirm prohibited item check completed.

**Cannot see:** Full invoices, profit reports, customer financial history, payroll, executive dashboard.

---

### PICKUP AGENT / DRIVER / DELIVERY RIDER

**Sees:** Assigned pickups ONLY, assigned deliveries ONLY, customer contact for assigned job,
pickup/delivery address, route information, proof upload form.

**Does:** Confirm pickup, confirm delivery, upload proof of pickup/delivery,
add delivery failure note, mark delivery attempted.

**Cannot see:** Other shipments, invoice amounts, full customer list,
reports, audit logs, financial data.

---

### CUSTOMS OFFICER

**Sees:** Shipments under customs clearance, declared value, customs value,
customs documents, customs exceptions, supplementary customs invoices.

**Does:** Update customs status, upload customs documents, request additional documents from customer,
raise customs exception, request supplementary invoice.

**Cannot see:** Retail data, payroll, executive reports, non-customs financial data.

---

### CARGO SALES AGENT

**Sees:** Customer list, quotations, shipment creation form, shipment status for own customers.

**Does:** Create quotation, create shipment order, request pickup,
communicate shipment status to customers, create customer records.

**Cannot see:** Invoice amounts (unless granted), profit margins, staff assignments,
audit logs, financial reports.

---

### STORE MANAGER (RETAIL)

**Sees:** Products, stock, sales orders, purchase orders, POS summary, low stock alerts,
cashier sessions, retail invoices, supplier orders, store staff performance.

**Does:** Approve stock adjustments, approve order cancellations (< 500,000 XAF),
review POS sales, manage store staff, approve discounts (if permission flag granted).

**Cannot see (unless granted):** Cargo operations, full executive reports, payroll, owner-only reports.

---

### SALES AGENT (RETAIL)

**Sees:** Product catalog, available stock quantities, customers, quotations,
own sales orders, own sales performance.

**Does:** Create quotation, create sales order, reserve stock (per policy),
submit discount requests, create customer records.

**Cannot see:** Cost price (unless granted), profit margin, supplier payment details,
payroll, audit logs.

---

### INVENTORY OFFICER

**Sees:** Products, warehouses, stock movements, receiving queue, low stock alerts,
stock adjustment requests, purchase order status.

**Does:** Receive stock from suppliers, record stock movements, request stock adjustment,
transfer stock between locations (if authorized), print stock labels.

**Cannot see:** Revenue reports, customer balances, finance dashboard, payroll, commission data.

---

### PROCUREMENT OFFICER / PURCHASE OFFICER

**Sees:** Supplier list, purchase requests, purchase orders, receiving status,
supplier contacts, supplier performance ratings.

**Does:** Create purchase order draft, update supplier communication,
submit purchase request for approval, record goods received.

**Cannot see:** Full finance reports, payroll, customer private financial data, executive dashboard.

---

### INFRASTRUCTURE SERVICES MANAGER

**Sees:** Service requests, service tickets, site visits, installation projects,
maintenance contracts, technician assignments, client assets, service invoice status,
warranty records, security devices, solar projects, open exceptions.

**Does:** Assign technicians, approve technician schedules, approve emergency intervention,
approve warranty decisions, close completed service jobs, review service reports.

**Cannot see (unless granted):** Full financial reports, payroll, owner-only reports,
unrelated cargo/retail operations.

---

### TECHNICAL SALES ENGINEER

**Sees:** Leads, customers, service quotations, site survey requests,
service and product catalog, service contracts, own sales pipeline.

**Does:** Create service quotation, schedule site survey request, create service proposal,
follow up on leads, create customer records for IT/Solar/Security clients.

**Cannot see:** Full financial reports, payroll, other sales agents' pipelines (unless manager),
unrelated cargo operations.

---

### FIELD TECHNICIAN / CCTV TECHNICIAN / SOLAR TECHNICIAN

**Sees:** Assigned jobs ONLY, site address, customer contact for assigned job,
equipment checklist, installation notes, service report form, photo upload,
serial number entry screen, warranty entry screen.

**Does:** Start job, update job progress, upload site photos, record installed equipment,
enter serial numbers, submit service report, request parts, mark job completed (pending signoff).

**Cannot see:** Other technicians' jobs, invoice amounts, company-wide customer list,
full inventory cost price, finance dashboard, audit logs.

---

### HELPDESK AGENT

**Sees:** Support tickets, customer contact details, customer service history,
ticket status, escalation notes, shipment tracking lookup, service ticket lookup.

**Does:** Create support ticket, update ticket status, escalate ticket to manager,
communicate with customer, add internal notes.

**Cannot see:** Financial reports, stock cost price, executive data, payroll, commission data.

---

### ENERGY CONSULTANT / SOLAR PROJECT MANAGER

**Sees:** Solar leads, site survey reports, load assessments, solar project pipeline,
quotations, project status, installed systems, client assets, maintenance schedules.

**Does:** Create solar leads, schedule site surveys, generate quotations,
manage project pipeline, review system designs, close project on commissioning.

**Cannot see:** Unrelated retail/cargo financial data, payroll, audit logs.

---

### COMMISSION MANAGER

**Sees:** All commission partners, pending/approved/unpaid commissions,
payout history, disputed commissions, top performing partners, fraud/risk flags,
commission rules, commission approval queue.

**Does:** Review commission leads, approve commissions, initiate payouts (within threshold),
resolve commission disputes, manage commission partner accounts.

**Cannot see (unless granted):** Owner-only financial reports, payroll.

---

### CUSTOMER SUPPORT AGENT

**Sees:** Customer profiles, support tickets, shipment tracking, order status,
service ticket status, complaint history.

**Does:** Create support ticket, update customer communication, escalate complaints,
add internal notes, look up shipment/order/service status for customers.

**Cannot see:** Profit/loss, payroll, supplier costs, sensitive financial controls, audit logs.

---

## CUSTOMER PORTAL USER (customer.tehtek.com)

Sees **only their own data**:
- Own profile and KYC status
- Own orders (retail + special orders)
- Own shipments and tracking timeline
- Own invoices and payment history
- Own receipts
- Own service tickets and quotations
- Own support tickets
- Own credit balance

Can do:
- Place retail order
- Request pickup for cargo shipment
- Track shipment in real time
- View and download invoices
- Upload payment proof
- Submit KYC documents
- Request support
- Update own contact details

Cannot see: Staff dashboard, other customers, internal staff notes,
staff assignments, cost prices, profit, audit logs, commission data.

---

## COMMISSION PARTNER PORTAL (section within customer.tehtek.com)

A commission partner has a portal login that shows only their commission data:
- Own leads submitted
- Own approved commissions
- Own unpaid commissions
- Own payout history
- Dispute submission form

Cannot see: Other partners' data, TEHTEK internal commission rules,
amounts paid to other partners.

---

## SIDEBAR VISIBILITY BY ROLE

| Section | Super Admin | Finance | Shipping Mgr | Warehouse | Driver | Store Mgr | Sales Agent | Cashier | Inventory | Infra Mgr | Technician | Support |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| Overview | ✅ | ✅ | ✅ | ❌ | ❌ | ✅ | ❌ | ❌ | ❌ | ✅ | ❌ | ❌ |
| Customers | ✅ | ✅ | ✅ | ❌ | ❌ | ✅ | ✅ | ❌ | ❌ | ✅ | ❌ | ✅ |
| Retail | ✅ | ❌ | ❌ | ❌ | ❌ | ✅ | ✅ | ❌ | ❌ | ❌ | ❌ | ❌ |
| POS | ✅ | ❌ | ❌ | ❌ | ❌ | ✅ | ❌ | ✅ | ❌ | ❌ | ❌ | ❌ |
| Stock | ✅ | ❌ | ❌ | ❌ | ❌ | ✅ | ❌ | ❌ | ✅ | ❌ | ❌ | ❌ |
| Cargo | ✅ | ❌ | ✅ | ✅ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ✅ |
| Tracking | ✅ | ❌ | ✅ | ✅ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ✅ |
| Pickup & Delivery | ✅ | ❌ | ✅ | ❌ | ✅ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ |
| Infrastructure | ✅ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ✅ | ❌ | ❌ |
| Solar | ✅ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ✅ | ❌ | ❌ |
| Security Systems | ✅ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ✅ | ❌ | ❌ |
| My Jobs | ✅ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ✅ | ❌ |
| Invoices | ✅ | ✅ | ✅ | ❌ | ❌ | ✅ | ❌ | ✅ | ❌ | ✅ | ❌ | ❌ |
| Payments | ✅ | ✅ | ❌ | ❌ | ❌ | ✅ | ❌ | ✅ | ❌ | ❌ | ❌ | ❌ |
| Cash Sessions | ✅ | ✅ | ❌ | ❌ | ❌ | ✅ | ❌ | ✅ | ❌ | ❌ | ❌ | ❌ |
| Procurement | ✅ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ✅ | ❌ | ❌ | ❌ |
| Suppliers | ✅ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ✅ | ❌ | ❌ | ❌ |
| Approvals | ✅ | ✅ | ✅ | ❌ | ❌ | ✅ | ❌ | ❌ | ❌ | ✅ | ❌ | ❌ |
| Exceptions | ✅ | ✅ | ✅ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ✅ | ❌ | ❌ |
| Commissions | ✅ | ✅ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ |
| Reports | ✅ | ✅ | ✅ | ❌ | ❌ | ✅ | ❌ | ❌ | ❌ | ✅ | ❌ | ❌ |
| Audit Logs | ✅ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ |
| Users & Roles | ✅ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ |
| Settings | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |

---

## PERMISSION KEYS (Complete List)

All permission keys are formatted as `resource:action`.
These keys are stored in the permissions table and assigned via role_permissions.
Individual overrides stored in permission_flags table.

```
# System
dashboard:view

# Customers
customers:read
customers:create
customers:update
customers:delete
customers:blacklist
customers:kyc_verify
customers:vip_grant

# Retail
retail:read
retail:pos
retail:orders
retail:quotations
retail:discounts
retail:cost_price        ← requires explicit grant

# Stock
stock:read
stock:adjust
stock:transfer
stock:receive

# Cargo
cargo:read
cargo:create
cargo:update
cargo:dispatch
cargo:tracking_update
cargo:customs
cargo:release_override   ← requires can_approve_shipment_release flag
cargo:bags
cargo:travelers

# Infrastructure Services
services:read
services:create
services:assign
services:update
services:complete
services:reports
services:warranty

# Solar
solar:read
solar:create
solar:update
solar:commission

# Security Systems
security_systems:read
security_systems:create
security_systems:update

# Orders
orders:read
orders:create
orders:cancel
orders:approve

# Invoices
invoices:read
invoices:create
invoices:cancel
invoices:write_off       ← requires can_write_off_invoice flag

# Payments
payments:read
payments:create
payments:confirm
payments:refund
payments:cash_session

# Finance
finance:reports
finance:executive_reports ← requires can_access_executive_reports flag
finance:payroll          ← requires can_access_payroll flag
finance:salary_data      ← requires can_view_salary_data flag
finance:bank_accounts    ← requires can_manage_bank_accounts flag

# Commissions
commissions:read
commissions:create
commissions:approve
commissions:pay
commissions:dispute
commission_partners:manage
commission_rules:manage

# Approvals
approvals:read
approvals:approve

# Exceptions
exceptions:read
exceptions:resolve

# Reports
reports:read
reports:executive
reports:ceo_dashboard    ← requires can_access_ceo_dashboard flag

# Procurement
procurement:read
procurement:create
procurement:approve

# Audit
audit:read               ← requires can_access_audit_logs flag

# Users & Roles
users:read
users:create
users:update
users:delete
roles:manage
permission_flags:manage  ← Super Admin only

# Settings
settings:view
settings:manage          ← Super Admin only
```

---

## INDIVIDUAL PERMISSION FLAGS (Known Flags)

These flags are stored per user in the permission_flags table.
They can ADD capabilities beyond a role, or RESTRICT capabilities a role normally grants.

```
can_approve_refund
can_override_price
can_export_financial_reports
can_delete_invoice
can_access_audit_logs
can_edit_paid_invoice
can_access_ceo_dashboard
can_manage_bank_accounts
can_create_discount
can_approve_shipment_release
can_release_shipment_without_payment
can_access_executive_reports
can_modify_customs_value
can_approve_high_risk_client
can_override_inventory_count
can_approve_vehicle_sale
can_approve_property_purchase
can_access_payroll
can_view_salary_data
can_approve_international_transfer
can_manage_vendor_contracts
can_grant_vip_status
can_write_off_invoice
can_approve_commission_payout
can_manage_commission_rules
can_access_cost_price
```

---

## SECURITY RULES SUMMARY

**Rule ACC-001:** One staff dashboard shell. Never separate dashboards per department.
Sidebar visibility = calculated from permissions. Never hardcoded by role label.

**Rule ACC-002:** Frontend hiding is not security.
Backend must check permissions on EVERY API call even if the UI hides the button.
```
Frontend hides/disables  →  Backend validates permission  →  Database enforces constraint  →  Audit logs attempt
```

**Rule ACC-003:** Multi-role union.
User with multiple roles gets the union of all role permissions.
Permission flags then add to or restrict this union.

**Rule ACC-004:** Company and branch scope always applied.
Every data query must include: WHERE company_id = user.company_id
Super Admin is the ONLY exception to this rule.

**Rule ACC-005:** Customer portal data isolation.
Backend must validate: customer_id == authenticated_user.customer_id on every portal query.
A customer can NEVER access another customer's data under any circumstance.

**Rule ACC-006:** Commission partner portal isolation.
A commission partner can only see their own leads, commissions, and payout history.
Never another partner's data.

**Rule ACC-007:** No API router without authentication. ★ NEW
Every APIRouter is instantiated with `dependencies=[Depends(get_current_user)]`.
No route is exposed unauthenticated unless explicitly in the public whitelist (ACC-008).
Startup route audit validates this on every deployment.

**Rule ACC-008:** Public route whitelist. ★ NEW
Only auth endpoints, password reset, health check, and the public tracking endpoint
operate without JWT. All others require a valid, non-expired access token.
Any addition to the whitelist requires Owner approval and this document updated.

**Rule UR-011:** Forced password change on first login.
Seeded accounts have must_change_password=true. Login response includes this flag.
Frontend blocks all navigation until PATCH /auth/me/password clears the flag.
Backend sets must_change_password=false on successful password change.
