# TEHTEK — Master Enum Document
# Version: 1.0 | April 2026
# Owner: Benjamin Boule Fogang
# Rule: NEVER define an enum in code without adding it here first.
# Location in code: app/core/enums.py (single source of truth)
# All enums are strings, lowercase with underscores. Never integers.

---

## 1. USER & ACCESS

### UserStatus
```
active      → Account fully operational
inactive    → Deactivated by admin (not deleted)
suspended   → Temporarily blocked (can be reactivated)
pending     → Awaiting verification or admin approval
```

### UserType
```
internal           → TEHTEK staff / employees
external           → Customers and vendors with portal access
referral           → Referral agents
commission_partner → Commission/sales partners
```

### KYCStatus
```
not_submitted → No documents uploaded yet
pending       → Documents uploaded, awaiting review
verified      → KYC approved by staff
rejected      → KYC rejected (reason stored separately)
expired       → Previously verified but documents have expired
```

### KYCLevel
```
basic    → Name + phone only — transactions ≤ 500,000 XAF
standard → ID document verified — transactions ≤ 5,000,000 XAF
enhanced → Full KYC — transactions > 5,000,000 XAF
```

### AuthTokenType ★ NEW
```
access   → Short-lived JWT access token (60 min staff / 30 min portal)
refresh  → Long-lived refresh token (7 days staff / 3 days portal) — single-use
reset    → Password reset token (30 min) — single-use
```

---

## 2. COMPANY & STRUCTURE

### CompanyType
```
parent     → TEHTEK IT Services (top-level group)
subsidiary → Business division (Cargo, Retail, Cars, etc.)
branch     → Physical location of a subsidiary
partner    → External partner organization
```

### BranchType
```
headquarters     → Main office
cargo_hub        → Cargo warehouse + operations
retail_store     → Physical retail location
warehouse        → Storage only
agency           → Agent pickup/delivery point
procurement      → Sourcing office (China, USA, Europe)
it_service_center → IT/Security/Solar service center
```

### DepartmentType
```
operations             → Core business execution
finance                → Accounting, payments, budgets
hr                     → Human resources, payroll
sales                  → Sales and CRM
logistics              → Cargo, delivery, pickup
warehouse              → Stock and inventory
it                     → Technology and systems
legal                  → Compliance and contracts
executive              → Management and oversight
customer_service       → Support and relations
infrastructure_services → IT + Security + Solar operations
```

---

## 3. CUSTOMER

### CustomerType
```
retail           → Walk-in or online retail buyer
corporate        → Business account (B2B)
vip              → High-value, priority customer
shipping         → Cargo/shipping customer
vendor           → Sells through TEHTEK platform
supplier         → Supplies goods to TEHTEK
referral_partner → Refers clients for commission
property_client  → Real estate transactions
fleet_client     → Car/vehicle fleet customer
tenant           → Property rental tenant
hotel_guest      → Hospitality customer
it_service_client → IT/Security/Solar service customer
solar_client     → Solar energy installation client
```

### CustomerRiskLevel
```
low         → Verified, good payment history
medium      → Some payment delays or incomplete KYC
high        → Disputes, late payments, or flagged behaviour
blacklisted → Blocked from all transactions
```

### CustomerStatus
```
active      → Normal account
inactive    → No recent activity or deactivated
suspended   → Temporarily blocked by admin
blacklisted → Permanently blocked with reason
```

---

## 4. COMMISSION PARTNER

### CommissionPartnerType
```
referral_agent                    → General referral partner
sales_commission_partner          → Active sales partner
corporate_introducer              → Introduces corporate clients
cargo_lead_agent                  → Brings cargo/shipping leads
procurement_connector             → Sourcing/procurement connections
property_referral_partner         → Real estate referrals
vehicle_sales_broker              → Car sales introductions
infrastructure_project_introducer → IT/Solar/Security project leads
vip_client_connector              → High-value client introductions
independent_business_partner      → General business development
```

### CommissionPartnerStatus
```
active      → Active partner
suspended   → Temporarily suspended
blacklisted → Permanently blocked
inactive    → No longer active
```

### CommissionStatus
```
pending   → Lead converted, awaiting invoice payment confirmation
payable   → Linked invoice paid — commission approved for payout
paid      → Commission paid to partner
disputed  → Partner disputes the amount
cancelled → Commission cancelled with mandatory reason
on_hold   → Flagged for review before payout
```

