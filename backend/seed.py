import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from datetime import datetime, date, timedelta
from backend.app.core.database import SessionLocal, Base, engine
from backend.app.models.models import (
    Customer,
    Lead,
    Technician,
    SiteSurvey,
    Product,
    SolarPackage,
    PackageComponent,
    InventoryItem,
    EquipmentSerial,
    Quotation,
    QuotationItem,
    SalesOrder,
    Payment,
    Installation,
    Warranty,
    ServiceTicket,
    Invoice,
    InvoiceItem,
    User,
    SubsidyApplication,
    SubsidyEvent
)
from backend.app.core.security import hash_password

# Demo staff logins, one per role. Change these passwords (Account > change-password) before any real use.
DEMO_PASSWORD = "SunPower@123"
DEMO_STAFF = [
    ("admin@sunpower.test", "Dhruv Admin", "admin"),
    ("sales@sunpower.test", "Sneha Sales", "sales"),
    ("technician@sunpower.test", None, "technician"),  # takes the name of the first technician record
    ("support@sunpower.test", "Sunita Support", "support"),
    ("warehouse@sunpower.test", "Wasim Warehouse", "warehouse"),
]

def seed_database():
    print("Dropping and recreating database schema...")
    from sqlalchemy import text
    with engine.connect() as conn:
        conn.execute(text("DROP SCHEMA public CASCADE; CREATE SCHEMA public;"))
        conn.commit()
    Base.metadata.create_all(bind=engine)

    db = SessionLocal()
    try:
        print("Seeding Technicians...")
        technicians_names = [
            ("Suresh Varma", "+91 98765 43210"),
            ("Rajesh Goud", "+91 98765 43211"),
            ("Ramesh Kumar", "+91 98765 43212"),
            ("Anita Patel", "+91 98765 43213"),
            ("Vikram Rao", "+91 98765 43214"),
            ("Pooja Nair", "+91 98765 43215"),
            ("Karthik Reddi", "+91 98765 43216"),
            ("Manoj Sharma", "+91 98765 43217"),
            ("Sunil Yadav", "+91 98765 43218"),
            ("Deepak Joshi", "+91 98765 43219"),
            ("Venkatesh B", "+91 98765 43220"),
            ("Harish C", "+91 98765 43221"),
            ("Naresh P", "+91 98765 43222"),
            ("Arjun Mehra", "+91 98765 43223"),
            ("Sanjay K", "+91 98765 43224")
        ]
        tech_objs = []
        for name, phone in technicians_names:
            t = Technician(name=name, phone=phone)
            db.add(t)
            tech_objs.append(t)
        db.flush()

        print("Seeding demo staff logins...")
        for email, name, role in DEMO_STAFF:
            db.add(User(
                name=name or tech_objs[0].name,
                email=email,
                phone=None,
                password_hash=hash_password(DEMO_PASSWORD),
                role=role,
                technician_id=tech_objs[0].id if role == "technician" else None,
            ))
        db.flush()

        print("Seeding Products...")
        products_data = [
            # name, category, unit, cost_price, unit_price, is_serialized
            ("540W Mono PERC Solar Panels", "Solar Panels", "Nos", 8500.0, 11500.0, False),
            ("5kW Solar On-Grid Inverter", "Inverter", "Nos", 38000.0, 52000.0, True),
            ("3kW Solar On-Grid Inverter", "Inverter", "Nos", 26000.0, 36000.0, True),
            ("1kW Solar Inverter", "Inverter", "Nos", 14000.0, 19000.0, True),
            ("150Ah Solar Tubular Battery", "Battery", "Nos", 11000.0, 15500.0, True),
            ("48V MPPT Solar Charge Controller", "Charge Controller", "Nos", 7500.0, 10500.0, True),
            ("4 sq mm DC Solar Cable (Roll)", "Wiring/Cables", "Meters", 45.0, 65.0, False),
            ("AC/DC Distribution Box & Isolator Switches", "Wiring Boxes/Switches", "Set", 4200.0, 6200.0, False),
            ("Aluminium Rooftop Mounting Stands", "Mounting Stands", "Set", 6500.0, 9500.0, False),
            ("Copper Earthing Rod & Lightning Arrester Kit", "Earthing/Safety", "Set", 3500.0, 5000.0, False),
            ("Turnkey Rooftop Installation & Commissioning", "Installation Service", "Set", 4000.0, 7000.0, False),
        ]
        
        product_map = {}
        for name, cat, unit, cost, price, is_ser in products_data:
            p = Product(
                name=name,
                category=cat,
                unit=unit,
                cost_price=cost,
                unit_price=price,
                is_serialized=is_ser
            )
            db.add(p)
            db.flush()
            product_map[name] = p

            # Seed stock in inventory
            inv = InventoryItem(
                product_id=p.id,
                quantity_on_hand=100 if not is_ser else 40,
                reserved_quantity=0
            )
            db.add(inv)

        db.flush()

        print("Seeding Serialized Stock...")
        # Add serial numbers in stock for testing dispatch
        serials_to_create = [
            (product_map["5kW Solar On-Grid Inverter"].id, "INV-2026-0042", "In Stock"),
            (product_map["5kW Solar On-Grid Inverter"].id, "INV-2026-0043", "In Stock"),
            (product_map["5kW Solar On-Grid Inverter"].id, "INV-2026-0044", "In Stock"),
            (product_map["3kW Solar On-Grid Inverter"].id, "INV-2026-0031", "In Stock"),
            (product_map["3kW Solar On-Grid Inverter"].id, "INV-2026-0032", "In Stock"),
            (product_map["1kW Solar Inverter"].id, "INV-2026-0011", "In Stock"),
            (product_map["150Ah Solar Tubular Battery"].id, "BAT-2026-0101", "In Stock"),
            (product_map["150Ah Solar Tubular Battery"].id, "BAT-2026-0102", "In Stock"),
            (product_map["48V MPPT Solar Charge Controller"].id, "CC-2026-0501", "In Stock"),
            # Expired warranty inverter in past
            (product_map["5kW Solar On-Grid Inverter"].id, "INV-2023-0018", "Installed"),
        ]

        serial_obj_map = {}
        for pid, snum, st in serials_to_create:
            s = EquipmentSerial(
                product_id=pid,
                serial_number=snum,
                status=st
            )
            db.add(s)
            db.flush()
            serial_obj_map[snum] = s

        print("Seeding Solar Packages (1kW to 5kW On-Grid and Off-Grid)...")
        # Define 1kW to 5kW On-Grid and Off-Grid
        packages_definitions = [
            ("1kW On-Grid Solar System", 1.0, "On-Grid", 55000.0, [
                ("540W Mono PERC Solar Panels", 2),
                ("1kW Solar Inverter", 1),
                ("4 sq mm DC Solar Cable (Roll)", 25),
                ("AC/DC Distribution Box & Isolator Switches", 1),
                ("Aluminium Rooftop Mounting Stands", 1),
                ("Copper Earthing Rod & Lightning Arrester Kit", 1),
                ("Turnkey Rooftop Installation & Commissioning", 1),
            ]),
            ("2kW On-Grid Solar System", 2.0, "On-Grid", 105000.0, [
                ("540W Mono PERC Solar Panels", 4),
                ("1kW Solar Inverter", 1), # or 2kW
                ("4 sq mm DC Solar Cable (Roll)", 40),
                ("AC/DC Distribution Box & Isolator Switches", 1),
                ("Aluminium Rooftop Mounting Stands", 1),
                ("Copper Earthing Rod & Lightning Arrester Kit", 1),
                ("Turnkey Rooftop Installation & Commissioning", 1),
            ]),
            ("3kW On-Grid Solar System", 3.0, "On-Grid", 155000.0, [
                ("540W Mono PERC Solar Panels", 6),
                ("3kW Solar On-Grid Inverter", 1),
                ("4 sq mm DC Solar Cable (Roll)", 50),
                ("AC/DC Distribution Box & Isolator Switches", 1),
                ("Aluminium Rooftop Mounting Stands", 2),
                ("Copper Earthing Rod & Lightning Arrester Kit", 1),
                ("Turnkey Rooftop Installation & Commissioning", 1),
            ]),
            ("4kW On-Grid Solar System", 4.0, "On-Grid", 205000.0, [
                ("540W Mono PERC Solar Panels", 8),
                ("3kW Solar On-Grid Inverter", 1),
                ("4 sq mm DC Solar Cable (Roll)", 65),
                ("AC/DC Distribution Box & Isolator Switches", 1),
                ("Aluminium Rooftop Mounting Stands", 2),
                ("Copper Earthing Rod & Lightning Arrester Kit", 1),
                ("Turnkey Rooftop Installation & Commissioning", 1),
            ]),
            ("5kW On-Grid Solar System", 5.0, "On-Grid", 245000.0, [
                ("540W Mono PERC Solar Panels", 10),
                ("5kW Solar On-Grid Inverter", 1),
                ("4 sq mm DC Solar Cable (Roll)", 80),
                ("AC/DC Distribution Box & Isolator Switches", 1),
                ("Aluminium Rooftop Mounting Stands", 3),
                ("Copper Earthing Rod & Lightning Arrester Kit", 1),
                ("Turnkey Rooftop Installation & Commissioning", 1),
            ]),
            ("1kW Off-Grid Solar System", 1.0, "Off-Grid", 85000.0, [
                ("540W Mono PERC Solar Panels", 2),
                ("1kW Solar Inverter", 1),
                ("150Ah Solar Tubular Battery", 1),
                ("48V MPPT Solar Charge Controller", 1),
                ("4 sq mm DC Solar Cable (Roll)", 30),
                ("AC/DC Distribution Box & Isolator Switches", 1),
                ("Aluminium Rooftop Mounting Stands", 1),
                ("Copper Earthing Rod & Lightning Arrester Kit", 1),
                ("Turnkey Rooftop Installation & Commissioning", 1),
            ]),
            ("3kW Off-Grid Solar System", 3.0, "Off-Grid", 215000.0, [
                ("540W Mono PERC Solar Panels", 6),
                ("3kW Solar On-Grid Inverter", 1),
                ("150Ah Solar Tubular Battery", 2),
                ("48V MPPT Solar Charge Controller", 1),
                ("4 sq mm DC Solar Cable (Roll)", 60),
                ("AC/DC Distribution Box & Isolator Switches", 1),
                ("Aluminium Rooftop Mounting Stands", 2),
                ("Copper Earthing Rod & Lightning Arrester Kit", 1),
                ("Turnkey Rooftop Installation & Commissioning", 1),
            ]),
            ("5kW Off-Grid Solar System", 5.0, "Off-Grid", 325000.0, [
                ("540W Mono PERC Solar Panels", 10),
                ("5kW Solar On-Grid Inverter", 1),
                ("150Ah Solar Tubular Battery", 4),
                ("48V MPPT Solar Charge Controller", 1),
                ("4 sq mm DC Solar Cable (Roll)", 90),
                ("AC/DC Distribution Box & Isolator Switches", 1),
                ("Aluminium Rooftop Mounting Stands", 3),
                ("Copper Earthing Rod & Lightning Arrester Kit", 1),
                ("Turnkey Rooftop Installation & Commissioning", 1),
            ]),
        ]

        package_map = {}
        for pname, cap, stype, base_p, comps in packages_definitions:
            sp = SolarPackage(
                name=pname,
                capacity_kw=cap,
                system_type=stype,
                description=f"Standard turnkey {stype} solar rooftop package.",
                base_price=base_p
            )
            db.add(sp)
            db.flush()
            package_map[pname] = sp

            for prod_name, qty in comps:
                pc = PackageComponent(
                    package_id=sp.id,
                    product_id=product_map[prod_name].id,
                    quantity=qty
                )
                db.add(pc)

        db.flush()

        print("Seeding Required Customer: Ravi Kumar...")
        # Customer: Ravi Kumar, Hyderabad, monthly bill ₹6,000, roof 700 sq.ft, needs 5kW On-Grid.
        ravi = Customer(
            name="Ravi Kumar",
            phone="+91 98480 12345",
            email="ravi.kumar@example.com",
            address="Plot 42, Jubilee Hills, Road No. 36",
            city="Hyderabad"
        )
        db.add(ravi)
        db.flush()

        # Seed Lead for Ravi Kumar
        ravi_lead = Lead(
            name="Ravi Kumar",
            phone="+91 98480 12345",
            email="ravi.kumar@example.com",
            address="Plot 42, Jubilee Hills, Road No. 36",
            city="Hyderabad",
            enquiry_source="Web",
            required_capacity=5.0,
            monthly_electricity_bill=6000.0,
            roof_area=700.0,
            grid_type="On-Grid",
            subsidy_requirement=True,
            lead_status="Converted",
            customer_id=ravi.id
        )
        db.add(ravi_lead)

        # Seed additional realistic leads
        other_leads = [
            ("Sita Raman", "+91 98490 55443", "sita.r@example.com", "Plot 12, Banjara Hills", "Hyderabad", "WhatsApp", 3.0, 3800.0, 450.0, "On-Grid", True, "Survey Scheduled"),
            ("Mohan Reddy", "+91 94401 22334", "mohan.reddy@example.com", "House 88, Madhapur", "Hyderabad", "Call", 5.0, 7200.0, 800.0, "On-Grid", False, "New"),
            ("Vikram Patel", "+91 97234 11223", "vikram.p@example.com", "Sector 4, Gandhinagar", "Ahmedabad", "Manual", 3.0, 4200.0, 500.0, "Off-Grid", False, "Contacted"),
        ]
        for name, ph, em, addr, city, src, req_cap, bill, roof, gtype, sub, lst in other_leads:
            db.add(Lead(
                name=name, phone=ph, email=em, address=addr, city=city, enquiry_source=src,
                required_capacity=req_cap, monthly_electricity_bill=bill, roof_area=roof,
                grid_type=gtype, subsidy_requirement=sub, lead_status=lst
            ))

        db.flush()

        print("Seeding Survey for Ravi Kumar (South-facing, low shading, 20° tilt, status Approved)...")
        ravi_survey = SiteSurvey(
            customer_id=ravi.id,
            lead_id=ravi_lead.id,
            technician_id=tech_objs[0].id,
            technician_name=tech_objs[0].name,
            roof_area=700.0,
            roof_direction="South",
            roof_tilt=20.0,
            shading_level="Low",
            cable_distance=18.0,
            grid_suitability="Suitable",
            recommended_capacity=5.0,
            survey_notes="Optimal RCC roof with unshaded south exposure. Excellent structural stability for 5kW On-Grid.",
            status="Approved"
        )
        db.add(ravi_survey)

        # Also seed a pending/draft survey for testing approval hard gate
        draft_survey = SiteSurvey(
            customer_id=ravi.id,
            technician_id=tech_objs[1].id,
            technician_name=tech_objs[1].name,
            roof_area=450.0,
            roof_direction="East",
            roof_tilt=15.0,
            shading_level="Medium",
            cable_distance=25.0,
            grid_suitability="Needs Upgrade",
            recommended_capacity=3.0,
            survey_notes="Pending transformer load clearance from DISCOM.",
            status="Draft"
        )
        db.add(draft_survey)
        db.flush()

        print("Creating Quotation, Sales Order, Payment for Ravi Kumar...")
        pkg_5kw = package_map["5kW On-Grid Solar System"]
        
        # Calculate subtotal from BOM
        subtotal_5kw = sum(comp.quantity * comp.product.unit_price for comp in pkg_5kw.components)
        tax_5kw = round(subtotal_5kw * 0.18, 2)
        total_5kw = round(subtotal_5kw + tax_5kw, 2)

        ravi_quotation = Quotation(
            customer_id=ravi.id,
            survey_id=ravi_survey.id,
            package_id=pkg_5kw.id,
            subtotal=subtotal_5kw,
            tax=tax_5kw,
            total=total_5kw,
            status="Accepted"
        )
        db.add(ravi_quotation)
        db.flush()

        for comp in pkg_5kw.components:
            db.add(QuotationItem(
                quotation_id=ravi_quotation.id,
                product_id=comp.product_id,
                quantity=comp.quantity,
                unit_price=comp.product.unit_price,
                total_price=comp.quantity * comp.product.unit_price
            ))

        # Sales Order
        ravi_order = SalesOrder(
            quotation_id=ravi_quotation.id,
            customer_id=ravi.id,
            package_id=pkg_5kw.id,
            total_amount=total_5kw,
            status="Completed",
            flat_labour_cost=6500.0
        )
        db.add(ravi_order)
        db.flush()

        # Advance payment
        ravi_payment = Payment(
            order_id=ravi_order.id,
            quotation_id=ravi_quotation.id,
            customer_id=ravi.id,
            amount=round(total_5kw * 0.30, 2), # 30% advance
            payment_date=datetime.utcnow() - timedelta(days=20),
            payment_type="advance",
            status="Recorded",
            reference_notes="NEFT Advance transfer from Ravi Kumar HDFC A/C"
        )
        db.add(ravi_payment)

        # Installation for Ravi Kumar
        completion_dt = datetime.utcnow() - timedelta(days=15)
        ravi_installation = Installation(
            sales_order_id=ravi_order.id,
            customer_id=ravi.id,
            technician_id=tech_objs[0].id,
            scheduled_date=(completion_dt - timedelta(days=1)).date(),
            system_capacity=5.0,
            confirmed_system_size=5.0,
            status="Completed",
            start_time=completion_dt - timedelta(hours=6),
            finish_time=completion_dt,
            notes="Mounted 10 panels and installed 5kW inverter. Generation verified at 22.4 kWh/day."
        )
        db.add(ravi_installation)
        db.flush()

        # Link serial INV-2026-0042 to Ravi's installation
        serial_42 = serial_obj_map["INV-2026-0042"]
        serial_42.status = "Installed"
        serial_42.order_id = ravi_order.id
        serial_42.installation_id = ravi_installation.id

        print("Seeding Active Warranty for Ravi Kumar's Inverter (INV-2026-0042)...")
        inv_w_start = completion_dt.date()
        inv_w_end = inv_w_start + timedelta(days=730) # 2 years
        ravi_inv_warranty = Warranty(
            customer_id=ravi.id,
            installation_id=ravi_installation.id,
            order_id=ravi_order.id,
            product_id=product_map["5kW Solar On-Grid Inverter"].id,
            serial_number="INV-2026-0042",
            warranty_type="serialized",
            duration_months=24,
            start_date=inv_w_start,
            end_date=inv_w_end,
            status="Active"
        )
        db.add(ravi_inv_warranty)

        # Also 20-year bulk solar panel warranty for Ravi's order
        ravi_panel_warranty = Warranty(
            customer_id=ravi.id,
            installation_id=ravi_installation.id,
            order_id=ravi_order.id,
            product_id=product_map["540W Mono PERC Solar Panels"].id,
            serial_number=None,
            warranty_type="bulk",
            duration_months=240,
            start_date=inv_w_start,
            end_date=inv_w_start + timedelta(days=7300), # 20 years
            status="Active"
        )
        db.add(ravi_panel_warranty)
        db.flush()

        print("Seeding Ravi Kumar's subsidy file (he asked for the government subsidy)...")
        ravi_subsidy = SubsidyApplication(
            order_id=ravi_order.id,
            customer_id=ravi.id,
            status="Applied",
            reference_number="SUB-2026-RK-001",
            expected_amount=78000.0,
            applied_on=date.today() - timedelta(days=9),
        )
        db.add(ravi_subsidy)
        db.flush()
        for step_status, step_note in [
            ("Documents pending", "File opened because the customer asked for the subsidy"),
            ("Documents collected", "Aadhaar, electricity bill and roof ownership proof received"),
            ("Applied", "Submitted on the national rooftop portal"),
        ]:
            db.add(SubsidyEvent(subsidy_id=ravi_subsidy.id, status=step_status, note=step_note))

        print("Seeding Active Ticket on INV-2026-0042 (COVERED -> Rs. 0)...")
        # Ticket: "Inverter stopped working" on INV-2026-0042 → should resolve to WARRANTY ACTIVE → COVERED → ₹0.
        ravi_ticket = ServiceTicket(
            customer_id=ravi.id,
            equipment_serial="INV-2026-0042",
            installation_id=ravi_installation.id,
            title="Inverter stopped working",
            description="Inverter red LED blinking and no AC power fed into the main DB.",
            priority="High",
            status="Resolved",
            service_type="COVERED",
            customer_charge=0.0,
            customer_confirmed=False
        )
        db.add(ravi_ticket)

        print("Seeding Second Customer with EXPIRED warranty and BILLABLE ticket...")
        # Customer 2: Anand Sharma
        anand = Customer(
            name="Anand Sharma",
            phone="+91 99000 88776",
            email="anand.sharma@example.com",
            address="15, Indiranagar, 100ft Road",
            city="Bengaluru"
        )
        db.add(anand)
        db.flush()

        # Past installation completed 3 years ago (2023-01-15)
        past_completion_dt = datetime(2023, 1, 15, 14, 0, 0)
        past_survey = SiteSurvey(
            customer_id=anand.id,
            technician_id=tech_objs[2].id,
            technician_name=tech_objs[2].name,
            roof_area=650.0,
            roof_direction="South",
            roof_tilt=22.0,
            shading_level="None",
            cable_distance=15.0,
            grid_suitability="Suitable",
            recommended_capacity=5.0,
            survey_notes="Historical survey from 2023.",
            status="Approved"
        )
        db.add(past_survey)
        db.flush()

        past_quote = Quotation(
            customer_id=anand.id,
            survey_id=past_survey.id,
            package_id=pkg_5kw.id,
            subtotal=subtotal_5kw,
            tax=tax_5kw,
            total=total_5kw,
            status="Accepted"
        )
        db.add(past_quote)
        db.flush()

        past_order = SalesOrder(
            quotation_id=past_quote.id,
            customer_id=anand.id,
            package_id=pkg_5kw.id,
            total_amount=total_5kw,
            status="Completed",
            flat_labour_cost=5500.0
        )
        db.add(past_order)
        db.flush()

        past_installation = Installation(
            sales_order_id=past_order.id,
            customer_id=anand.id,
            technician_id=tech_objs[2].id,
            scheduled_date=past_completion_dt.date(),
            system_capacity=5.0,
            confirmed_system_size=5.0,
            status="Completed",
            start_time=past_completion_dt - timedelta(hours=5),
            finish_time=past_completion_dt,
            notes="Commissioned in January 2023."
        )
        db.add(past_installation)
        db.flush()

        # Link past serial INV-2023-0018
        past_serial = serial_obj_map["INV-2023-0018"]
        past_serial.order_id = past_order.id
        past_serial.installation_id = past_installation.id

        # EXPIRED WARRANTY: 2023-01-15 to 2025-01-15 (expired in 2025)
        past_w_start = date(2023, 1, 15)
        past_w_end = date(2025, 1, 15)
        expired_warranty = Warranty(
            customer_id=anand.id,
            installation_id=past_installation.id,
            order_id=past_order.id,
            product_id=product_map["5kW Solar On-Grid Inverter"].id,
            serial_number="INV-2023-0018",
            warranty_type="serialized",
            duration_months=24,
            start_date=past_w_start,
            end_date=past_w_end,
            status="Expired"
        )
        db.add(expired_warranty)
        db.flush()

        # Ticket on INV-2023-0018 -> BILLABLE -> draft invoice created!
        anand_ticket = ServiceTicket(
            customer_id=anand.id,
            equipment_serial="INV-2023-0018",
            installation_id=past_installation.id,
            title="Inverter error code E04 / No AC output",
            description="Inverter displays hardware fault code E04. Display shows warranty period elapsed.",
            priority="Urgent",
            status="Open",
            service_type="BILLABLE",
            customer_charge=7080.0,
            customer_confirmed=False
        )
        db.add(anand_ticket)
        db.flush()

        # Draft invoice for Anand's ticket
        anand_invoice = Invoice(
            invoice_number=f"INV-SRV-{anand_ticket.id:04d}",
            customer_id=anand.id,
            order_id=past_order.id,
            ticket_id=anand_ticket.id,
            subtotal=6000.0,
            tax=1080.0,
            total=7080.0,
            status="Draft"
        )
        db.add(anand_invoice)
        db.flush()

        # Add invoice items
        db.add(InvoiceItem(
            invoice_id=anand_invoice.id,
            description="Replacement Inverter Power Board / Capacitors",
            quantity=1,
            unit_price=4500.0,
            total=4500.0
        ))
        db.add(InvoiceItem(
            invoice_id=anand_invoice.id,
            description="Emergency Technician Diagnostic & Replacement Labour",
            quantity=1,
            unit_price=1500.0,
            total=1500.0
        ))

        anand_ticket.invoice_id = anand_invoice.id

        db.commit()
        print("SEEDING COMPLETE SUCCESSFULLY!")
        print(f"Demo staff logins (password for all: {DEMO_PASSWORD}):")
        for email, _name, role in DEMO_STAFF:
            print(f"   {role:<10} {email}")
        print("1. Ravi Kumar (INV-2026-0042) -> Active Warranty -> COVERED -> Rs. 0")
        print("2. Anand Sharma (INV-2023-0018) -> Expired Warranty -> BILLABLE -> Draft Invoice Rs. 7,080")
    except Exception as e:
        db.rollback()
        print("ERROR DURING SEEDING:", e)
        raise e
    finally:
        db.close()

if __name__ == "__main__":
    seed_database()
