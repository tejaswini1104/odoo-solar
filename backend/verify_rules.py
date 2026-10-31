import os
import sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from fastapi import HTTPException
from backend.app.core.database import SessionLocal
from backend.app.models.models import SiteSurvey, Customer, SolarPackage, EquipmentSerial, Payment, SalesOrder, ServiceTicket, Warranty
from backend.app.schemas.schemas import QuotationCreate, ServiceTicketCreate
from backend.app.services.quotation_service import QuotationService
from backend.app.services.order_service import OrderService
from backend.app.services.dispatch_service import DispatchService
from backend.app.services.installation_service import InstallationService
from backend.app.services.ticket_service import TicketService

def test_hard_gates():
    db = SessionLocal()
    print("--------------------------------------------------")
    print("RUNNING STRICT PHASE 1 RULE VERIFICATION")
    print("--------------------------------------------------")

    # 1. QUOTATION HARD GATE: Survey Must Be Approved
    print("\n[Rule 1] Hard Gate: Quotation cannot be created without Approved survey...")
    customer = db.query(Customer).first()
    package = db.query(SolarPackage).filter(SolarPackage.capacity_kw == 3.0, SolarPackage.system_type == "On-Grid").first()

    # Create a fresh draft survey
    draft_survey = SiteSurvey(
        customer_id=customer.id,
        technician_name="Surveyor Test",
        roof_area=400.0,
        roof_direction="North",
        roof_tilt=18.0,
        shading_level="High",
        cable_distance=20.0,
        grid_suitability="Pending",
        recommended_capacity=3.0,
        survey_notes="Initial test survey in draft state",
        status="Draft"
    )
    db.add(draft_survey)
    db.commit()
    assert customer is not None, "Customer missing"
    assert package is not None, "Package missing"

    try:
        QuotationService.create_quotation(
            db,
            QuotationCreate(
                customer_id=customer.id,
                survey_id=draft_survey.id,
                package_id=package.id
            )
        )
        print("FAIL: Quotation allowed with Draft survey!")
        assert False, "Should have raised HTTPException"
    except HTTPException as e:
        print(f"PASS: Correctly rejected with HTTP {e.status_code}: {e.detail}")

    # Now approve survey and test quotation creation
    draft_survey.status = "Approved"
    db.commit()
    q = QuotationService.create_quotation(
        db,
        QuotationCreate(
            customer_id=customer.id,
            survey_id=draft_survey.id,
            package_id=package.id
        )
    )
    print(f"PASS: Quotation #{q.id} created successfully after approval with {len(q.items)} auto-generated BOM items! Total: Rs. {q.total}")

    # 2. ORDER CONFIRMATION HARD GATE: Requires survey approved + advance payment recorded
    print("\n[Rule 2] Hard Gate: Order confirmation requires advance payment...")
    order = OrderService.create_or_get_order_from_quotation(db, q.id)
    try:
        OrderService.confirm_order(db, order.id)
        print("FAIL: Order confirmed without payment!")
        assert False, "Should have raised HTTPException"
    except HTTPException as e:
        print(f"PASS: Correctly rejected order confirmation: {e.detail}")

    # Add payment and confirm
    pay = Payment(
        order_id=order.id,
        quotation_id=q.id,
        customer_id=customer.id,
        amount=50000.0,
        payment_type="advance",
        status="Recorded"
    )
    db.add(pay)
    db.commit()

    confirmed_order = OrderService.confirm_order(db, order.id)
    assert confirmed_order.status == "Confirmed"
    assert confirmed_order.installation is not None
    print(f"PASS: Order #{confirmed_order.id} confirmed! Installation #{confirmed_order.installation.id} auto-created for technician '{confirmed_order.installation.technician.name}'.")

    # 3. DISPATCH HARD GATE: Serial Number Validation
    print("\n[Rule 3] Hard Gate: Dispatch rejects missing or invalid serial numbers...")
    try:
        # Try dispatching with invalid serial number
        DispatchService.dispatch_serials(db, confirmed_order.id, ["INVALID-SERIAL-999"])
        print("FAIL: Dispatch allowed invalid serial!")
        assert False, "Should have raised HTTPException"
    except HTTPException as e:
        print(f"PASS: Correctly rejected invalid serial dispatch: {e.detail}")

    # Find in-stock serial for 3kW inverter
    serial_3k = db.query(EquipmentSerial).filter(
        EquipmentSerial.product_id == package.components[1].product_id, # Inverter
        EquipmentSerial.status == "In Stock"
    ).first()
    assert serial_3k is not None, "In-stock 3kW inverter serial needed"

    dispatched_order = DispatchService.dispatch_serials(db, confirmed_order.id, [serial_3k.serial_number])
    assert dispatched_order.status == "Dispatched"
    assert serial_3k.status == "Dispatched"
    print(f"PASS: Order #{dispatched_order.id} dispatched with serial '{serial_3k.serial_number}'!")

    # 4. INSTALLATION COMPLETION & AUTOMATIC WARRANTY CREATION
    print("\n[Rule 4] Automatic Warranty Engine on Installation Completion...")
    inst = confirmed_order.installation
    completed_inst = InstallationService.complete_installation(
        db,
        installation_id=inst.id,
        confirmed_system_size=3.0,
        serial_numbers=[serial_3k.serial_number]
    )
    assert completed_inst.status == "Completed"
    assert serial_3k.status == "Installed"

    # Check warranties created
    warranties = db.query(Warranty).filter(Warranty.installation_id == completed_inst.id).all()
    print("DEBUG Warranties found:", [(w.id, w.product_id, w.warranty_type, w.serial_number) for w in warranties])
    assert len(warranties) >= 2, f"Expected at least inverter + panel warranties, got {len(warranties)}"
    inv_w = [w for w in warranties if w.serial_number == serial_3k.serial_number][0]
    panel_w = [w for w in warranties if w.warranty_type == "bulk"][0]

    assert inv_w.status == "Active" and inv_w.duration_months == 24
    assert panel_w.status == "Active" and panel_w.duration_months == 240
    print(f"PASS: Warranties automatically created: Inverter {inv_w.duration_months}mo (End: {inv_w.end_date}), Panels {panel_w.duration_months}mo (End: {panel_w.end_date})!")

    # 5. SERVICE TICKET & WARRANTY DECISION
    print("\n[Rule 5] Service Ticket Warranty Decision: Active vs Expired...")
    # Active ticket test
    active_ticket = TicketService.create_ticket(
        db,
        ServiceTicketCreate(
            customer_id=customer.id,
            equipment_serial=serial_3k.serial_number,
            title="Slight inverter buzzing noise",
            description="Noise observed during peak generation."
        )
    )
    assert active_ticket.service_type == "COVERED"
    assert active_ticket.customer_charge == 0.0
    assert active_ticket.invoice_id is None
    print(f"PASS: Active warranty ticket resolved to '{active_ticket.service_type}', customer_charge: Rs. {active_ticket.customer_charge}")

    # Expired ticket test (INV-2023-0018)
    expired_ticket = TicketService.create_ticket(
        db,
        ServiceTicketCreate(
            customer_id=customer.id,
            equipment_serial="INV-2023-0018",
            title="Out-of-warranty capacitor breakdown",
            description="Inverter blown fuse and failed capacitor."
        )
    )
    assert expired_ticket.service_type == "BILLABLE"
    assert expired_ticket.customer_charge > 0.0
    assert expired_ticket.invoice_id is not None
    print(f"PASS: Expired warranty ticket resolved to '{expired_ticket.service_type}', customer_charge: Rs. {expired_ticket.customer_charge}, draft invoice #{expired_ticket.invoice_id} auto-created!")

    # 6. TICKET CLOSURE HARD GATE: Customer Confirmation Mandatory
    print("\n[Rule 6] Hard Gate: Ticket cannot be closed without customer confirmation...")
    try:
        TicketService.close_ticket(db, active_ticket.id)
        print("FAIL: Ticket closed without customer confirmation!")
        assert False, "Should have raised HTTPException"
    except HTTPException as e:
        print(f"PASS: Correctly rejected closure: {e.detail}")

    TicketService.customer_confirm_ticket(db, active_ticket.id)
    closed_ticket = TicketService.close_ticket(db, active_ticket.id)
    assert closed_ticket.status == "Closed"
    print(f"PASS: Ticket #{closed_ticket.id} closed after customer confirmation!")

    print("\n--------------------------------------------------")
    print("ALL PHASE 1 BACKEND BUSINESS RULES FULLY VERIFIED!")
    print("--------------------------------------------------")
    db.close()

if __name__ == "__main__":
    test_hard_gates()