### CommissionPayoutStatus
```
pending   → Payout initiated, awaiting approval
approved  → Approved, awaiting payment
processed → Payment completed
failed    → Payment failed — needs retry
cancelled → Payout cancelled
```

### CommissionDisputeStatus
```
open                 → Dispute reported, not yet handled
in_review            → Under investigation
resolved_for_partner → Resolved in partner's favour
resolved_for_tehtek  → Resolved in TEHTEK's favour
escalated            → Sent to higher authority
closed               → Closed
```

---

## 5. SHIPMENT

### ShipmentType
```
air_express  → Travelers carrying packages in checked baggage (1-5 days)
air_cargo    → Standard airline cargo (5-10 days)
sea_freight  → Sea container freight (25-45 days)
land_freight → Cross-border land transport
local_express → Same-day local delivery
```

### ShipmentRoute
```
china_cameroon   → China → Cameroon
usa_cameroon     → USA → Cameroon
europe_cameroon  → Europe → Cameroon
cameroon_china   → Cameroon → China (exports)
cameroon_usa     → Cameroon → USA (exports)
cameroon_local   → Within Cameroon
cameroon_africa  → Cameroon → Other African countries
```

### ShipmentStatus
```
draft               → Created but not confirmed
confirmed           → Confirmed by staff, tracking number assigned
package_received    → Physical package received at warehouse
warehoused          → Stored in warehouse awaiting dispatch
ready_for_dispatch  → Cleared and ready to ship
assigned_to_bag     → Added to a bag/carton/container
assigned_to_carrier → Assigned to a traveler or carrier
in_transit          → En route to destination
arrived_destination → Landed at destination country
customs_clearance   → Under customs review
customs_cleared     → Customs approved
customs_held        → Held by customs (issue to resolve)
customs_seized      → Seized by customs (serious)
storage_pending     → Arrived but customer has not collected
storage_fee_applied → Storage fee being charged
abandoned           → Declared abandoned — management decision required
out_for_delivery    → With delivery rider/driver
delivered           → Successfully delivered ✅
delivery_failed     → Delivery attempted but failed
returned_to_sender  → Being sent back to origin
lost                → Package confirmed lost
cancelled           → Cancelled before dispatch
```

### ShipmentPriority
```
standard → Normal processing
express  → Priority processing (+ fee)
urgent   → Immediate handling (+ premium fee)
```

### PickupType
```
warehouse_dropoff → Customer drops off at TEHTEK warehouse
pickup_request    → TEHTEK picks up from customer location
agent_collection  → Picked up from authorized agent point
```

### DeliveryType
```
door_delivery    → Delivered to receiver's address
agency_pickup    → Receiver collects from agent/branch
warehouse_pickup → Receiver collects from TEHTEK warehouse
```

### PackageCondition
```
intact  → No damage
damaged → Visible damage on receipt
opened  → Seal broken
wet     → Water damage
partial → Partial contents only
```

### Incoterm
```
dap → Delivered At Place (TEHTEK delivers, customer pays customs)
ddp → Delivered Duty Paid (TEHTEK handles everything)
exw → Ex Works (customer arranges from origin)
fob → Free On Board (seller delivers to port)
cif → Cost Insurance Freight (seller covers to destination port)
```

### InsuranceStatus
```
not_requested → Customer did not request insurance
requested     → Insurance requested, awaiting activation
active        → Insurance active on this shipment
claim_pending → Claim filed, under review
claim_paid    → Claim approved and paid out
claim_rejected → Claim rejected with reason
```

---

## 6. CARRIER & TRAVELER

### CarrierType
```
traveler      → Individual carrying packages in checked baggage (Air Express)
airline_cargo → Official airline cargo service
sea_carrier   → Sea freight carrier / shipping line
local_driver  → Local delivery driver (owned or contracted)
partner_agent → External logistics partner
```

### CarrierStatus
```
available  → Ready for assignment
assigned   → Assigned to a bag/shipment
in_transit → Currently carrying goods
arrived    → Arrived at destination
completed  → Assignment completed
cancelled  → Assignment cancelled
```

---

## 7. BAG / CONSOLIDATION

### BagType
```
bag          → Soft bag (Air Express — traveler)
carton       → Cardboard box consolidation (Air Cargo)
pallet       → Palletized freight
container_20ft → 20-foot sea container
container_40ft → 40-foot sea container
```

