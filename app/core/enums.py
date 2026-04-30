"""
TEHTEK — Master Enums  (TEHTEK_ENUMS.md v1.4)
Single source of truth. NEVER define enums anywhere else.
All values: lowercase_with_underscores strings.
"""
from enum import Enum


# ── 1. USER & ACCESS ─────────────────────────────────────────────────────────

class UserStatus(str, Enum):
    active    = "active"
    inactive  = "inactive"
    suspended = "suspended"
    pending   = "pending"

class UserType(str, Enum):
    internal           = "internal"
    external           = "external"
    referral           = "referral"
    commission_partner = "commission_partner"

class KYCStatus(str, Enum):
    not_submitted = "not_submitted"
    pending       = "pending"
    verified      = "verified"
    rejected      = "rejected"
    expired       = "expired"

class KYCLevel(str, Enum):
    basic    = "basic"
    standard = "standard"
    enhanced = "enhanced"

class AuthTokenType(str, Enum):
    access  = "access"
    refresh = "refresh"
    reset   = "reset"


# ── 2. COMPANY & STRUCTURE ───────────────────────────────────────────────────

class CompanyType(str, Enum):
    parent     = "parent"
    subsidiary = "subsidiary"
    branch     = "branch"
    partner    = "partner"

class BranchType(str, Enum):
    headquarters      = "headquarters"
    cargo_hub         = "cargo_hub"
    retail_store      = "retail_store"
    warehouse         = "warehouse"
    agency            = "agency"
    procurement       = "procurement"
    it_service_center = "it_service_center"

class DepartmentType(str, Enum):
    operations              = "operations"
    finance                 = "finance"
    hr                      = "hr"
    sales                   = "sales"
    logistics               = "logistics"
    warehouse               = "warehouse"
    it                      = "it"
    legal                   = "legal"
    executive               = "executive"
    customer_service        = "customer_service"
    infrastructure_services = "infrastructure_services"


# ── 3. CUSTOMER ──────────────────────────────────────────────────────────────

class CustomerType(str, Enum):
    retail           = "retail"
    corporate        = "corporate"
    vip              = "vip"
    shipping         = "shipping"
    vendor           = "vendor"
    supplier         = "supplier"
    referral_partner = "referral_partner"
    property_client  = "property_client"
    fleet_client     = "fleet_client"
    tenant           = "tenant"
    hotel_guest      = "hotel_guest"
    it_service_client = "it_service_client"
    solar_client     = "solar_client"

class CustomerRiskLevel(str, Enum):
    low         = "low"
    medium      = "medium"
    high        = "high"
    blacklisted = "blacklisted"

class CustomerStatus(str, Enum):
    active      = "active"
    inactive    = "inactive"
    suspended   = "suspended"
    blacklisted = "blacklisted"


# ── 4. COMMISSION PARTNER ────────────────────────────────────────────────────

class CommissionPartnerType(str, Enum):
    referral_agent                    = "referral_agent"
    sales_commission_partner          = "sales_commission_partner"
    corporate_introducer              = "corporate_introducer"
    cargo_lead_agent                  = "cargo_lead_agent"
    procurement_connector             = "procurement_connector"
    property_referral_partner         = "property_referral_partner"
    vehicle_sales_broker              = "vehicle_sales_broker"
    infrastructure_project_introducer = "infrastructure_project_introducer"
    vip_client_connector              = "vip_client_connector"
    independent_business_partner      = "independent_business_partner"

class CommissionPartnerStatus(str, Enum):
    active      = "active"
    suspended   = "suspended"
    blacklisted = "blacklisted"
    inactive    = "inactive"

class CommissionStatus(str, Enum):
    pending   = "pending"
    payable   = "payable"
    paid      = "paid"
    disputed  = "disputed"
    cancelled = "cancelled"
    on_hold   = "on_hold"

class CommissionPayoutStatus(str, Enum):
    pending   = "pending"
    approved  = "approved"
    processed = "processed"
    failed    = "failed"
    cancelled = "cancelled"

class CommissionDisputeStatus(str, Enum):
    open                 = "open"
    in_review            = "in_review"
    resolved_for_partner = "resolved_for_partner"
    resolved_for_tehtek  = "resolved_for_tehtek"
    escalated            = "escalated"
    closed               = "closed"


