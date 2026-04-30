# TEHTEK — Business Rules Contract
# Version: 1.5 | April 2026
# Owner: Benjamin Boule Fogang
# Rule: Every rule enforced at 3 levels: Database → Backend → Frontend + Audit log
# Adding new rules: write here first → owner review → implement all 3 levels → test
# Changelog v1.5: Added UR-011 (forced password change on first login for seeded accounts).
# Changelog v1.4: Added UR-007 to UR-010 (auth/JWT rules), ACC-007 (no router without auth),
#                 ACC-008 (public route whitelist).

---

## ENFORCEMENT LEVELS

```
Level 1 — DATABASE : Hard constraint (CHECK, UNIQUE, FK, trigger)
Level 2 — BACKEND  : Business logic validation in controller
Level 3 — FRONTEND : UI disables or hides the action before it is attempted
Level 4 — AUDIT    : Every attempt logged, even if blocked
```

---

## SECTION 1 — SHIPMENT RULES

### SR-001 — No shipment without a customer
A shipment cannot be created without a linked, active customer record.
- DB: customer_id FK NOT NULL
- Backend: validate customer exists, is active, not blacklisted (call validate_for_transaction)
- Frontend: customer selector required and validated before form submits

### SR-002 — No shipment without a tracking number
Every shipment receives a system-generated tracking number on confirmation.
- DB: tracking_number UNIQUE NOT NULL — generated via sequence_registry
- Backend: auto-generate atomically on status change draft → confirmed
- Format: TRK-[ROUTE_CODE]-[YEAR]-[000000] e.g. TRK-CNACM-2026-000142
- Tracking numbers are immutable — never changed after assignment

### SR-003 — No shipment released if invoice is unpaid ★ KING RULE
A shipment cannot move to out_for_delivery status if its invoice is unpaid or partial.
- DB: trigger validates invoice.status before status change to out_for_delivery
- Backend: validate invoice.status == paid before dispatch action
- Frontend: dispatch button disabled with "Invoice unpaid" message shown
- Override: requires can_approve_shipment_release permission flag + mandatory reason + audit log

### SR-004 — No shipment status goes backward
Statuses follow a one-way flow with one allowed exception.
- Allowed reversal: delivery_failed → out_for_delivery (retry delivery, max 3 attempts)
- All other reversals: owner-level permission + mandatory reason
- Backend: validate transition against allowed_transitions map on every status change

### SR-005 — Weight and dimensions required before dispatch
- DB: check on status transition to ready_for_dispatch
- Backend: validate weight_kg, length_cm, width_cm, height_cm all non-null
- Frontend: warning shown and dispatch blocked if fields empty

### SR-006 — Photos required for international shipments
For shipment_type = air_cargo or sea_freight: minimum 2 package photos required.
- Backend: validate photo_count >= 2 before confirming dispatch
- Frontend: photo upload required before dispatch button activates

### SR-007 — Customs values mandatory for international shipments
declared_value and customs_value cannot be null for non-local routes.
- DB: conditional check based on route
- Backend: validate on confirmation
- Frontend: both fields required for any non-local route

### SR-008 — Customer accepts liability declaration before confirmation
Before confirming a shipment, customer must explicitly accept:
"I confirm all declared information is accurate. I accept full responsibility
for false declarations, prohibited items, and resulting customs penalties."
- DB: declaration_accepted = true required before status → confirmed
- Backend: block confirmation if declaration_accepted is false
- Frontend: mandatory checkbox before submit
- Audit: timestamp, IP address, and user logged on acceptance

### SR-009 — Prohibited item check mandatory at every intake
Warehouse staff must confirm prohibited item screening before accepting a package.
- DB: prohibited_check_done = true required before status → warehoused
- Backend: block status change if check not confirmed
- Frontend: checklist acknowledgment required
- Reference: TEHTEK_PROHIBITED_ITEMS.md for full list

### SR-010 — Insurance status declared before dispatch
insurance_status cannot be null when shipment moves past warehoused status.
- Backend: validate insurance_status is set (default: not_requested — customer chose not to insure)
- Insured value cannot exceed declared_value

---

## SECTION 2 — CARRIER & BAG RULES

### CB-001 — No bag sealed without complete package manifest
All packages in a bag must have tracking numbers and weights before the bag is sealed.
- Backend: validate all package fields before allowing BagStatus → sealed
- Manifest auto-generated and immutable after sealing

