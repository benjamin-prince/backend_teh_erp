# TEHTEK — Prohibited & Restricted Items Policy
# Version: 1.0 | April 2026
# Applies to: All routes — China / USA / Europe ↔ Cameroon + Local deliveries
# Owner: Benjamin Boule Fogang
# Review: Quarterly or whenever carrier/customs regulations change

---

## POLICY STATEMENT

TEHTEK accepts no liability for packages containing prohibited or restricted items.

By signing or digitally accepting the shipping declaration (SR-008), the customer:
1. Confirms all declared information is accurate and complete
2. Accepts FULL responsibility for false declarations
3. Accepts liability for all customs penalties, seizures, and legal consequences
4. Acknowledges that TEHTEK will cooperate fully with authorities if required

Customer liability acceptance is logged with timestamp and IP address on every shipment confirmation.

---

## CATEGORY 1 — ABSOLUTELY PROHIBITED (All Routes, No Exceptions)

### Weapons & Dangerous Materials
- Firearms, ammunition, explosives of any kind
- Military equipment and accessories
- Chemical, biological, radiological, nuclear materials
- Tear gas, pepper spray, stun guns, tasers
- Replica or toy weapons that resemble real weapons
- Knives and bladed weapons (unless declared and route permits)

### Narcotics & Controlled Substances
- Illegal drugs of any kind
- Precursor chemicals for drug manufacturing
- Drug paraphernalia of any kind

### Human & Animal
- Human remains (except with full legal documentation — contact management before acceptance)
- Live animals (except with full legal documentation, CITES permits, and airline approval)
- Endangered species or parts thereof (ivory, animal skins, horns, etc.)
- Wildlife products prohibited under CITES convention

### Financial
- Counterfeit currency, stamps, or documents
- Counterfeit products of any branded goods
- Stolen goods of any kind

### Other Absolute Prohibitions
- Pornographic or obscene material
- Hate material, terrorist propaganda, extremist content
- Items that violate intellectual property rights (fake branded goods)

---

## CATEGORY 2 — RESTRICTED ITEMS (Require Pre-Approval Before Acceptance)

These items CAN be shipped but require documentation review and Shipping Manager
pre-approval before any package is accepted.

### Electronics & Batteries
- **Lithium batteries (standalone, not installed in device):**
  Maximum 2 batteries per shipment. Capacity limits apply per airline/route.
  Must comply with IATA Dangerous Goods Regulations (DGR).
- **Power banks:** Declared capacity required. Must meet airline lithium battery standards.
- **High-value electronics (> 500,000 XAF):** Declared value + insurance required.
- **Drone / UAV equipment:** May require import/export permits at destination.
- **Radioactive materials (medical/industrial):** Special permits required from both origin and destination authorities.

### Medical & Pharmaceutical
- **Prescription medications:** Valid prescription required. Quantity must not exceed personal use limits for the route.
- **Medical devices:** May require regulatory clearance at destination country.
- **Dietary supplements and vitamins:** Large quantities suggesting commercial import require import permits.
- **CBD / hemp products:** Prohibited on most routes. Check current status per specific route before accepting.

### Food & Agricultural Products
- **Fresh food / perishables:** NOT accepted on Air Express (traveler route) — airline restrictions.
- **Processed food:** Accepted with quantity limits. Commercial quantities require customs permits.
- **Seeds and plants:** Phytosanitary certificate required.
- **Animal products (meat, dairy, eggs):** Import restrictions vary heavily by destination. Check per route.
- **Honey and bee products:** Agricultural import restrictions at most destinations.

### Liquids
- **Air Express (traveler route — checked baggage):**
  - Liquids in carry-on: max 100ml per container, must fit in 1-litre transparent bag
  - Liquids in checked baggage: sealed, leak-proof packaging, manifest declared
- **Air Cargo and Sea Freight:** Liquids in sealed, leak-proof, correctly labelled packaging with full manifest declaration
- **Alcohol:** Subject to import restrictions and duties at destination. Declare quantity and value. Prohibited in certain countries.
- **Perfumes / cologne:** Flammable — restricted quantities on air routes.

### Financial & Documents
- **Cash above 1,000,000 XAF (or equivalent):** Must be declared. May require documentation. Contact manager before accepting.
- **Jewellery and precious metals above 500,000 XAF:** Insurance required + customs declaration.
- **Negotiable instruments (cheques, bonds):** Require legal documentation.

### Other Restricted Items
- **Tobacco products:** Subject to import taxes and strict quantity limits per route.
- **Compressed gas canisters (aerosols, fire extinguishers):** Restricted on all air routes.
- **Fireworks and pyrotechnics:** Prohibited on air routes. Restricted on sea/land — requires permits.