# ── 5. SHIPMENT ──────────────────────────────────────────────────────────────

class ShipmentType(str, Enum):
    air_express   = "air_express"
    air_cargo     = "air_cargo"
    sea_freight   = "sea_freight"
    land_freight  = "land_freight"
    local_express = "local_express"

class ShipmentRoute(str, Enum):
    china_cameroon  = "china_cameroon"
    usa_cameroon    = "usa_cameroon"
    europe_cameroon = "europe_cameroon"
    cameroon_china  = "cameroon_china"
    cameroon_usa    = "cameroon_usa"
    cameroon_local  = "cameroon_local"
    cameroon_africa = "cameroon_africa"

class ShipmentStatus(str, Enum):
    draft               = "draft"
    confirmed           = "confirmed"
    package_received    = "package_received"
    warehoused          = "warehoused"
    ready_for_dispatch  = "ready_for_dispatch"
    assigned_to_bag     = "assigned_to_bag"
    assigned_to_carrier = "assigned_to_carrier"
    in_transit          = "in_transit"
    arrived_destination = "arrived_destination"
    customs_clearance   = "customs_clearance"
    customs_cleared     = "customs_cleared"
    customs_held        = "customs_held"
    customs_seized      = "customs_seized"
    storage_pending     = "storage_pending"
    storage_fee_applied = "storage_fee_applied"
    abandoned           = "abandoned"
    out_for_delivery    = "out_for_delivery"
    delivered           = "delivered"
    delivery_failed     = "delivery_failed"
    returned_to_sender  = "returned_to_sender"
    lost                = "lost"
    cancelled           = "cancelled"

class ShipmentPriority(str, Enum):
    standard = "standard"
    express  = "express"
    urgent   = "urgent"

class PickupType(str, Enum):
    warehouse_dropoff = "warehouse_dropoff"
    pickup_request    = "pickup_request"
    agent_collection  = "agent_collection"

class DeliveryType(str, Enum):
    door_delivery    = "door_delivery"
    agency_pickup    = "agency_pickup"
    warehouse_pickup = "warehouse_pickup"

class PackageCondition(str, Enum):
    intact  = "intact"
    damaged = "damaged"
    opened  = "opened"
    wet     = "wet"
    partial = "partial"

class Incoterm(str, Enum):
    dap = "dap"
    ddp = "ddp"
    exw = "exw"
    fob = "fob"
    cif = "cif"

class InsuranceStatus(str, Enum):
    not_requested  = "not_requested"
    requested      = "requested"
    active         = "active"
    claim_pending  = "claim_pending"
    claim_paid     = "claim_paid"
    claim_rejected = "claim_rejected"


# ── 6. CARRIER & TRAVELER ────────────────────────────────────────────────────

class CarrierType(str, Enum):
    traveler      = "traveler"
    airline_cargo = "airline_cargo"
    sea_carrier   = "sea_carrier"
    local_driver  = "local_driver"
    partner_agent = "partner_agent"

class CarrierStatus(str, Enum):
    available  = "available"
    assigned   = "assigned"
    in_transit = "in_transit"
    arrived    = "arrived"
    completed  = "completed"
    cancelled  = "cancelled"


# ── 7. BAG / CONSOLIDATION ───────────────────────────────────────────────────

class BagType(str, Enum):
    bag            = "bag"
    carton         = "carton"
    pallet         = "pallet"
    container_20ft = "container_20ft"
    container_40ft = "container_40ft"

class BagStatus(str, Enum):
    open                = "open"
    sealed              = "sealed"
    assigned_to_carrier = "assigned_to_carrier"
    checked_in          = "checked_in"
    in_transit          = "in_transit"
    arrived             = "arrived"
    customs_clearance   = "customs_clearance"
    customs_cleared     = "customs_cleared"
    being_unpacked      = "being_unpacked"
    closed              = "closed"


# ── 8. TRACKING ──────────────────────────────────────────────────────────────