### BagStatus
```
open                → Accepting packages
sealed              → Sealed, no more packages accepted
assigned_to_carrier → Assigned to traveler or carrier
checked_in          → Checked in at airport/port
in_transit          → En route
arrived             → Arrived at destination
customs_clearance   → Under customs review
customs_cleared     → Customs approved
being_unpacked      → Packages being sorted
closed              → All packages processed
```

---

## 8. TRACKING

### TrackingEventType
```
order_created         → Shipment order placed
package_received      → Package physically received at warehouse
weight_measured       → Weight and dimensions recorded
photos_uploaded       → Package photos taken and uploaded
label_printed         → Tracking label generated and attached
warehoused            → Stored in warehouse
assigned_to_bag       → Added to bag/carton/container
bag_sealed            → Bag sealed for dispatch
assigned_to_carrier   → Assigned to traveler or carrier
carrier_checked_in    → Traveler checked in at airport/port
dispatched            → Left TEHTEK facility
arrived_hub           → Arrived at transit hub
customs_submitted     → Customs documents submitted
customs_cleared       → Customs approved
customs_held          → Held at customs
bag_arrived           → Bag/container arrived at destination
bag_opened            → Bag being unpacked
package_extracted     → Package removed from bag
out_for_delivery      → With delivery agent
delivery_attempted    → Delivery tried, receiver not available
delivered             → Received by customer/receiver ✅
delivery_failed       → Could not deliver
returned              → Return initiated
storage_started       → Package in storage (post-arrival)
storage_fee_applied   → Storage fee charged
abandoned_flagged     → Marked as potentially abandoned
exception_raised      → Issue reported (see exception)
status_updated        → Manual status update by staff
note_added            → Internal note added
```

---

## 9. INVOICE & PAYMENT

### InvoiceType
```
shipment            → Invoice for cargo/shipping service
retail_sale         → Invoice for product sale
purchase            → Invoice from supplier to TEHTEK
service             → Invoice for IT/Security/Solar service
proforma            → Proforma / quotation invoice
credit_note         → Credit issued to customer
storage_fee         → Invoice for storage charges
insurance           → Invoice for shipment insurance
it_service          → IT service invoice
solar_project       → Solar project invoice
maintenance_contract → Maintenance/AMC contract invoice
emergency_service   → Emergency intervention invoice
commission_payout   → Commission payment to partner
```

### InvoiceStatus
```
draft      → Being prepared
sent       → Sent to customer
viewed     → Customer opened the invoice
partial    → Partially paid
paid       → Fully paid ✅
overdue    → Past due date, unpaid
disputed   → Customer raised a dispute
cancelled  → Cancelled (mandatory reason required)
written_off → Declared uncollectable (CFO approval required)
```

### PaymentMethod
```
cash            → Physical cash
mobile_money    → MTN MoMo / Orange Money
bank_transfer   → Wire transfer
card            → Debit/credit card
cheque          → Bank cheque
crypto          → Cryptocurrency
tehmoney_wallet → Internal TehMoney wallet (future)
credit          → Customer credit balance used
```

### PaymentStatus
```
pending   → Payment initiated but not confirmed
confirmed → Payment confirmed and reconciled ✅
failed    → Payment attempt failed
refunded  → Payment returned to customer
partial   → Partial payment received
disputed  → Payment under dispute
```

---

## 10. STOCK & INVENTORY

### StockCategory
```
electronics        → Phones, computers, gadgets
accessories        → Cables, cases, peripherals
office_supplies    → Paper, stationery, equipment
raw_material       → Manufacturing inputs
finished_good      → Ready-to-sell product
consumable         → Single-use items
spare_part         → Replacement parts
packaging          → Boxes, wrapping, labels
solar_equipment    → Panels, inverters, batteries
security_equipment → Cameras, sensors, access control devices
network_equipment  → Routers, switches, cables
it_equipment       → Servers, UPS, network devices
```

### StockStatus
```
in_stock     → Quantity above minimum threshold
low_stock    → Below minimum threshold — alert triggered
out_of_stock → Zero quantity available
discontinued → No longer stocked
on_order     → Purchase order placed, awaiting arrival
reserved     → Allocated to an order, not yet dispatched
```

### StockMovementType
```
purchase_received    → Stock received from supplier
sale_dispatched      → Stock dispatched to customer
return_received      → Returned item added back to stock
adjustment_add       → Manual stock addition (reason required)
adjustment_remove    → Manual stock removal (reason required)
damage_write_off     → Damaged goods removed from stock
transfer_out         → Transferred to another branch
transfer_in          → Received from another branch
reservation_placed   → Reserved for an order (quantity held)
reservation_expired  → Reservation time limit passed, stock released
reservation_released → Released manually before expiry
project_consumed     → Stock consumed by a service/installation project
```

