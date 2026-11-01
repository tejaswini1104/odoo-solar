# SunPower Solutions — Solar Installation Management System (Phase 1)

A modular monolith web platform designed to streamline rooftop solar operations from initial lead inquiry through site survey hard gates, turnkey BOM generation, order confirmation, serialized dispatch, installation completion, automatic warranty activation, and after-sales service tickets.

---

## Technology Stack

- **Backend**: Python 3.11+, FastAPI, SQLAlchemy 2.0, Pydantic v2
- **Database**: PostgreSQL 18 (with relational FKs and DB-level unique constraints on serial numbers)
- **Frontend**: React 18, Vite, Tailwind CSS, Lucide Icons
- **Storage**: Local disk storage under `backend/media/` (no cloud dependencies)
- **Authentication**: Cookie sessions with five staff roles plus customers (see "Roles and sign-in")

---

## Phase 1 Scope & Features Implemented

1. **Customer & Lead Management**:
   - Capture customer enquiries with technical specifics (required kW, electricity bill, roof area, grid type, subsidy flag).
   - Convert qualifying leads directly into customer accounts with a single action.

2. **Site Survey & Hard Gate Approval**:
   - Comprehensive roof inspection parameters: area, orientation, tilt angle, shading level, cable run, and grid suitability.
   - **Enforced Hard Gate**: Quotation creation is strictly blocked in the backend service layer unless the linked site survey is in `Approved` status (returns HTTP 400 if violated).

3. **Solar Packages & Automatic BOM**:
   - Seeded 1kW to 5kW On-Grid and Off-Grid turnkey packages mapped to realistic components via `PackageComponent`.
   - Selecting a package automatically generates the complete Bill of Materials (BOM) with quantities and prices. Zero manual part entry.

4. **Quotations & Sales Orders**:
   - Turnkey quotation generation with automatic 18% GST calculation.
   - Acceptance and conversion to Sales Orders with payment tracking.

5. **Order Confirmation Automation (Atomic DB Transaction)**:
   - Confirms order only when: (1) linked survey is Approved, and (2) at least an advance payment is recorded.
   - Automatically executes in a single database transaction:
     - Transitions order to `Confirmed`.
     - Automatically reserves required component inventory quantities.
     - Automatically creates an `Installation` job record.
     - Automatically assigns a technician from the active crew.

6. **Inventory & Serial Number Tracking**:
   - Track bulk stock quantities (on hand, reserved, available).
   - Serialized tracking with **database-level unique constraint** on `EquipmentSerial.serial_number` for Inverters, Batteries, and Charge Controllers.
   - **Dispatch Hard Gate**: Validates that all required serialized units have unique, in-stock serial numbers assigned before dispatch. Deducts reserved and on-hand stock atomically.

7. **Installation Completion & Automatic Warranty Engine**:
   - Captures confirmed system size (kW) and verifies linked serial numbers on the "Mark Completed" action.
   - **Automatic Warranty Engine**: Automatically creates warranty records upon completion:
     - Inverters: 24 months (2 years)
     - Batteries: 24 months (2 years)
     - Charge Controllers: 24 months (2 years)
     - Solar Panels: 240 months (20 years) — *Assumption: Solar panels are bulk-tracked in this phase, so one bulk warranty record is created per installation for solar panels.*
     - Start date = completion date; end date is calculated automatically. Zero manual date entry.

8. **Service Tickets & Coverage Decision**:
   - On ticket creation with an equipment serial number, the backend automatically performs a warranty lookup:
     - **Active Warranty**: Sets `service_type = COVERED` and `customer_charge = ₹0`.
     - **Expired Warranty**: Sets `service_type = BILLABLE` and automatically spawns a draft `Invoice` with editable placeholder parts and labour lines.
   - **Ticket Closure Hard Gate**: A ticket cannot transition to `Closed` status without the `customer_confirmed` flag being set first.

9. **Billing & Invoices**:
   - Structured invoice records linked to orders or service tickets with editable line items.