class TrackingEventType(str, Enum):
    order_created       = "order_created"
    package_received    = "package_received"
    weight_measured     = "weight_measured"
    photos_uploaded     = "photos_uploaded"
    label_printed       = "label_printed"
    warehoused          = "warehoused"
    assigned_to_bag     = "assigned_to_bag"
    bag_sealed          = "bag_sealed"
    assigned_to_carrier = "assigned_to_carrier"
    carrier_checked_in  = "carrier_checked_in"
    dispatched          = "dispatched"
    arrived_hub         = "arrived_hub"
    customs_submitted   = "customs_submitted"
    customs_cleared     = "customs_cleared"
    customs_held        = "customs_held"
    bag_arrived         = "bag_arrived"
    bag_opened          = "bag_opened"
    package_extracted   = "package_extracted"
    out_for_delivery    = "out_for_delivery"
    delivery_attempted  = "delivery_attempted"
    delivered           = "delivered"
    delivery_failed     = "delivery_failed"
    returned            = "returned"
    storage_started     = "storage_started"
    storage_fee_applied = "storage_fee_applied"
    abandoned_flagged   = "abandoned_flagged"
    exception_raised    = "exception_raised"
    status_updated      = "status_updated"
    note_added          = "note_added"


# ── 9. INVOICE & PAYMENT ─────────────────────────────────────────────────────

class InvoiceType(str, Enum):
    shipment             = "shipment"
    retail_sale          = "retail_sale"
    purchase             = "purchase"
    service              = "service"
    proforma             = "proforma"
    credit_note          = "credit_note"
    storage_fee          = "storage_fee"
    insurance            = "insurance"
    it_service           = "it_service"
    solar_project        = "solar_project"
    maintenance_contract = "maintenance_contract"
    emergency_service    = "emergency_service"
    commission_payout    = "commission_payout"

class InvoiceStatus(str, Enum):
    draft       = "draft"
    sent        = "sent"
    viewed      = "viewed"
    partial     = "partial"
    paid        = "paid"
    overdue     = "overdue"
    disputed    = "disputed"
    cancelled   = "cancelled"
    written_off = "written_off"

class PaymentMethod(str, Enum):
    cash            = "cash"
    mobile_money    = "mobile_money"
    bank_transfer   = "bank_transfer"
    card            = "card"
    cheque          = "cheque"
    crypto          = "crypto"
    tehmoney_wallet = "tehmoney_wallet"
    credit          = "credit"

class PaymentStatus(str, Enum):
    pending   = "pending"
    confirmed = "confirmed"
    failed    = "failed"
    refunded  = "refunded"
    partial   = "partial"
    disputed  = "disputed"


# ── 10. STOCK & INVENTORY ────────────────────────────────────────────────────

class StockCategory(str, Enum):
    electronics        = "electronics"
    accessories        = "accessories"
    office_supplies    = "office_supplies"
    raw_material       = "raw_material"
    finished_good      = "finished_good"
    consumable         = "consumable"
    spare_part         = "spare_part"
    packaging          = "packaging"
    solar_equipment    = "solar_equipment"
    security_equipment = "security_equipment"
    network_equipment  = "network_equipment"
    it_equipment       = "it_equipment"

class StockStatus(str, Enum):
    in_stock     = "in_stock"
    low_stock    = "low_stock"
    out_of_stock = "out_of_stock"
    discontinued = "discontinued"
    on_order     = "on_order"
    reserved     = "reserved"

class StockMovementType(str, Enum):
    purchase_received    = "purchase_received"
    sale_dispatched      = "sale_dispatched"
    return_received      = "return_received"
    adjustment_add       = "adjustment_add"
    adjustment_remove    = "adjustment_remove"
    damage_write_off     = "damage_write_off"
    transfer_out         = "transfer_out"
    transfer_in          = "transfer_in"
    reservation_placed   = "reservation_placed"
    reservation_expired  = "reservation_expired"
    reservation_released = "reservation_released"
    project_consumed     = "project_consumed"


# ── 11. ORDER ────────────────────────────────────────────────────────────────

class OrderType(str, Enum):
    sale_order     = "sale_order"
    purchase_order = "purchase_order"
    return_order   = "return_order"
    transfer_order = "transfer_order"
    special_order  = "special_order"

class OrderStatus(str, Enum):
    draft               = "draft"
    pending             = "pending"
    confirmed           = "confirmed"
    deposit_required    = "deposit_required"
    deposit_paid        = "deposit_paid"
    processing          = "processing"
    ready               = "ready"
    shipped             = "shipped"
    delivered           = "delivered"
    cancelled           = "cancelled"
    on_hold             = "on_hold"
    reservation_expired = "reservation_expired"