---

## 11. ORDER

### OrderType
```
sale_order     → TEHTEK selling to customer
purchase_order → TEHTEK buying from supplier
return_order   → Customer returning goods to TEHTEK
transfer_order → Stock moving between branches
special_order  → Product not in stock, procured on request
```

### OrderStatus
```
draft               → Being created
pending             → Awaiting confirmation
confirmed           → Confirmed by staff
deposit_required    → Special order awaiting deposit
deposit_paid        → Deposit received, procurement started
processing          → Being prepared/packed
ready               → Ready for pickup or dispatch
shipped             → Dispatched to customer
delivered           → Received by customer ✅
cancelled           → Cancelled (reason required)
on_hold             → Paused (unpaid, dispute, or other issue)
reservation_expired → Unpaid reservation auto-cancelled
```

### ReservationStatus
```
active    → Stock held, awaiting payment
paid      → Payment confirmed, reservation converted to order
expired   → Time limit passed, stock released automatically
cancelled → Manually cancelled by staff or customer
```

---

## 12. INFRASTRUCTURE SERVICES (IT + SECURITY + SOLAR)

### ServiceType
```
# IT Infrastructure
server_installation | server_maintenance | network_installation
router_configuration | switch_configuration | firewall_setup
vpn_setup | wifi_deployment | cloud_setup | backup_setup
email_domain_setup | microsoft365_setup | google_workspace_setup
software_installation | cybersecurity_support | it_consulting
office_it_support

# Security Systems
cctv_installation | cctv_monitoring | ip_camera_setup | dvr_nvr_setup
biometric_installation | fingerprint_system | face_recognition_setup
smart_lock_installation | gate_automation | electric_fence_setup
alarm_system_setup | motion_sensor_setup | intrusion_detection
fire_alarm_setup | smoke_detection | security_lighting
guard_monitoring_setup

# Smart Systems
smart_home_installation | smart_office_automation | hotel_smart_access
airbnb_smart_locks | remote_property_monitoring | energy_monitoring
iot_setup | building_access_management

# Solar & Energy
solar_installation | solar_maintenance | battery_backup_setup
inverter_installation | ups_installation | generator_hybrid_setup
energy_audit | site_survey | solar_upgrade | power_optimization
street_light_installation | industrial_power_setup | data_center_backup

# General
maintenance_contract | emergency_support | amc_contract | managed_service
```

### ServiceTicketStatus
```
draft               → Being created
scheduled           → Date and technician planned
assigned            → Technician formally assigned
site_visit_required → Needs site inspection before work
quotation_sent      → Quotation sent to customer
approved            → Customer approved the work
in_progress         → Work underway
waiting_parts       → Paused — waiting for parts/equipment
waiting_customer    → Paused — waiting for customer action
completed           → Work done, report submitted, customer signed
invoiced            → Invoice generated and sent
paid                → Invoice paid ✅
under_warranty      → Within warranty period
cancelled           → Cancelled with reason
```

### ContractType
```
one_time              → Single job, no recurring
monthly_maintenance   → Monthly recurring maintenance
quarterly_maintenance → Quarterly recurring maintenance
annual_sla            → Annual service level agreement
emergency_support     → Emergency-only coverage
managed_service       → Full managed IT/infrastructure service
amc                   → Annual Maintenance Contract
```

### SolarProjectStatus
```
lead           → Initial enquiry / lead
site_survey    → Site assessment in progress
quotation_sent → Quotation prepared and sent
approved       → Customer approved, deposit required
design_phase   → System design and engineering
procurement    → Equipment being sourced/ordered
installation   → Physical installation in progress
testing        → System testing and commissioning
commissioned   → System live and operational ✅
under_warranty → Within warranty period
maintenance    → Ongoing maintenance phase
completed      → Project fully closed
cancelled      → Project cancelled
```

### EnergySystemType
```
off_grid           → Fully off-grid solar system
on_grid            → Grid-tied solar system
hybrid             → Solar + grid hybrid
ups_backup         → UPS-only backup system
generator_hybrid   → Solar + generator combination
solar_street_light → Solar-powered street lighting
commercial_backup  → Commercial power backup system
industrial_power   → Industrial-scale power solution
```

### ProjectPriority
```
standard  → Normal processing
urgent    → Priority handling
emergency → Immediate dispatch required
```

