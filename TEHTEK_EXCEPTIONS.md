# TEHTEK — Exception Handling Matrix
# Version: 1.0 | April 2026
# Owner: Benjamin Boule Fogang
# Rule: If not in this document, staff must escalate — NEVER invent a resolution.
# Adding new exceptions: escalate first → document within 48h → implement next sprint

---

## HOW TO USE THIS DOCUMENT

Every exception has:
- TRIGGER: What causes this exception
- WHO HANDLES: Who is responsible for resolving it
- STATUS: What status to set on the affected record
- CUSTOMER ACTION: What the customer is told
- SYSTEM ACTION: What the system does automatically
- RESOLUTION OPTIONS: The allowed ways to close this exception
- ESCALATION: What happens if not resolved in time
- AUDIT: What must be logged

---

## ESCALATION TREE

```
Staff Member
    ↓ (unable to resolve in defined time)
Department Manager
    ↓ (above financial threshold or unresolved 24h)
Finance Manager / Shipping Manager / Infrastructure Services Manager
    ↓ (above 1,000,000 XAF or unresolved 48h)
CFO / COO
    ↓ (above 5,000,000 XAF or strategic impact)
Owner — Benjamin Boule Fogang (final authority)
```

---

## SECTION 1 — PAYMENT EXCEPTIONS

### EX-PAY-001 — Partial Payment Received
**Trigger:** Customer pays less than the invoice total.
**Who handles:** Accounts Receivable Clerk
**Status:** Invoice → partial | Shipment/service: still blocked for release
**Customer:** "We received your partial payment of [amount]. Outstanding balance: [amount]. Complete payment to release your shipment/service."
**System:** Create payment record. Update paid_amount. Recalculate balance. Resume overdue schedule on balance.
**Resolution:**
1. Customer pays balance → invoice → paid → release
2. Finance Manager approves release with outstanding balance (can_approve_shipment_release flag) → logged as exception
3. Payment extension granted (approval required) → new due_date set
**Escalation:** 7 days no payment → Finance Manager | 14 days → Owner
**Audit:** Payment record created. If override: approver, reason, amount, date.

---

### EX-PAY-002 — Payment Disputed by Customer
**Trigger:** Customer claims they paid but system shows unpaid, or customer disputes the amount charged.
**Who handles:** Finance Manager
**Status:** Invoice → disputed | Job/shipment → on hold
**Customer:** "Your payment dispute has been received. Reference: [dispute_id]. We will contact you within 24 hours."
**System:** Create exception record. Assign to Finance Manager. Freeze automatic overdue reminders during dispute.
**Resolution:**
1. Payment confirmed → invoice → paid → release → notify customer
2. Payment not found → customer provides proof → re-review
3. Error on TEHTEK side → issue credit note or corrected invoice
4. Dispute rejected → notify customer with explanation → resume normal flow
**Escalation:** Unresolved 48h → CFO
**Audit:** All communications logged. Decision and who decided logged.

---

### EX-PAY-003 — Overpayment Received
**Trigger:** Customer pays more than the invoice total.
**Who handles:** Accounts Receivable Clerk
**Status:** Invoice → paid | Excess → customer.credit_balance
**Customer:** "Thank you for your payment. Invoice [number] is paid. Excess [amount] added to your account credit."
**System:** Mark invoice paid. Create credit_balance record. Credit can be used on next invoice.
**Resolution:**
1. Customer accepts credit for future use → no action needed
2. Customer requests refund → can_approve_refund flag required → process refund
**Audit:** Overpayment logged. Credit record created. Refund (if any) with approver.

---

### EX-PAY-004 — Cash Discrepancy at Session Close
**Trigger:** Cashier cash_counted ≠ cash_expected at daily session close.
**Who handles:** Store Manager / Finance Manager
**Status:** CashSession → discrepancy_flagged
**Customer:** N/A — internal
**System:** Session locked. Alert sent to manager. ApprovalWorkflow created.
**Resolution:**
1. Recount confirms error → corrected, session closed normally
2. Discrepancy < 10,000 XAF → manager approves with reason → closed
3. Discrepancy > 10,000 XAF → Finance Manager approves
4. Discrepancy > 50,000 XAF → Owner notified, investigation before close
**Escalation:** Immediately if above 50,000 XAF.
**Audit:** Expected, counted, difference, who approved, reason — all logged.