### CB-002 — No traveler assignment without full travel details
Required fields before assignment: full name, ID number, flight number,
departure date, destination, phone number.
- DB: all fields NOT NULL on carrier_assignments
- Backend: validate all fields present before assignment is created

### CB-003 — Bag weight cannot exceed carrier limit
Sum of package weights must not exceed carrier.max_weight_kg.
- Backend: calculate total weight, validate against carrier limit
- Frontend: running total shown during package assignment to bag

### CB-004 — Package can only be in one bag at a time
- DB: UNIQUE constraint on bag_packages(package_id)
- Backend: validate package not already in an active bag

---

## SECTION 3 — STORAGE & ABANDONMENT RULES

### ST-001 — Free storage period after arrival
All shipments receive free storage after arriving at a TEHTEK branch.
- Standard customers: 3 days free storage
- VIP customers: 7 days free storage
- After free period ends: storage fee applies automatically

### ST-002 — Storage fee schedule
After free period expires:
- Days 1-7 of paid period: 500 XAF per package per day
- Days 8-14: 1,000 XAF per package per day
- Day 15+: escalate to management for decision
- Storage fee invoice auto-generated when fee period starts
- Shipment status: → storage_fee_applied

### ST-003 — Abandoned package process
- Day 21 after arrival (or day 14 post-free period): customer sent final warning
- Warning sent via WhatsApp + SMS + Email
- Day 28: status → abandoned — management decision mandatory
  Options: Dispose (photo evidence required) | Auction (value > 50,000 XAF) | Hold (owner approval)
- Cannot close exception without owner decision

### ST-004 — Storage fees are separate from original invoice
Customer must pay both: original shipment invoice AND storage fee invoice before release.
- Waiving storage fees requires Finance Manager approval + audit log entry

---

## SECTION 4 — PAYMENT & INVOICE RULES

### PR-001 — Every confirmed shipment or completed service auto-generates an invoice
- Backend: invoice created in the same transaction as confirmation
- Invoice number generated atomically via sequence_registry
- Format: INV-[YEAR]-[MM]-[000000]

### PR-002 — Invoices cannot be deleted — only cancelled
- DB: no DELETE permission on invoices table for any role
- Backend: only status → cancelled is allowed, with mandatory reason
- Only Finance Manager or above can cancel invoices

### PR-003 — Cancelled invoices cannot be reactivated
- DB: trigger prevents status change from cancelled to any other status
- To resume: create a new invoice

### PR-004 — Partial payments tracked per payment record
Each payment creates a payment_records entry. Balance recalculated after each.
- DB: balance = total - paid_amount (updated on each payment)
- Invoice status → partial until balance reaches zero

### PR-005 — Payment proof required for bank transfers
If payment_method = bank_transfer: proof document upload is required.
- Backend: validate proof_url is not null before confirming bank transfer payment
- Frontend: file upload required when bank transfer is selected

### PR-006 — Written-off invoices require CFO approval
Only users with can_write_off_invoice permission flag can change status → written_off.
- Audit log: who approved, reason, amount written off, date

### PR-007 — Overdue invoice notification schedule
Daily background job sends notifications:
- on due_date: first reminder
- due_date + 3 days: second reminder
- due_date + 7 days: third reminder + Finance Manager notified
- due_date + 14 days: Owner notified and escalation initiated

### PR-008 — No price override without permission flag
Changing a price on a confirmed invoice requires can_override_price flag.
- Audit log: original price, new price, who changed it, reason

### PR-009 — Receipt auto-generated on full payment
When invoice status → paid: receipt auto-generated and sent.
- Format: RCP-[YEAR]-[MM]-[000000]
- Sent automatically via WhatsApp + Email

---

## SECTION 5 — CUSTOMER RULES

### CR-001 — No transaction with a blacklisted customer
Blacklisted customers cannot create shipments, orders, or receive services.
- DB: check customer.status != blacklisted before creating any transaction
- Backend: CustomerController.validate_for_transaction() called by all modules
- Frontend: "Account restricted" message shown, actions disabled
- Override: can_approve_high_risk_client flag + mandatory reason + audit log

### CR-002 — Outstanding balance warning before new transaction
If customer.outstanding_balance > 0 for more than 30 days: warn staff.
- Backend: validate_for_transaction() returns warnings list
- Frontend: yellow warning banner shown — staff can proceed but the warning is logged
- If balance exceeds threshold (by customer type): manager approval required

### CR-003 — KYC required for high-value transactions
KYC level must match the transaction value:
- Basic KYC: transactions up to 500,000 XAF
- Standard KYC: transactions up to 5,000,000 XAF
- Enhanced KYC: transactions above 5,000,000 XAF
- Backend: validate kyc_level against transaction value in validate_for_transaction()