### WarrantyStatus
```
active        → Warranty active
expired       → Warranty period ended
voided        → Warranty voided (misuse/tampering)
claimed       → Warranty claim processed
claim_pending → Warranty claim under review
```

---

## 13. CASH SESSION

### CashSessionStatus
```
open                → Cashier session active — accepting payments
closed              → Session closed, cash reconciled ✅
discrepancy_flagged → Mismatch between expected and counted cash
approved            → Manager approved session close (with or without discrepancy)
```

---

## 14. APPROVAL & WORKFLOW

### ApprovalStatus
```
pending   → Awaiting decision
approved  → Approved by authorized person ✅
rejected  → Rejected with mandatory reason
escalated → Sent to higher authority
expired   → No decision within time limit
cancelled → Withdrawn before decision
```

### ApprovalType
```
refund_request               → Customer refund approval
price_override               → Price change on confirmed order/invoice
discount_approval            → Discount above staff threshold
vip_upgrade                  → Customer VIP status grant
blacklist_override           → Allow blacklisted customer to transact
shipment_release             → Release shipment despite unpaid invoice
invoice_write_off            → Declare invoice uncollectable
stock_adjustment             → Manual stock count change
customs_override             → Handle customs exception
payment_extension            → Grant extra time to pay
storage_fee_waiver           → Waive storage fee
reservation_extension        → Extend stock reservation beyond limit
deposit_waiver               → Waive deposit requirement (special order)
insurance_claim              → Approve insurance compensation
abandoned_disposal           → Authorize disposal of abandoned package
cash_discrepancy             → Approve cash session with mismatch
emergency_fee_waiver         → Waive emergency service fee
project_budget_override      → Approve budget change on project
warranty_claim               → Approve warranty repair/replacement
commission_payout            → Approve commission payment to partner
commission_dispute_resolution → Resolve commission dispute
```

---

## 15. EXCEPTION

### ExceptionType
```
partial_payment          → Customer paid less than invoice total
payment_dispute          → Customer disputes the charge
lost_package             → Package cannot be located
damaged_goods            → Goods damaged in transit or at intake
wrong_delivery           → Delivered to wrong address
customs_seizure          → Package seized at customs
customs_additional_fee   → Extra customs duty required
delivery_refused         → Receiver refused delivery
address_not_found        → Delivery address incorrect or missing
customer_unreachable     → Cannot contact receiver
vip_override_request     → VIP customer requests policy exception
force_majeure            → Uncontrollable external event
staff_error              → Error caused by TEHTEK staff
supplier_error           → Supplier sent wrong/damaged goods
storage_overdue          → Customer not collected after deadline
abandoned_package        → Package declared abandoned
prohibited_item_found    → Prohibited item discovered at intake
false_declaration        → Customer declared incorrect value/contents
traveler_no_show         → Assigned traveler did not appear
bag_discrepancy          → Bag contents don't match manifest
insurance_claim          → Insurance claim filed
cash_discrepancy         → Cashier cash session mismatch
reservation_expired      → Unpaid reservation auto-cancelled
service_delay            → Service job cannot be completed on schedule
parts_unavailable        → Required parts not in stock
technician_unavailable   → Assigned technician cannot attend
site_access_denied       → Technician cannot access site
equipment_failure        → Installed equipment malfunctioned
warranty_dispute         → Customer disputes warranty coverage
solar_system_fault       → Installed solar system malfunction
power_grid_issue         → Grid-related power issue affecting system
commission_dispute       → Commission partner disputes amount
commission_fraud_flag    → Potential commission fraud detected
auth_replay_attack       → Used refresh token presented again — session invalidated ★ NEW
unauthorized_access      → Request to protected route without valid token ★ NEW
```

### ExceptionStatus
```
open      → Reported, not yet handled
in_review → Being investigated
resolved  → Resolved with documented outcome
escalated → Sent to higher authority
closed    → Closed (resolved or written off)
```

---

## 16. SEQUENCE REGISTRY