---

## SECTION 2 — SHIPMENT EXCEPTIONS

### EX-SHP-001 — Package Lost in Transit
**Trigger:** Package cannot be located AND carrier confirms loss, OR package not arrived after 2× estimated time.
**Who handles:** Shipping Manager
**Status:** Shipment → lost | Invoice → on_hold
**Customer:** "We regret to inform you that your shipment [tracking] appears to be lost. A formal investigation has been opened. Reference: [id]. We will update you within 48 hours."
**System:** Create exception. Assign to Shipping Manager. Notify International Coordinator if international route. Flag for insurance claim if applicable.
**Resolution:**
1. Package found → update status, resume normal flow, notify customer
2. Confirmed lost → check declared_value + insurance → CFO approves compensation → credit note or refund
**Escalation:** 72h → Owner | Loss > 1,000,000 XAF → Owner immediately
**Audit:** Full investigation timeline. Compensation amount and approver.

---

### EX-SHP-002 — Damaged Goods
**Trigger:** Package or contents found damaged at warehouse intake, in transit, or on delivery.
**Who handles:** Warehouse Officer (discovery) → Shipping Manager (resolution)
**Status:** Package condition → damaged | Exception flag set on shipment
**Customer (at intake):** "We received your package with visible damage. Photos have been taken. A damage report has been filed. Reference: [id]."
**Customer (at delivery):** "Your package arrived damaged. Please keep the packaging. A damage claim has been opened. Reference: [id]."
**System:** Photos required and uploaded (mandatory). Exception created. Weight and condition logged.
**Resolution:**
1. Minor damage, customer accepts → delivery confirmed, damage note recorded
2. Significant damage → carrier claim filed, customer compensated
3. Customer refuses delivery → return process initiated
4. Insurance claim → process as EX-SHP-001 compensation flow
**Audit:** Photos stored permanently. Damage report logged. All communications logged.

---

### EX-SHP-003 — Delivery Failed — Receiver Not Available
**Trigger:** Driver/rider cannot complete delivery — receiver not present or reachable.
**Who handles:** Delivery Manager / Dispatch Controller
**Status:** Shipment → delivery_failed | Tracking event: delivery_attempted (with timestamp)
**Customer:** "Delivery of your shipment [tracking] was attempted on [date/time] but was unsuccessful. Contact us to reschedule. Reference: [id]."
**System:** Log attempt with timestamp and GPS location. Increment delivery_attempt_count.
**Resolution:**
1. Reschedule delivery → new attempt → status → out_for_delivery
2. Customer collects from branch/agency → delivery_type changed → customer notified
3. After 3rd failed attempt → return_to_sender initiated, storage fee may apply
4. Customer unreachable 7 days → return process started
**Escalation:** After 3rd failure → Delivery Manager + Finance Manager (for return cost).
**Audit:** Each attempt: time, driver, outcome, contact attempt details.

---

### EX-SHP-004 — Wrong Delivery Address
**Trigger:** Address provided is incorrect, incomplete, or does not exist.
**Who handles:** Customer Service → Delivery Manager
**Status:** Shipment → delivery_failed | Exception: address_not_found
**Customer:** "We were unable to locate the delivery address for [tracking]. Please contact us immediately with the correct address. An address correction fee may apply."
**System:** Halt delivery. Exception created. Package returned to nearest TEHTEK branch.
**Resolution:**
1. Customer provides correct address → new delivery scheduled, address correction fee applied
2. No response within 5 days → return_to_sender initiated
**Audit:** Original address. Delivery attempt logged. Address correction and any fees logged.

---