### CR-004 — Customer with history cannot be hard-deleted
If a customer has any shipment, order, invoice, or payment history:
- Only soft-delete is allowed (deleted_at timestamp set)
- DB: FK constraints prevent hard deletion of referenced customers

### CR-005 — VIP status requires explicit staff approval
- Backend: can_grant_vip_status permission flag required
- DB: vip_granted_by and vip_granted_at recorded
- Audit log: who granted it, reason, date

---

## SECTION 6 — USER & AUTHENTICATION RULES

### UR-001 — Users are scoped to company and branch
Every user belongs to at least one company. Branch is optional (group-level users have no branch).
- DB: company_id NOT NULL on users; branch_id nullable
- Backend: all queries for non-superadmin users filtered by company_id

### UR-002 — Account locked after 5 failed login attempts
Account locked for 15 minutes. Admin can manually unlock.
- DB: failed_login_count, locked_until fields on users table
- Backend: check and enforce on every login attempt

### UR-003 — Every login attempt is logged
Both successful and failed attempts are recorded in user_audit_logs.
- DB: user_audit_logs entry on every login
- Fields: user_id, action, ip_address, user_agent, success, timestamp

### UR-004 — Superadmin cannot be deleted or suspended
The is_superadmin flag protects the founder account.
- Backend: block any delete, suspend, or role removal on is_superadmin = true users

### UR-005 — Password must meet minimum requirements
- Minimum 8 characters
- At least 1 uppercase letter
- At least 1 digit
- Validated in Pydantic schema before reaching DB

### UR-006 — All sensitive user actions are audit-logged
Always logged regardless of success or failure:
Login/logout · Password change · Role assignment change
Permission flag change · Account suspension · VIP grant/revoke
Customer blacklist/unblacklist · Any approval decision
Cash discrepancy approval · Invoice cancellation/write-off

### UR-007 — JWT access token expiry ★ NEW
Access tokens expire after 60 minutes (staff app) and 30 minutes (customer portal).
- Backend: validate token expiry on every protected route in dependencies.py
- Frontend: auto-refresh using refresh token before expiry
- On expiry without valid refresh token: force logout, redirect to login

### UR-008 — Refresh token rotation ★ NEW
Every use of a refresh token issues a NEW refresh token and invalidates the old one.
- DB: refresh tokens stored with is_used = true after first use
- Backend: reject any refresh token already marked used (replay protection)
- Refresh token lifetime: 7 days (staff) / 3 days (customer portal)
- Refresh tokens are single-use. Using an already-used token triggers a security alert.

### UR-009 — Refresh token replay triggers immediate session invalidation ★ NEW
If a used refresh token is presented again:
- All active sessions for that user are immediately invalidated
- User is forced to log in again
- Security alert created in user_audit_logs with ip_address and user_agent
- Shipping Manager / Admin notified if staff account affected

### UR-010 — Password reset tokens are single-use and time-limited ★ NEW
- Reset token expires after 30 minutes
- Token is invalidated immediately on first use (whether successful or not)
- DB: reset_token_expiry and reset_token fields on users; cleared after use
- Failed reset attempts logged in user_audit_logs

### UR-011 — Seeded accounts must change password on first login ★ NEW
Any user account created by the system seed (not by a staff member) must change their
password immediately after their first successful login.
- DB: must_change_password BOOLEAN NOT NULL DEFAULT FALSE on users table
- Seed: must_change_password = TRUE for all seeded accounts (superadmin on first launch)
- Backend (login): must_change_password flag included in TokenResponse
- Frontend: if must_change_password = true in login response → redirect to /change-password
  before granting access to any other page or API. Do not allow navigation around this.
- Backend (change password): on successful PATCH /auth/me/password → set must_change_password = FALSE
- The flag is cleared only by the user completing the password change themselves
- Staff-created users: must_change_password defaults to FALSE unless explicitly set TRUE by creator
- Audit log: password change event logged with actor = user themselves

---

## SECTION 7 — STOCK & INVENTORY RULES

### STK-001 — Stock cannot go below zero
- DB: CHECK constraint quantity >= 0
- Backend: validate available_quantity >= requested_quantity before any dispatch

### STK-002 — Every stock movement requires a reason and staff member
- DB: reason NOT NULL, created_by NOT NULL on all stock_movements records
- No silent stock changes allowed