### SequenceType and Formats
```
tracking_number   → TRK-[ROUTE]-[YEAR]-[000000]    e.g. TRK-CNACM-2026-000142
invoice_number    → INV-[YEAR]-[MM]-[000000]         e.g. INV-2026-04-000089
customer_code     → CUS-[000000]                     e.g. CUS-000034
order_number      → ORD-[YEAR]-[000000]              e.g. ORD-2026-000201
receipt_number    → RCP-[YEAR]-[MM]-[000000]         e.g. RCP-2026-04-000055
pickup_number     → PKP-[YEAR]-[000000]              e.g. PKP-2026-000018
bag_number        → BAG-[TYPE]-[YEAR]-[0000]         e.g. BAG-AIR-2026-0012
service_ticket    → SVC-[YEAR]-[000000]              e.g. SVC-2026-000045
project_number    → PRJ-[YEAR]-[000000]              e.g. PRJ-2026-000007
contract_number   → CNT-[YEAR]-[000000]              e.g. CNT-2026-000003
commission_record → COM-[YEAR]-[000000]              e.g. COM-2026-000019
payout_number     → PAY-[YEAR]-[MM]-[000000]         e.g. PAY-2026-04-000008
```

---

## 17. NOTIFICATION

### NotificationChannel
```
whatsapp → WhatsApp Business message (primary in Cameroon)
sms      → SMS text message
email    → Email
in_app   → In-app notification
push     → Mobile push notification
```

### NotificationStatus
```
pending → Queued to send
sent    → Successfully delivered
failed  → Delivery failed
read    → Recipient opened/read
```

### NotificationType
```
# Cargo
shipment_created | package_received | assigned_to_bag
shipment_dispatched | customs_update | out_for_delivery
delivered | delivery_failed | storage_fee_warning
storage_fee_applied | abandoned_warning

# Finance
invoice_sent | payment_received | payment_overdue
payment_partial | receipt_generated

# Infrastructure Services
service_ticket_created | technician_assigned | technician_enroute
service_completed | service_report_ready | warranty_expiring
contract_renewal_due | maintenance_scheduled | emergency_dispatched

# Solar
site_survey_scheduled | quotation_ready | project_started
installation_completed | system_commissioned | maintenance_due
battery_low_alert | system_fault_alert

# Customer Account
vip_status_granted | account_suspended | kyc_approved | kyc_rejected

# Reservations & Orders
reservation_expiring | reservation_expired | special_order_ready

# Commissions
commission_approved | commission_paid | commission_disputed
new_lead_converted | payout_processed

# Security & Auth ★ NEW
auth_token_expired | suspicious_login_attempt | account_locked
session_invalidated | password_changed | new_login_detected

# System
exception_raised | insurance_claim_update
```

---

## 18. AUTHENTICATION ★ NEW

### AuditAction
All values used in user_audit_logs.action field.
```
# Authentication
login_success          → Successful login
login_failed           → Failed login attempt
logout                 → User logged out
token_refreshed        → Access token refreshed via refresh token
token_replay_detected  → Used refresh token presented — security event
password_reset_requested → Password reset email/SMS sent
password_reset_completed → Password successfully reset
account_locked         → Account locked after failed attempts
account_unlocked       → Account manually unlocked by admin
mfa_enabled            → MFA turned on
mfa_disabled           → MFA turned off

# User Management
user_created           → New user created
user_updated           → User profile updated
user_suspended         → User suspended
user_reactivated       → User reactivated
user_deleted           → User soft-deleted
role_assigned          → Role added to user
role_removed           → Role removed from user
permission_flag_added  → Individual permission flag added
permission_flag_removed → Individual permission flag removed

# Financial Actions
invoice_cancelled      → Invoice cancelled
invoice_written_off    → Invoice written off (CFO approval)
price_overridden       → Price changed on confirmed invoice
refund_approved        → Refund approved
cash_discrepancy_approved → Cash discrepancy session approved

# Customer Actions
customer_blacklisted   → Customer blacklisted
customer_unblacklisted → Blacklist removed
vip_granted            → VIP status granted
vip_revoked            → VIP status removed
kyc_approved           → KYC documents approved
kyc_rejected           → KYC documents rejected

# Shipment Actions
shipment_released      → Shipment released (with or without payment override)
declaration_accepted   → Customer accepted liability declaration (SR-008)
prohibited_check_done  → Warehouse prohibited item check completed (SR-009)

# Commission Actions
commission_payout_approved → Commission payout approved
commission_dispute_resolved → Commission dispute resolved
commission_fraud_flagged → Fraud flag set on commission
```

---

## ENUM RULES

1. All enums are string type — never integers
2. All values are lowercase_with_underscores
3. New enum → update this document first → then add to app/core/enums.py → then migrate
4. Deprecated enums are marked as deprecated — never deleted from database
5. Frontend TypeScript types in types/ must mirror these exactly
6. API responses always return the string value, never an integer index