### EX-SHP-005 — Customs Seizure
**Trigger:** Customs authority seizes the package (prohibited items, undeclared value, missing documents).
**Who handles:** Customs Officer → Shipping Manager → Owner (if above threshold)
**Status:** Shipment → customs_seized
**Customer:** "Your shipment [tracking] has been seized by customs authorities. Please contact us immediately. Reference: [id]."
**System:** Immediate notification to Customs Officer and Shipping Manager. Invoice → on_hold. Document checklist generated.
**Resolution:**
1. Documents provided, customs releases → customs_cleared → resume normal flow
2. Additional duty required → customer billed → paid → release (EX-SHP-006)
3. Prohibited items → confiscated → TEHTEK not liable per SR-008 (customer accepted liability)
4. Legal dispute → escalate to Legal/Compliance Officer
**Escalation:** Immediately to Shipping Manager | 48h → Owner | Confiscation → Owner immediately
**Audit:** All customs communications. Documents submitted. Resolution logged.

---

### EX-SHP-006 — Customs Additional Fee Required
**Trigger:** Customs requires additional duty payment not included in original invoice.
**Who handles:** Customs Officer → Accounts Receivable
**Status:** Shipment stays at customs_clearance (held pending payment)
**Customer:** "Customs authorities have assessed an additional duty of [amount] on your shipment [tracking]. A supplementary invoice has been generated. Payment is required before release."
**System:** Supplementary invoice created (InvoiceType: shipment). Sent to customer. Shipment held.
**Resolution:**
1. Customer pays → release → resume normal flow
2. Customer disputes → refer to EX-PAY-002
3. TEHTEK absorbs cost → CFO approval, can_override_price flag required
**Audit:** Original declared value vs customs assessed value. Who absorbed cost if applicable.

---

### EX-SHP-007 — Prohibited Item Found at Intake
**Trigger:** Warehouse staff discovers prohibited item during intake screening (SR-009).
**Who handles:** Warehouse Manager → Shipping Manager
**Status:** Shipment → cancelled
**Customer:** "We have discovered that your package contains items we cannot accept for shipping ([item type]). We will contact you to arrange collection or disposal of the item."
**System:** Exception created. Package quarantined. Customer notified immediately.
**Resolution:**
1. Customer collects prohibited item → item removed → repack without prohibited item → new shipment
2. Customer cannot collect → disposal (Owner approval required, photos taken)
3. Authorities notified if legally required (weapons, narcotics, etc.)
**Audit:** Prohibited item type logged. Photos taken. Who discovered and when. Outcome logged.

---

### EX-SHP-008 — False Declaration Discovered
**Trigger:** Actual contents or declared value differs significantly from customer declaration.
**Who handles:** Customs Officer / Warehouse Manager → Shipping Manager
**Status:** Shipment → customs_held or cancelled (depending on severity)
**Customer:** "The contents/value of your shipment do not match your declaration. This is a serious violation. You accepted full responsibility per our shipping terms. Customs penalties may apply."
**System:** Exception: false_declaration. Invoice revised to actual value. Customer liable for all penalties per SR-008.
**Resolution:**
1. Minor discrepancy (honest mistake) → correct declaration, pay difference, continue
2. Significant undervaluation → customer pays correct customs amount + penalty
3. Prohibited items declared as other goods → EX-SHP-007 process applies
4. Repeat offender → flag for blacklist review
**Audit:** Original declaration vs actual. Penalty amounts. Customer liability acceptance logged.

---

### EX-SHP-009 — Traveler No-Show
**Trigger:** Assigned traveler (Air Express) does not appear at check-in or cancels.
**Who handles:** International Coordinator → Shipping Manager
**Status:** Bag → open (reassignment needed) | Shipments: remain at ready_for_dispatch
**Customer:** N/A initially (internal). If delay beyond expected date: standard delay notification.
**System:** Exception: traveler_no_show. Cancel carrier_assignment. Alert coordination team for reassignment.
**Resolution:**
1. New traveler found → reassign bag → continue
2. Next scheduled traveler → update estimated_arrival_date, notify customers of delay
3. Cannot reassign → escalate to air_cargo option (price difference billed if applicable)
**Escalation:** 24h no reassignment → Shipping Manager escalates to management.
**Audit:** Original traveler, no-show reason if known, reassignment details, customer notifications.

---