### STK-003 — Large stock adjustments require manager approval
Manual adjustments above 10 units OR above 100,000 XAF value:
- Backend: create ApprovalWorkflow before applying adjustment
- Stock is reserved but not adjusted until approved

### STK-004 — Low stock triggers automatic staff alert
When stock_item.quantity < stock_item.min_quantity:
- Notification sent to Inventory Officer and Store Manager
- In-app alert + email

### STK-005 — Unpaid stock reservations expire after 24 hours
- Scheduled background job checks all reservations
- Expired reservations: status → expired, stock released, customer notified
- Paid reservations are never touched by the expiry job

### STK-006 — Paid reservations do not expire
Once payment is confirmed on a reservation: status → paid, protected until pickup or delivery.

### STK-007 — Special orders require minimum 50% deposit before procurement
- Backend: validate deposit_amount >= (order.total * 0.5) before starting procurement
- Frontend: deposit amount shown clearly on special order creation form
- Balance due before release/delivery — same SR-003 rule applies

---

## SECTION 8 — ORDER RULES

### OR-001 — Order total must always match line items
total = sum(line_items) + tax - discount
- Backend: recalculate total on every line item change
- DB: no manual total override without matching line items

### OR-002 — Confirmed orders cannot have line items edited
Once order status is confirmed, processing, or shipped:
- Line items are locked
- To change: cancel and create a new order
- Cancellations above 500,000 XAF require manager approval

### OR-003 — Purchase orders require supplier confirmation reference
Cannot move to processing without supplier_ref_number being set.
- Backend: validate field presence before status change

### OR-004 — Order numbers generated via sequence registry
Format: ORD-[YEAR]-[000000]
- Generated atomically — never duplicated

---

## SECTION 9 — INFRASTRUCTURE SERVICES RULES

### ISR-001 — No service job without a customer
- DB: customer_id FK NOT NULL on service_tickets
- Backend: validate customer exists and is active

### ISR-002 — No technician assignment without a scheduled date
- DB: scheduled_date NOT NULL on technician_assignments
- Backend: validate date is in the future at time of assignment

### ISR-003 — Completed service requires signed customer acceptance
- Backend: customer_acceptance_signed = true required before status → completed
- Physical or digital signature stored
- No exceptions — rule ISR-003 is hard

### ISR-004 — Every completed job generates a service report
- Backend: service_report content required before status → completed
- Report must include: work done, parts used, technician notes, customer signature reference

### ISR-005 — Every completed job generates an invoice
- Backend: invoice auto-generated on status → completed
- Invoice linked to service ticket — InvoiceType = it_service or solar_project

### ISR-006 — All installed equipment must be documented before job close
- Backend: validate at least one asset exists in client_assets / security_devices / installed_systems
- Serial number, model, location, installation date all required

### ISR-007 — Warranty attached to every installed device
- DB: warranty_period_months, warranty_start_date, warranty_end_date required
- FK from installed device to warranty_records

### ISR-008 — Emergency service requires priority fee by default
- Backend: priority_fee applied automatically on emergency service type
- Waiver: Finance Manager approval (ApprovalType: emergency_fee_waiver) + audit log

### ISR-009 — Maintenance contracts require SLA definition
For ContractType = monthly_maintenance, quarterly_maintenance, annual_sla, amc:
- response_time_hours required
- covered_services list required
- excluded_services list required
- billing_cycle required
- start_date and end_date required

### ISR-010 — Client-owned equipment must be recorded before maintenance begins
- Backend: validate client_assets exist for the customer before work order can be opened

---

## SECTION 10 — SOLAR & ENERGY RULES

### ESR-001 — No solar project without a completed site survey
- Backend: site_survey_completed = true required before status can move past lead

### ESR-002 — No quotation without a load assessment
Quotation generation requires:
- site_survey_report uploaded
- load_assessment_kwh recorded
- proposed_system_capacity_kwp defined

### ESR-003 — No installation without signed quotation and minimum 50% deposit
- DB: check before status → installation
- customer_signed_quotation = true required
- deposit_paid = true AND deposit_amount >= 50% of project value required

### ESR-004 — Installed equipment must have warranty records
Every panel, inverter, battery: serial number + warranty_records entry required.
- Backend: validate before project can be commissioned

### ESR-005 — Maintenance schedule auto-created for every commissioned system
On status → commissioned:
- First maintenance: 3 months after commissioning
- Annual maintenance: every 12 months thereafter
- Auto-created by backend — not optional