10. **Order-Level Profitability View**:
    - Dedicated view calculating Realized Revenue, Material Cost (sum of dispatched BOM item costs), Flat Labour Cost, Net Profit, and Profit Margin % per completed installation.

---

## Quickstart & Setup Commands

### 1. Prerequisites
- **Python**: 3.11+
- **Node.js**: v18+ (tested on v24.14.0)
- **PostgreSQL**: Running on `localhost:5432` with a database named `solar_erp`

If the database is not created yet, create it using `psql`:
```bash
psql -U postgres -c "CREATE DATABASE solar_erp;"
```

---

### 2. Backend Setup & Run

#### Install Dependencies:
```bash
python -m pip install -r backend/requirements.txt
```

#### Run Database Migrations & Seed Data:
```bash
python backend/seed.py
```
*This drops and recreates the public schema, sets up all relational tables, constraints, packages, technicians, inventory, and seeds the required walkthrough scenario.*

#### Run Phase 1 Rule Verification Test Suite:
```bash
python backend/verify_rules.py
```

#### Start FastAPI Server:
```bash
python -m uvicorn backend.app.main:app --host 127.0.0.1 --port 8000
```
API Documentation will be available at: `http://127.0.0.1:8000/docs`

---

### 3. Frontend Setup & Run

In a separate terminal:
```bash
cd frontend
npm install
npm run dev -- --host 127.0.0.1 --port 5173
```
Open your browser at: `http://127.0.0.1:5173/`

---

## Seed Data Walkthrough & Verification Scenarios

The seed dataset demonstrates the entire Phase 1 lifecycle:

1. **Active Warranty & Free Service Flow**:
   - **Customer**: Ravi Kumar (Hyderabad), monthly bill ₹6,000, roof 700 sq.ft, 5kW On-Grid system.
   - **Survey**: South-facing, 20° tilt, low shading, status `Approved`.
   - **Installed Hardware**: 5kW Inverter `INV-2026-0042` with Active warranty (expires in 2 years).
   - **Service Ticket**: *"Inverter stopped working"* on `INV-2026-0042` → **Resolved to WARRANTY ACTIVE → COVERED → ₹0**.

2. **Expired Warranty & Billable Service Flow**:
   - **Customer**: Anand Sharma (Bengaluru).
   - **Installed Hardware**: 5kW Inverter `INV-2023-0018` commissioned in January 2023 → **Warranty Expired in January 2025**.
   - **Service Ticket**: *"Inverter error code E04 / No AC output"* on `INV-2023-0018` → **Resolved to BILLABLE → Draft Invoice #INV-SRV-0002 auto-created for ₹7,080** with editable parts & labour line items.

3. **Profitability View**:
   - Displays gross revenue (₹2,58,302), material cost (₹1,57,800), labour cost (₹6,500), and net profit (₹94,002 / 36.4% margin) for completed orders.

---

## What has been built since Phase 1

- **First call before a survey**: a lead must be marked *Contacted* with the shadow-free roof area and a grid-suitability answer before a survey can be booked. A grid found unsuitable on the call blocks the booking.
- **Surveys** are booked by Sales and given automatically to the technician with the least open work.
- **Installation proof**: start and finish times, confirmed system size, photos of the finished roof and the homeowner's on-screen signature. A job cannot be completed without them.
- **Warranty clock starts at delivery** (`POST /api/dispatch/{id}/delivered`) for every serial number (2 years) and the panels (20 years). Completing the installation only fills in anything still missing.
- **Barcode and serial scanning at dispatch**: a handheld scanner or typed serials (Enter), or the phone camera where the browser supports `BarcodeDetector`. Nothing is pre-filled. Each scan is checked against in-stock units for the order, and dispatch stays disabled until every unit is scanned.
- **Warehouse pick list** for every physical part (panels, cables, stands and serial-numbered units). Installation is a service and is never packed or counted as stock.
- **Repair invoices are priced automatically**: the faulty part's list price plus `SERVICE_LABOUR_CHARGE` (config), plus GST. Support can still edit the lines. A ticket needs a delivered serial number that belongs to the customer.
- **Find the customer in seconds**: ticket creation searches by phone, name, address or serial number and lists the customer's equipment with warranty status.
- **Alerts** (the bell in the top bar, staff and portal): new enquiries and reported payments to Sales, orders to pack to the warehouse, new jobs and survey visits to the technician, new tickets to Support, and progress updates to the customer.
- **Order cancellation** before dispatch releases reserved stock, removes the installation job, closes the subsidy file and tells Sales how much to refund.
- **Profit uses real costs**: material is priced at the average paid in recorded stock purchases (list cost price for anything never purchased). Each job also shows what the customer has paid and the balance due.
- **Printable invoices and quotations** (staff and portal): *PDF* opens a clean page; choose "Save as PDF" in the print dialog.
- **Director's view**: today, this week, this month or a custom range, unfinished work with what each item is waiting for, profit per job, technician pay, stock spend, subsidy files and CSV exports.
- Duplicate customers (same phone or email) are refused, and converting a lead reuses an existing customer.