### EX-SHP-010 — Bag Discrepancy on Arrival
**Trigger:** Number or weight of packages in bag does not match the sealed manifest on arrival.
**Who handles:** Warehouse Officer (destination) → Shipping Manager
**Status:** Bag → being_unpacked | Exception: bag_discrepancy
**Customer:** Customers with potentially affected packages notified individually.
**System:** Full count logged against manifest. Missing packages flagged as EX-SHP-001. Extra packages investigated.
**Resolution:**
1. Count error → recount confirms all packages present → close exception
2. Missing packages → lost package process per EX-SHP-001
3. Extra packages → identify correct customer and notify
**Audit:** Manifest vs actual count. Status of each package. Resolution per package.

---

## SECTION 3 — STORAGE & ABANDONMENT EXCEPTIONS

### EX-STR-001 — Storage Fee Period Reached
**Trigger:** Package not collected after free storage period ends (3 days standard, 7 days VIP).
**Who handles:** Warehouse Officer → Customer Service
**Status:** Shipment → storage_fee_applied
**Customer:** "Your shipment [tracking] has been in storage for [X] days. Storage fees now apply: [amount] per day. Please collect immediately."
**System:** Storage fee invoice auto-generated. Daily fee accumulates.
Notifications sent: day 1 of fee, day 7, day 14.
**Resolution:**
1. Customer collects and pays both invoices → closed
2. Customer requests delivery → delivery fee added, arranged
3. Customer pays outstanding and requests more time → accepted with note added
**Escalation:** Day 14 post-arrival → Warehouse Manager notified.

---

### EX-STR-002 — Abandoned Package
**Trigger:** Day 21 after arrival with no customer contact or payment on storage fees.
**Who handles:** Warehouse Manager → Owner (decision mandatory)
**Status:** Shipment → abandoned
**Customer:** Final warning at day 21: "Your package [tracking] will be declared abandoned in 7 days unless you contact us and settle all outstanding amounts."
**System:** Abandoned flag set. 7-day final countdown. If no response → management decision required.
**Resolution (Owner decision mandatory):**
1. Dispose → photo evidence required, cost logged, customer informed
2. Auction → if declared_value > 50,000 XAF, proceeds applied to outstanding balance
3. Hold further → Owner approval required, reason documented, storage cost continues
**Escalation:** Cannot close without Owner approval.
**Audit:** Full timeline. Decision maker. Outcome. Any auction proceeds.

---

## SECTION 4 — INSURANCE EXCEPTIONS

### EX-INS-001 — Insurance Claim Filed
**Trigger:** Customer files insurance claim for lost or damaged shipment with active insurance.
**Who handles:** Finance Manager → CFO (if above threshold)
**Status:** InsuranceStatus → claim_pending
**Customer:** "Your insurance claim for shipment [tracking] has been received. Reference: [claim_id]. Review will be completed within 5 business days."
**System:** Exception created. Linked to original EX-SHP-001 or EX-SHP-002 record.
**Resolution:**
1. Claim approved → compensation up to insured_value → credit note or bank transfer
2. Partially approved → partial compensation with written explanation
3. Rejected → customer informed with specific reason (false declaration, prohibited items not covered)
**Escalation:** Claims > 500,000 XAF → CFO | > 2,000,000 XAF → Owner
**Audit:** Claimed amount, approved amount, approver, payment method and reference.

---

## SECTION 5 — INFRASTRUCTURE SERVICES EXCEPTIONS

### EX-SVC-001 — Service Delay
**Trigger:** Scheduled job cannot be completed on the planned date.
**Who handles:** Technician → Maintenance Coordinator
**Status:** ServiceTicketStatus → scheduled (with reschedule flag)
**Customer:** "Your service appointment on [date] has been delayed. New date: [date]. We apologise for the inconvenience."
**System:** Reschedule ticket. Update technician_assignment. Log reason.
**Resolution:**
1. Reschedule → new date confirmed → customer notified
2. Repeated delays → escalate to Infrastructure Services Manager
3. Customer requests cancellation → apply cancellation policy per contract
**Audit:** Original date, delay reason, new date, who rescheduled.

---