### ESR-006 — Battery and inverter serial numbers are mandatory
- DB: serial_number NOT NULL on battery_inventory and inverter_inventory
- Backend: validate before job can be marked completed

### ESR-007 — Safety checklist mandatory before commissioning
- Backend: safety_checklist_completed = true required before status → commissioned
- Checklist: electrical safety, grounding, protection devices, labelling verified

### ESR-008 — Customer final acceptance required before project closure
- Backend: customer_final_acceptance = true required before status → completed
- Physical or digital signature stored

### ESR-009 — Commercial projects above threshold require supervisor approval
Projects above 5,000,000 XAF value:
- Backend: supervisor_approved = true required before status → procurement

### ESR-010 — Emergency maintenance billing
- Outside contract: priority fee applies automatically
- Within AMC/maintenance contract: check covered_services first
- Waiver: Finance Manager approval + audit log

---

## SECTION 11 — COMMISSION RULES

### COM-001 — No commission without a linked transaction
Every commission must link to a shipment, order, invoice, service project, or contract.
- DB: at least one of (shipment_id, order_id, invoice_id, project_id) must be set — NOT all null

### COM-002 — Commission status payable only after TEHTEK receives payment
commission.status cannot become payable until:
- linked invoice.status = paid OR linked payment.status = confirmed
- DB: trigger validates before status change
- Backend: validate at controller level

### COM-003 — Commission rate must follow approved commission_rules
No ad-hoc percentage negotiation after a deal is closed.
- Must come from: predefined % in commission_rules table, fixed approved amount, or custom override
- Custom override: Sales Manager approval + audit log

### COM-004 — Commission payout requires multi-level approval
- Up to 50,000 XAF: Sales Manager approval
- 50,001 to 500,000 XAF: Finance Manager approval
- Above 500,000 XAF: Owner approval
All approvals logged via ApprovalWorkflow

### COM-005 — Every commission payout must be fully auditable
Required before payout can be marked processed:
- approved_by (user_id)
- paid_by (user_id)
- payment_method
- payout_date
- payment_proof_url
- payment_reference
- reason for any adjustment from original amount

### COM-006 — Commission disputes must be logged
- Dispute creates ExceptionType: commission_dispute record
- Finance review → manager decision → full audit trail preserved
- Status tracked via CommissionDisputeStatus

### COM-007 — No commission payout before TEHTEK receives money ★
This is the most important commission rule. Non-negotiable.
- DB: trigger validates linked invoice is paid before any payout record can be created
- Backend: double-check in controller before creating payout
- Only the Founder can authorize an exception — no one else

### COM-008 — Commission fraud flags freeze payout immediately
If fraud_flag = true on a commission record:
- Payout frozen automatically
- Exception created: commission_fraud_flag
- Finance Manager AND Owner notified immediately
- Investigation required and completed before any payout can proceed

---

## SECTION 12 — CASHIER & CASH RULES

### CASH-001 — Cashier must open a daily session before accepting cash
Active cash session required before recording any cash payment.
- Backend: validate active cash_session exists for cashier before any cash transaction

### CASH-002 — Daily cash session must be closed at end of shift
Cashier declares physical cash counted (cash_counted).
System calculates expected from all transactions (cash_expected).
- If match → session closes normally
- If mismatch → status → discrepancy_flagged, session cannot close

### CASH-003 — Cash discrepancy requires manager approval
Any mismatch between cash_counted and cash_expected:
- Mandatory reason required
- ApprovalWorkflow created (ApprovalType: cash_discrepancy)
- Session cannot close until approved
- Audit: expected, counted, difference, who approved, reason

### CASH-004 — Cash discrepancy escalation thresholds
- Above 10,000 XAF → Finance Manager notified immediately
- Above 50,000 XAF → Owner notified immediately, investigation required before close

### CASH-005 — No cash payment recorded outside an open session
- DB: cash_session_id NOT NULL on all cash payment records

---

## SECTION 13 — SEQUENCE REGISTRY RULES

### SEQ-001 — All sequential numbers generated via sequence_registry table
Atomic increment using SELECT FOR UPDATE.
Never generate sequential numbers at application level — race conditions.

### SEQ-002 — Sequences never reset mid-year
Year resets are acceptable (restart at 000001 each January 1).
Never reset mid-year under any circumstance.

### SEQ-003 — Gaps in sequences are acceptable
Cancelled transactions retire their number — it is never reused.
Auditors may see gaps — this is normal and correct.