class ReservationStatus(str, Enum):
    active    = "active"
    paid      = "paid"
    expired   = "expired"
    cancelled = "cancelled"


# ── 12. INFRASTRUCTURE SERVICES ──────────────────────────────────────────────

class ServiceTicketStatus(str, Enum):
    draft               = "draft"
    scheduled           = "scheduled"
    assigned            = "assigned"
    site_visit_required = "site_visit_required"
    quotation_sent      = "quotation_sent"
    approved            = "approved"
    in_progress         = "in_progress"
    waiting_parts       = "waiting_parts"
    waiting_customer    = "waiting_customer"
    completed           = "completed"
    invoiced            = "invoiced"
    paid                = "paid"
    under_warranty      = "under_warranty"
    cancelled           = "cancelled"

class ContractType(str, Enum):
    one_time              = "one_time"
    monthly_maintenance   = "monthly_maintenance"
    quarterly_maintenance = "quarterly_maintenance"
    annual_sla            = "annual_sla"
    emergency_support     = "emergency_support"
    managed_service       = "managed_service"
    amc                   = "amc"

class SolarProjectStatus(str, Enum):
    lead           = "lead"
    site_survey    = "site_survey"
    quotation_sent = "quotation_sent"
    approved       = "approved"
    design_phase   = "design_phase"
    procurement    = "procurement"
    installation   = "installation"
    testing        = "testing"
    commissioned   = "commissioned"
    under_warranty = "under_warranty"
    maintenance    = "maintenance"
    completed      = "completed"
    cancelled      = "cancelled"

class EnergySystemType(str, Enum):
    off_grid           = "off_grid"
    on_grid            = "on_grid"
    hybrid             = "hybrid"
    ups_backup         = "ups_backup"
    generator_hybrid   = "generator_hybrid"
    solar_street_light = "solar_street_light"
    commercial_backup  = "commercial_backup"
    industrial_power   = "industrial_power"

class ProjectPriority(str, Enum):
    standard  = "standard"
    urgent    = "urgent"
    emergency = "emergency"

class WarrantyStatus(str, Enum):
    active        = "active"
    expired       = "expired"
    voided        = "voided"
    claimed       = "claimed"
    claim_pending = "claim_pending"


# ── 13. CASH SESSION ─────────────────────────────────────────────────────────

class CashSessionStatus(str, Enum):
    open                = "open"
    closed              = "closed"
    discrepancy_flagged = "discrepancy_flagged"
    approved            = "approved"


# ── 14. APPROVAL & WORKFLOW ──────────────────────────────────────────────────

class ApprovalStatus(str, Enum):
    pending   = "pending"
    approved  = "approved"
    rejected  = "rejected"
    escalated = "escalated"
    expired   = "expired"
    cancelled = "cancelled"

class ApprovalType(str, Enum):
    refund_request               = "refund_request"
    price_override               = "price_override"
    discount_approval            = "discount_approval"
    vip_upgrade                  = "vip_upgrade"
    blacklist_override           = "blacklist_override"
    shipment_release             = "shipment_release"
    invoice_write_off            = "invoice_write_off"
    stock_adjustment             = "stock_adjustment"
    customs_override             = "customs_override"
    payment_extension            = "payment_extension"
    storage_fee_waiver           = "storage_fee_waiver"
    reservation_extension        = "reservation_extension"
    deposit_waiver               = "deposit_waiver"
    insurance_claim              = "insurance_claim"
    abandoned_disposal           = "abandoned_disposal"
    cash_discrepancy             = "cash_discrepancy"
    emergency_fee_waiver         = "emergency_fee_waiver"
    project_budget_override      = "project_budget_override"
    warranty_claim               = "warranty_claim"
    commission_payout            = "commission_payout"
    commission_dispute_resolution = "commission_dispute_resolution"


# ── 15. EXCEPTION ────────────────────────────────────────────────────────────