### EX-SVC-002 — Parts Unavailable
**Trigger:** Required parts/equipment not in stock for a scheduled job.
**Who handles:** Field Technician → Maintenance Coordinator → Procurement
**Status:** ServiceTicketStatus → waiting_parts
**Customer:** "Parts required for your service are on order. Expected: [date]. We will reschedule promptly on arrival."
**System:** Create procurement request linked to ticket. Hold ticket status.
**Resolution:**
1. Parts arrive → reschedule and complete service
2. Alternative parts available → propose to customer → approve → proceed
3. Long delay → offer partial service or partial refund of deposit
**Audit:** Parts required, procurement date, arrival date, cost impact.

---

### EX-SVC-003 — Site Access Denied
**Trigger:** Technician arrives on site but cannot gain access (customer absent, security restriction).
**Who handles:** Technician → Maintenance Coordinator
**Status:** ServiceTicketStatus → waiting_customer
**Customer:** "Our technician arrived at [time] but was unable to access the site. Please reschedule."
**System:** Log attempt with timestamp and GPS. Call-out fee may apply per contract.
**Resolution:**
1. Reschedule → customer confirms access → proceed
2. Second failed access → call-out fee applied
3. Third failed access → customer billed for all wasted visits, ticket cancelled on request
**Audit:** Arrival time, access denial reason, attempts count, fees applied.

---

### EX-SVC-004 — Equipment Failure Within Warranty
**Trigger:** Installed equipment fails within its warranty period.
**Who handles:** Customer reports → Helpdesk → assigned engineer
**Status:** ServiceTicketStatus → in_progress | WarrantyStatus → claimed
**Customer:** "Your warranty claim has been opened. Reference: [id]. Technician scheduled within 48 hours."
**System:** Verify warranty_records. Confirm within period. Create priority warranty claim ticket.
**Resolution:**
1. Covered by warranty → repair or replace at no cost to customer → document fully
2. Failure due to customer misuse → not covered → quote new repair job
3. Manufacturer defect → file claim with supplier → temporary replacement if available
**Escalation:** Unresolved 48h → Infrastructure Services Manager.
**Audit:** Failure description, warranty confirmed, resolution method, parts replaced.

---

### EX-SVC-005 — Solar System Fault Post-Installation
**Trigger:** Installed solar system malfunction reported by customer.
**Who handles:** Helpdesk → Solar Engineer (emergency priority)
**Status:** ServiceTicketStatus → in_progress (emergency)
**Customer:** "Solar system fault reported. Emergency technician dispatched. Reference: [id]."
**System:** Emergency ticket created. Solar Engineer assigned. Infrastructure Services Manager notified.
Check warranty (ESR-004) and maintenance contract (ISR-009).
**Resolution:**
1. Within warranty → repair/replace at no cost → update maintenance schedule
2. Under AMC → covered → no extra charge → log in maintenance history
3. Outside warranty, no contract → emergency billing (ISR-008)
4. Critical client (hospital, data centre) → Owner notified immediately
**Audit:** Fault type, affected components, downtime hours, resolution, parts replaced, cost.

---

### EX-SVC-006 — Customer Disputes Service Invoice
**Trigger:** Customer disputes charge after service completion.
**Who handles:** Finance Manager
**Status:** Invoice → disputed
**Customer:** "Your dispute has been received. Reference: [id]. Review within 48 hours."
**System:** Freeze payment reminders. Attach service report to review file.
**Resolution:**
1. Invoice correct → show service report, customer signature, technician notes → confirm
2. Billing error found → issue credit note or corrected invoice
3. Customer refuses to pay after confirmation → Finance Manager → legal action if needed
**Audit:** Original invoice, dispute reason, resolution decision.

---

### EX-SVC-007 — Technician Unavailable
**Trigger:** Assigned technician cannot attend (illness, emergency, resignation).
**Who handles:** Maintenance Coordinator → Infrastructure Services Manager
**Status:** ServiceTicketStatus → scheduled (reassignment in progress)
**Customer:** "We are reassigning a technician to your appointment. New confirmation within 24 hours."
**System:** Cancel assignment. Alert coordinator. Reassign to available technician.
**Resolution:**
1. Reassign same day → notify customer of new technician → proceed
2. Cannot reassign same day → reschedule → compensate VIP customers if applicable
**Audit:** Original assignment, reason for unavailability, new assignment, delay duration.

---

## SECTION 6 — CUSTOMER EXCEPTIONS