### Not built
- **Anonymous enquiry form.** The portal form needs an account (a deliberate choice for now).
- **Email, SMS or WhatsApp delivery.** Alerts are in the app only.
- **Online payment gateway** (customers pay by bank transfer and report the reference), **refund recording**, and an **audit log**.
- Photos and signatures are stored on local disk under `backend/media/`, not in cloud storage.
- Per-unit purchase cost: serial-numbered units are costed at the average purchase price of the product, not the exact purchase they came from.

---

## Roles and sign-in

Everyone signs in on the same page, `/login`. The role decides where they land and what they can reach.
Customers go to the portal (`/portal`). Staff go to the staff application (`/`). The API enforces the same rules,
so a role that is not allowed to do something is refused even if it calls the API directly.

| Role | Works with |
|---|---|
| **Administrator** | Sees everything (dashboard, profitability) and manages staff accounts. Does not send invoices, verify payments or change orders. |
| **Sales** | Leads, customers, surveys, quotations (create, send), orders, recording and verifying order payments, installation invoices, and assigning a technician to a job. |
| **Technician** | Their own surveys and their own installation jobs, which they mark complete. |
| **Customer Support** | Tickets, warranties, repair invoices, and verifying repair payments. |
| **Warehouse** | Dispatch: assigning serial numbers and sending an order out. |
| **Customer** | The portal: packages, enquiries, quotations, payments, invoices, warranties and support tickets, for their own account only. |

Who may approve a site survey is still undecided. For now, anyone who can edit surveys (Sales and Technician) can approve.

### Demo logins (created by `python backend/seed.py`)

Password for all of them is `SunPower@123`. Change it from **Change password** in the top bar before any real use.

| Role | Email |
|---|---|
| Administrator | admin@sunpower.test |
| Sales | sales@sunpower.test |
| Technician | technician@sunpower.test |
| Customer Support | support@sunpower.test |
| Warehouse | warehouse@sunpower.test |

Customers register themselves at `/register`.

### Creating real staff accounts

An administrator adds staff under **Staff Accounts** in the app. To create the first administrator on a database
without the demo data, run:

```bash
python backend/create_staff.py --name "Asha Rao" --email asha@yourcompany.com --role admin
```

### Database changes for an existing database

A fresh `python backend/seed.py` creates everything (and wipes the `public` schema first). An existing database
keeps its data: run `python backend/apply_migrations.py`, which creates new tables and applies the SQL files in
`backend/migrations/` (`001` to `007`). It is safe to run more than once.

### Automated tests

```bash
python -m pip install -r backend/requirements-dev.txt
python -m pytest backend/tests
```

The tests run against a temporary SQLite file, never your PostgreSQL database. They walk the whole journey
(first call, survey, quotation, advance, dispatch, delivery, warranty, installation proof, repairs, profit) and check
the hard gates and who may do what. `python backend/verify_rules.py` is the older check against the seeded database.

### Bank details

Customers see the company bank details when paying. Replace the placeholders in `BANK_DETAILS` in
`backend/app/core/config.py` before showing the portal to anyone.