class ExceptionType(str, Enum):
    partial_payment        = "partial_payment"
    payment_dispute        = "payment_dispute"
    lost_package           = "lost_package"
    damaged_goods          = "damaged_goods"
    wrong_delivery         = "wrong_delivery"
    customs_seizure        = "customs_seizure"
    customs_additional_fee = "customs_additional_fee"
    delivery_refused       = "delivery_refused"
    address_not_found      = "address_not_found"
    customer_unreachable   = "customer_unreachable"
    vip_override_request   = "vip_override_request"
    force_majeure          = "force_majeure"
    staff_error            = "staff_error"
    supplier_error         = "supplier_error"
    storage_overdue        = "storage_overdue"
    abandoned_package      = "abandoned_package"
    prohibited_item_found  = "prohibited_item_found"
    false_declaration      = "false_declaration"
    traveler_no_show       = "traveler_no_show"
    bag_discrepancy        = "bag_discrepancy"
    insurance_claim        = "insurance_claim"
    cash_discrepancy       = "cash_discrepancy"
    reservation_expired    = "reservation_expired"
    service_delay          = "service_delay"
    parts_unavailable      = "parts_unavailable"
    technician_unavailable = "technician_unavailable"
    site_access_denied     = "site_access_denied"
    equipment_failure      = "equipment_failure"
    warranty_dispute       = "warranty_dispute"
    solar_system_fault     = "solar_system_fault"
    power_grid_issue       = "power_grid_issue"
    commission_dispute     = "commission_dispute"
    commission_fraud_flag  = "commission_fraud_flag"
    auth_replay_attack     = "auth_replay_attack"
    unauthorized_access    = "unauthorized_access"

class ExceptionStatus(str, Enum):
    open      = "open"
    in_review = "in_review"
    resolved  = "resolved"
    escalated = "escalated"
    closed    = "closed"


# ── 16. SEQUENCE REGISTRY ────────────────────────────────────────────────────

class SequenceType(str, Enum):
    tracking_number   = "tracking_number"
    invoice_number    = "invoice_number"
    customer_code     = "customer_code"
    order_number      = "order_number"
    receipt_number    = "receipt_number"
    pickup_number     = "pickup_number"
    bag_number        = "bag_number"
    service_ticket    = "service_ticket"
    project_number    = "project_number"
    contract_number   = "contract_number"
    commission_record = "commission_record"
    payout_number     = "payout_number"


# ── 17. NOTIFICATION ─────────────────────────────────────────────────────────

class NotificationChannel(str, Enum):
    whatsapp = "whatsapp"
    sms      = "sms"
    email    = "email"
    in_app   = "in_app"
    push     = "push"

class NotificationStatus(str, Enum):
    pending = "pending"
    sent    = "sent"
    failed  = "failed"
    read    = "read"


# ── 18. AUTHENTICATION ───────────────────────────────────────────────────────

class AuditAction(str, Enum):
    # Auth
    login_success            = "login_success"
    login_failed             = "login_failed"
    logout                   = "logout"
    token_refreshed          = "token_refreshed"
    token_replay_detected    = "token_replay_detected"
    password_reset_requested = "password_reset_requested"
    password_reset_completed = "password_reset_completed"
    account_locked           = "account_locked"
    account_unlocked         = "account_unlocked"
    mfa_enabled              = "mfa_enabled"
    mfa_disabled             = "mfa_disabled"
    # User management
    user_created             = "user_created"
    user_updated             = "user_updated"
    user_suspended           = "user_suspended"
    user_reactivated         = "user_reactivated"
    user_deleted             = "user_deleted"
    role_assigned            = "role_assigned"
    role_removed             = "role_removed"
    permission_flag_added    = "permission_flag_added"
    permission_flag_removed  = "permission_flag_removed"
    # Financial
    invoice_cancelled        = "invoice_cancelled"
    invoice_written_off      = "invoice_written_off"
    price_overridden         = "price_overridden"
    refund_approved          = "refund_approved"
    cash_discrepancy_approved = "cash_discrepancy_approved"
    # Customer
    customer_blacklisted     = "customer_blacklisted"
    customer_unblacklisted   = "customer_unblacklisted"
    vip_granted              = "vip_granted"
    vip_revoked              = "vip_revoked"
    kyc_approved             = "kyc_approved"
    kyc_rejected             = "kyc_rejected"
    # Shipment
    shipment_released        = "shipment_released"
    declaration_accepted     = "declaration_accepted"
    prohibited_check_done    = "prohibited_check_done"
    # Commission
    commission_payout_approved = "commission_payout_approved"
    commission_dispute_resolved = "commission_dispute_resolved"
    commission_fraud_flagged = "commission_fraud_flagged"