### EX-CUS-001 — VIP Override Request
**Trigger:** VIP customer requests an exception to standard policy (release without full payment, priority without extra fee, etc.)
**Who handles:** VIP Client Manager → relevant Department Manager
**Resolution:**
1. Override approved (with relevant permission flag) → logged in ApprovalWorkflow
2. Override rejected → customer informed professionally with alternative offered
3. Partial accommodation negotiated → document terms
**Rule:** VIP status never grants automatic override rights. Every override reviewed weekly.
**Audit:** Request, approver, reason, outcome — all logged.

---

### EX-CUS-002 — Blacklisted Customer Requests Service
**Trigger:** Person or company on blacklist attempts any transaction.
**Who handles:** Customer Service → Compliance Manager
**Customer:** "We are unable to process your request. Please contact our support team." (Do NOT disclose the reason automatically.)
**System:** No transaction created. Attempt logged.
**Resolution:**
1. Blacklist confirmed valid → request rejected, logged
2. Blacklist was an error → Compliance Manager approves removal (can_approve_high_risk_client flag) → customer reactivated
3. Partial reactivation → specific transaction types only, documented
**Audit:** All approach attempts logged regardless of outcome.

---

## SECTION 7 — STOCK & RETAIL EXCEPTIONS

### EX-STK-001 — Stock Count Discrepancy
**Trigger:** Physical count does not match system count during stock audit.
**Who handles:** Inventory Officer → Store Manager (if above threshold)
**Resolution:**
1. Recount and discrepancy confirmed:
   a. < 5 units or < 50,000 XAF → Inventory Officer adjusts with reason
   b. > 5 units or > 50,000 XAF → Store Manager approval required
   c. Suspected theft/fraud → IT Security + Management investigation required
**Audit:** Before and after count. Who adjusted. Reason. Investigation record if fraud suspected.

---

### EX-STK-002 — Reservation Expired
**Trigger:** Automated job: unpaid reservation reached 24-hour limit.
**Who handles:** System automated → Customer Service notification
**Status:** Reservation → expired | Stock released | Order → reservation_expired
**Customer:** "Your reservation for [product] has expired as payment was not received within 24 hours. Stock has been released. Contact us to rebook."
**System:** Stock released automatically. Customer notified immediately.
**Resolution:**
1. Customer wants to rebook → new reservation created (if stock available)
2. Customer no longer interested → no action
**Audit:** Reservation created, expired, stock released — all timestamped.

---

### EX-STK-003 — Supplier Sent Wrong or Damaged Goods
**Trigger:** Goods received from supplier do not match purchase order or are damaged on arrival.
**Who handles:** Warehouse Officer → Procurement Officer
**Status:** Purchase order → exception | Stock NOT recorded until resolved
**Resolution:**
1. Return to supplier → debit note created, supplier arranges pickup
2. Partial acceptance → accept correct items, return the rest
3. Compensation from supplier → supplier credit note applied to TEHTEK account
**Audit:** Photo evidence required. Discrepancy logged. All supplier communication logged.

---

## SECTION 8 — COMMISSION EXCEPTIONS

### EX-COM-001 — Commission Dispute
**Trigger:** Commission partner disputes the calculated commission amount.
**Who handles:** Finance Manager → Sales Manager → Owner if escalated
**Status:** CommissionStatus → disputed | CommissionDisputeStatus → open
**Partner:** "Your commission dispute for [reference] has been received. Reference: [dispute_id]. Review within 5 business days."
**System:** Exception: commission_dispute. Freeze payout. Assign to Finance Manager.
**Resolution:**
1. Dispute valid → recalculate, approve corrected amount → process payout
2. Dispute invalid → explain to partner with documentation → resume original amount
3. Cannot agree → escalate to Owner for final decision
**Audit:** Original amount, disputed amount, decision, who decided.

---

### EX-COM-002 — Commission Fraud Flag
**Trigger:** System or staff flags potential commission fraud (fake lead, duplicate, self-referral).
**Who handles:** Finance Manager + Owner (both notified immediately)
**Status:** CommissionStatus → on_hold | commission_fraud_flag = true
**System:** Payout frozen. Exception: commission_fraud_flag. Finance Manager AND Owner notified.
**Resolution:**
1. Investigation proves fraud → commission cancelled, partner flagged, may be blacklisted
2. Investigation clears partner → remove flag, process payout
**Audit:** Fraud flag reason, investigation notes, outcome, who authorized resolution.