---

## CATEGORY 3 — ROUTE-SPECIFIC RESTRICTIONS

### China → Cameroon
- **Electronics:** High customs scrutiny. Declared value must match supplier invoice.
- **Branded goods:** Any branded electronics, clothing, or accessories may be inspected for counterfeits. All must be genuine.
- **Batteries:** Must comply with IATA DGR. Lithium battery documentation required.
- **Food products:** Processed food accepted with quantity limits. Fresh food not accepted.

### USA → Cameroon
- **Food:** USDA export requirements must be met at origin.
- **Medications:** FDA regulations at origin apply in addition to destination rules.
- **Electronics:** US export control regulations (EAR) may restrict certain technology items.
- **High-value items:** Customs duty applies based on declared CIF value at destination.

### Europe → Cameroon
- **Agricultural products:** Strict phytosanitary requirements apply.
- **Chemicals:** REACH regulations at origin may restrict certain chemical products.
- **Electronics with data:** Devices containing personal data may be subject to GDPR considerations on export.

### Cameroon → International (Exports)
- **Wildlife and natural resources:** Strict CITES compliance required for any animal or plant materials.
- **Cultural artifacts and antiques:** Export permit required from Cameroonian Ministry of Culture.
- **Cash / currency export:** Declaration required above legal threshold (check current limits).
- **Cocoa, coffee, timber:** Export permits and phytosanitary certificates required.

---

## WAREHOUSE INTAKE CHECKLIST (Mandatory for Every Package)

Warehouse Officer must complete this checklist before accepting any package.
Reference: Business Rule SR-009 — check must be logged in system before status → warehoused.

```
□ Package weight and dimensions match the declaration
□ Package contents appear consistent with declaration (when inspectable)
□ No suspicious weight discrepancy (e.g. declared as clothes but very heavy for size)
□ No prohibited items visible, declared, or suspected
□ Battery-powered devices: battery type and count declared
□ Liquids: properly sealed and declared
□ High-value items: declared value matches accompanying supplier invoice
□ Branded goods: appear to be genuine products
□ Customer declaration (SR-008) has been accepted in system: declaration_accepted = true
□ prohibited_check_done = true set in system
```

**If ANY item is suspicious, uncertain, or outside guidelines:**
**DO NOT ACCEPT the package. Escalate immediately to Shipping Manager.**
Staff are NEVER to accept a borderline package without manager approval.
There is no penalty for rejecting uncertain packages. There is liability for accepting prohibited ones.

---

## WHAT HAPPENS WHEN PROHIBITED ITEMS ARE FOUND

### At warehouse intake
→ Process: EX-SHP-007 (Prohibited Item Found at Intake)
→ Package rejected. Customer contacted to collect the prohibited item.
→ Shipment status → cancelled.

### During transit (discovered by carrier or at hub)
→ Carrier reports to TEHTEK. TEHTEK notifies customer immediately.
→ Carrier may hand package over to authorities without TEHTEK involvement.
→ TEHTEK cooperates fully with all authorities.
→ Customer bears ALL costs, penalties, and legal consequences.
→ Customer accepted this liability in the shipping declaration (SR-008).

### At customs at destination
→ Process: EX-SHP-005 (Customs Seizure) or EX-SHP-008 (False Declaration)
→ Customer liable for all penalties per signed declaration (SR-008).
→ TEHTEK not liable for customer's false declaration or prohibited item.

---

## STAFF RESPONSIBILITIES

### Warehouse Officers
First line of detection. Every package must be checked before warehousing. No exceptions.

### Customs Officers
Manage all seizure documentation and communicate with customs authorities.
Keep records of all customs interactions.

### Shipping Manager
Final authority on borderline cases. Any uncertain item escalates to Shipping Manager before acceptance.
Responsible for keeping this document current.

### All Staff
No staff member may accept a prohibited item regardless of:
- Customer pressure or urgency
- Claims that "it will pass customs"
- Instructions from another staff member without manager approval
- Promises of additional payment

**If in doubt: REJECT and ESCALATE. Never assume.**

---

## DOCUMENT MAINTENANCE

This document must be reviewed:
- Every quarter as a minimum
- Whenever a carrier changes its dangerous goods policy
- Whenever Cameroon customs regulations are updated
- Whenever a new route is added to TEHTEK services
- Whenever a seizure incident reveals a gap in this policy

Responsible: Shipping Manager + Legal/Compliance Officer
Approved by: Benjamin Boule Fogang (Owner)