### SEQ-004 — Sequence formats
```
tracking_number   → TRK-[ROUTE]-[YEAR]-[000000]
invoice_number    → INV-[YEAR]-[MM]-[000000]
customer_code     → CUS-[000000]
order_number      → ORD-[YEAR]-[000000]
receipt_number    → RCP-[YEAR]-[MM]-[000000]
pickup_number     → PKP-[YEAR]-[000000]
bag_number        → BAG-[TYPE]-[YEAR]-[0000]
service_ticket    → SVC-[YEAR]-[000000]
project_number    → PRJ-[YEAR]-[000000]
contract_number   → CNT-[YEAR]-[000000]
commission_record → COM-[YEAR]-[000000]
payout_number     → PAY-[YEAR]-[MM]-[000000]
```

---

## SECTION 14 — DATA INTEGRITY RULES

### DI-001 — Soft delete only — no hard deletes in production
deleted_at timestamp on all critical tables.
All queries filter WHERE deleted_at IS NULL by default.
Physical deletion only by Super Admin in rare legal compliance cases.

### DI-002 — Amounts stored as Numeric(14,2)
Consistent across all tables. Never mix integer and decimal storage.

### DI-003 — All timestamps stored in UTC
Display conversion to Africa/Douala timezone happens in the frontend only.
Never store local time in the database.

### DI-004 — Tracking numbers are immutable
Once assigned to a shipment: never changed.
If error: cancel shipment, create new one. Never edit the tracking number.

---

## SECTION 15 — ACCESS & DASHBOARD RULES

### ACC-001 — One staff dashboard shell, permission-based menus
Do not build separate dashboards per department.
One shared layout. Sidebar visibility calculated from permissions, not role labels.
Reference: TEHTEK_ACCESS_MATRIX.md

### ACC-002 — Frontend visibility is not security
Backend must check permissions on every API call even if UI hides the button.
Triple enforcement: Frontend → Backend → Database → Audit

### ACC-003 — Multi-role permission union
User with multiple roles: union of all role permissions applies.
Permission flags can add to or restrict this union.

### ACC-004 — Company and branch scope always applied
All queries scoped by user.company_id + user.branch_id.
Super Admin is the only role that bypasses company/branch scope.

### ACC-005 — Customer portal data isolation
Customer portal users can ONLY query their own data.
Backend: validate customer_id == authenticated_user.customer_id on every portal query.

### ACC-006 — Commission partner portal isolation
Commission partners in portal see ONLY their own leads, commissions, and payouts.

### ACC-007 — No API router endpoint without authentication ★ NEW
Every API endpoint MUST require a valid JWT access token, with no exceptions except
the routes explicitly listed in the public route whitelist (ACC-008).
- Backend: `get_current_user` dependency applied at router level — NEVER per-route manually
- Apply dependency at `APIRouter` instantiation, not at individual endpoints
- Pattern: `router = APIRouter(dependencies=[Depends(get_current_user)])`
- This means: if you add a new router and forget auth, the app WILL NOT protect it by default
- At startup: an automated route audit logs all routes WITHOUT auth dependency — reviewed daily
- Any unprotected route (outside whitelist) is treated as a critical security incident

### ACC-008 — Public route whitelist (no auth required) ★ NEW
ONLY the following routes may operate without authentication. All others require JWT.

Staff App (app.tehtek.com / api.tehtek.com/api/v1):
```
POST   /api/v1/auth/login
POST   /api/v1/auth/refresh
POST   /api/v1/auth/password-reset/request
POST   /api/v1/auth/password-reset/confirm
GET    /api/v1/health           ← system health check only
```

Customer Portal (customer.tehtek.com):
```
POST   /api/v1/portal/auth/login
POST   /api/v1/portal/auth/refresh
POST   /api/v1/portal/auth/password-reset/request
POST   /api/v1/portal/auth/password-reset/confirm
GET    /api/v1/tracking/{tracking_number}   ← public shipment tracking (read-only, no PII)
GET    /api/v1/health
```

Any deviation from this list requires:
- Owner approval
- Written justification in this document
- Audit log entry
- Review within 7 days of deployment

---

## RULE OVERRIDE PROCESS

1. Staff member submits override request with mandatory reason
2. System creates ApprovalWorkflow record
3. Authorized person approves or rejects
4. Audit log: who requested, who decided, reason, timestamp, outcome
5. All overrides reviewed weekly by management

## ADDING NEW RULES

1. Write rule here with code (SR-xxx, PR-xxx, etc.)
2. Owner reviews and approves
3. Implement at all 3 enforcement levels simultaneously
4. Test before deploying to production