---

## SECTION 9 — STAFF & SYSTEM EXCEPTIONS

### EX-SYS-001 — Staff Error
**Trigger:** Staff member made an error (wrong status, amount, customer linked, etc.)
**Who handles:** Department Manager
**Resolution:**
1. Error documented
2. Manager approves correction with mandatory reason
3. Correction applied
4. Original record PRESERVED in audit log — never deleted or overwritten
5. Financial impact > 100,000 XAF → Finance Manager also approves
**Policy:** Errors are treated as learning events unless repeated or fraudulent. No punishment for honest mistakes reported promptly.
**Audit:** Error description, who made it, who corrected it, before/after values.

---

### EX-SYS-002 — Force Majeure
**Trigger:** Uncontrollable external event (flood, strike, war, pandemic, government action, power failure).
**Who handles:** Owner / relevant Department Manager
**Status:** Affected shipments/jobs flagged with force_majeure = true | All timelines paused
**Customer:** Official communication sent explaining situation. No penalties or late fees applied for force majeure delays.
**Audit:** Force majeure event logged with start date, end date, affected records count.

---

## SECTION 10 — AUTHENTICATION & SECURITY EXCEPTIONS ★ NEW

### EX-AUTH-001 — Refresh Token Replay Attack Detected
**Trigger:** A refresh token that has already been used (is_used = true) is presented again to
the /auth/refresh endpoint. This indicates a stolen token or session hijacking attempt.
**Who handles:** System (automated) → CTO / Owner notified immediately
**Status:** All active sessions for the affected user are immediately invalidated.
**User notification:** "Your session has been terminated for security reasons. Please log in again.
If you did not initiate this, contact support immediately."
**System:**
- All refresh tokens for the user marked as revoked
- All active sessions terminated
- AuditAction: token_replay_detected logged with ip_address, user_agent, timestamp
- ExceptionType: auth_replay_attack created
- CTO and Owner notified via WhatsApp + email
**Resolution:**
1. User logs in again → issue new tokens → monitor for repeat
2. Investigate IP address and user_agent of the replay attempt
3. If account appears compromised → force password reset, notify user
4. If staff account → Shipping Manager notified, access reviewed
**Escalation:** Immediately to CTO | Staff account involved → Owner
**Audit:** Token ID used, IP address of replay attempt, user_agent, timestamp, outcome.

---

### EX-AUTH-002 — Account Lockout from Failed Login Attempts
**Trigger:** User reaches 5 consecutive failed login attempts (UR-002). Account locked for 15 minutes.
**Who handles:** System (automated) | Admin can manually unlock
**Status:** UserStatus: locked_until set to now + 15 minutes
**User notification:** "Your account has been temporarily locked due to multiple failed login attempts.
Try again in 15 minutes or contact support."
**System:**
- failed_login_count = 5, locked_until = now + 15 minutes
- AuditAction: account_locked logged with ip_address and user_agent of all attempts
- ExceptionType: unauthorized_access logged if this is a staff account
- If same IP triggers lockout on multiple accounts within 1 hour → escalate to CTO (potential brute force)
**Resolution:**
1. 15 minutes pass → account automatically unlocks, failed_login_count reset
2. Admin manually unlocks before timeout → AuditAction: account_unlocked
3. Repeated lockout events from same IP → block IP at Caddy level, CTO reviews
4. Suspected targeted attack → Owner notified, affected user warned
**Escalation:** Multiple accounts locked from same IP → CTO immediately
**Audit:** All failed attempts with ip_address, user_agent, timestamp. Unlock action and who performed it.

---

## EXCEPTION REVIEW SCHEDULE

| Frequency | Review |
|---|---|
| Daily | All open exceptions reviewed by relevant manager |
| Weekly | All exceptions closed in the week reviewed by Owner |
| Monthly | Exception patterns analysed — which types recur most |
| Quarterly | Policy and document updated based on patterns |
