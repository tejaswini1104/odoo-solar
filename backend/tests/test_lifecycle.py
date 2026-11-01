"""The whole customer journey, from the first call to the 20-year warranty, through the real API."""
import base64
from datetime import date, datetime, timedelta

from backend.app.models.models import (
    Customer, EquipmentSerial, InventoryItem, Invoice, Lead, Notification, SalesOrder, StockPurchase,
    StockPurchaseItem, Warranty,
)

# A valid 1x1 PNG and JPEG-less proof: enough for the file-type checks
PNG = base64.b64decode(
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8z8BQDwAEhQGAhKmMIQAAAABJRU5ErkJggg=="
)
SIGNATURE = "data:image/png;base64," + base64.b64encode(PNG).decode()


def make_lead(db, customer_id, status="New"):
    lead = Lead(
        name="Ravi Kumar", phone="9876500001", email="ravi@t.test", address="12 Lake Road", city="Hyderabad",
        enquiry_source="Web", required_capacity=3, monthly_electricity_bill=4000, roof_area=500,
        grid_type="On-Grid", subsidy_requirement=False, lead_status=status, customer_id=customer_id,
    )
    db.add(lead)
    db.commit()
    return lead


def approved_survey(api, ids, db):
    """Call the customer, book the survey, let the technician measure and approve it. Returns the survey id."""
    lead = make_lead(db, ids["customer"])
    booked = api["sales"].post("/api/surveys/schedule", json={"customer_id": ids["customer"], "lead_id": lead.id, "scheduled_date": ids["tomorrow"]})
    assert booked.status_code == 400, "Booking before the first call must be refused"

    call = api["sales"].post(f"/api/leads/{lead.id}/status", json={"status": "Contacted", "shadow_free_area": 420, "grid_connection_ok": True})
    assert call.status_code == 200, call.text
    booked = api["sales"].post("/api/surveys/schedule", json={"customer_id": ids["customer"], "lead_id": lead.id, "scheduled_date": ids["tomorrow"]})
    assert booked.status_code == 201, booked.text
    survey_id = booked.json()["id"]

    done = api["technician"].put(f"/api/surveys/{survey_id}/complete", json={
        "roof_area": 420, "roof_direction": "South", "roof_tilt": 20, "shading_level": "Low", "cable_distance": 15,
        "grid_suitability": "Suitable", "recommended_capacity": 3, "recommended_system_type": "On-Grid",
    })
    assert done.status_code == 200, done.text
    assert api["sales"].post(f"/api/surveys/{survey_id}/approve").status_code == 200
    return survey_id


def confirmed_order(api, ids, db):
    survey_id = approved_survey(api, ids, db)
    quote = api["sales"].post("/api/quotations", json={"customer_id": ids["customer"], "survey_id": survey_id, "package_id": ids["package"]})
    assert quote.status_code == 200, quote.text
    quote = quote.json()
    assert api["sales"].post(f"/api/quotations/{quote['id']}/send").status_code == 200
    order = api["sales"].post(f"/api/quotations/{quote['id']}/confirm").json()

    refused = api["sales"].post(f"/api/orders/{order['id']}/confirm")
    assert refused.status_code == 400, "No verified advance yet, so confirmation must fail"

    advance = round(order["total_amount"] * 0.30, 2)
    paid = api["sales"].post("/api/payments", json={"order_id": order["id"], "customer_id": ids["customer"], "amount": advance})
    assert paid.status_code == 200, paid.text
    confirmed = api["sales"].post(f"/api/orders/{order['id']}/confirm")
    assert confirmed.status_code == 200, confirmed.text
    return order["id"], quote


def prepare_ticket(api, db, ticket, replacement=None):
    """Take a ticket through the steps before resolving: technician, site visit, quotation if billable, dispatch."""
    from backend.app.models.models import Technician
    tid = ticket["id"]
    tech = db.query(Technician).first()
    assert api["support"].post(f"/api/tickets/{tid}/assign", json={"technician_id": tech.id}).status_code == 200
    visit = api["technician"].post(f"/api/repair-visits/{tid}/report", json={"needs_replacement": bool(replacement), "notes": "Checked on site"})
    assert visit.status_code == 200, visit.text
    if ticket["service_type"] == "BILLABLE":
        assert api["support"].post(f"/api/tickets/{tid}/quote", json={"approved": True}).status_code == 200
    if replacement:
        sent = api["warehouse"].post(f"/api/dispatch/replacements/{tid}/send", json={"serial_number": replacement})
        assert sent.status_code == 200, sent.text


def dispatch_and_deliver(api, order_id):
    pick = api["warehouse"].get(f"/api/dispatch/{order_id}/pick-list").json()
    names = {line["product_name"] for line in pick["lines"]}
    assert {"Solar Panel 540W", "Mounting Stands", "3kW Inverter", "Charge Controller"} <= names
    assert "Installation" not in names, "A service is not packed"
    assert pick["lines"][0]["is_serialized"], "Serial-numbered units are listed first"

    sent = api["warehouse"].post(f"/api/dispatch/{order_id}/serials", json={"serial_numbers": ["INV-T-001", "CC-T-001"]})
    assert sent.status_code == 200, sent.text
    delivered = api["warehouse"].post(f"/api/dispatch/{order_id}/delivered")
    assert delivered.status_code == 200, delivered.text


def test_full_journey_to_warranty(api, ids, db):
    order_id, quote = confirmed_order(api, ids, db)

    # Confirmation alerts the warehouse and the technician, and tells the customer
    roles = {(n.role, n.technician_id is not None) for n in db.query(Notification).all()}
    assert ("warehouse", False) in roles
    assert (None, True) in roles
    order = db.get(SalesOrder, order_id)
    assert order.installation is not None and order.installation.technician_id is not None
    assert db.query(InventoryItem).join(InventoryItem.product).filter_by(name="Solar Panel 540W").one().reserved_quantity == 6

    dispatch_and_deliver(api, order_id)
    db.expire_all()
    warranties = db.query(Warranty).filter(Warranty.order_id == order_id).all()
    by_type = {w.warranty_type: w for w in warranties}
    assert len([w for w in warranties if w.warranty_type == "serialized"]) == 2
    assert all(w.duration_months == 24 for w in warranties if w.warranty_type == "serialized")
    assert by_type["bulk"].duration_months == 240, "Panels carry a 20 year warranty"

    # The crew cannot finish without proof, and then can
    inst = db.get(SalesOrder, order_id).installation
    start = (datetime.utcnow() - timedelta(hours=5)).isoformat()
    body = {"confirmed_system_size": 3, "serial_numbers": ["INV-T-001", "CC-T-001"], "start_time": start}
    assert api["technician"].post(f"/api/installations/{inst.id}/complete", json=body).status_code == 400
    photo = api["technician"].post(f"/api/installations/{inst.id}/photos", files={"file": ("roof.png", PNG, "image/png")}, data={"caption": "Finished roof"})
    assert photo.status_code == 201, photo.text
    sign = api["technician"].post(f"/api/installations/{inst.id}/signature", json={"signed_by": "Ravi Kumar", "signature_data_url": SIGNATURE})
    assert sign.status_code == 200, sign.text
    done = api["technician"].post(f"/api/installations/{inst.id}/complete", json=body)
    assert done.status_code == 200, done.text

    db.expire_all()
    assert db.query(Warranty).filter(Warranty.order_id == order_id).count() == 3, "Completion must not warrant anything twice"
    assert db.get(SalesOrder, order_id).status == "Completed"

    # Profit: panels (6 x 8000) + stands 4000 + two serials (30000 + 5000), labour 5 h at 300
    rows = api["admin"].get("/api/profitability").json()
    assert len(rows) == 1
    row = rows[0]
    assert row["material_cost"] == 6 * 8000 + 4000 + 30000 + 5000
    assert row["labour_cost"] == 1500
    assert row["amount_paid"] > 0 and row["balance_due"] == round(order.total_amount - row["amount_paid"], 2)


def test_profit_uses_what_was_really_paid_for_stock(api, ids, db):
    order_id, _ = confirmed_order(api, ids, db)
    dispatch_and_deliver(api, order_id)
    panels = db.query(InventoryItem).join(InventoryItem.product).filter_by(name="Solar Panel 540W").one().product
    purchase = StockPurchase(supplier="Sun Supply", purchased_on=date.today(), total_cost=0)
    db.add(purchase)
    db.flush()
    db.add(StockPurchaseItem(purchase_id=purchase.id, product_id=panels.id, quantity=100, unit_cost=7000))
    db.commit()

    inst = db.get(SalesOrder, order_id).installation
    start = (datetime.utcnow() - timedelta(hours=2)).isoformat()
    api["technician"].post(f"/api/installations/{inst.id}/photos", files={"file": ("r.png", PNG, "image/png")})
    api["technician"].post(f"/api/installations/{inst.id}/signature", json={"signed_by": "Ravi", "signature_data_url": SIGNATURE})
    assert api["technician"].post(f"/api/installations/{inst.id}/complete", json={"confirmed_system_size": 3, "serial_numbers": ["INV-T-001", "CC-T-001"], "start_time": start}).status_code == 200

    row = api["admin"].get("/api/profitability").json()[0]
    assert row["material_cost"] == 6 * 7000 + 4000 + 30000 + 5000, "Panels are costed at the 7000 actually paid, not the 8000 list cost"


def test_repair_ticket_free_under_warranty_and_auto_priced_after(api, ids, db):
    order_id, _ = confirmed_order(api, ids, db)
    dispatch_and_deliver(api, order_id)

    covered = api["support"].post("/api/tickets", json={"customer_id": ids["customer"], "equipment_serial": "INV-T-001", "title": "No power", "description": "Fault code E04"})
    assert covered.status_code == 200, covered.text
    assert covered.json()["service_type"] == "COVERED" and covered.json()["customer_charge"] == 0

    # Eighteen months later the 2 year cover still applies; at 25 months it has ended
    warranty = db.query(Warranty).filter_by(serial_number="CC-T-001").one()
    warranty.end_date = date.today() - timedelta(days=1)
    db.commit()
    billable = api["support"].post("/api/tickets", json={"customer_id": ids["customer"], "equipment_serial": "CC-T-001", "title": "Dead controller", "description": "No charge"}).json()
    assert billable["service_type"] == "BILLABLE"
    invoice = db.get(Invoice, billable["invoice_id"])
    part, labour = 7000.0, 1500.0
    assert [i.total for i in invoice.items] == [part, labour], "Priced from the faulty part and the labour charge, not a placeholder"
    assert invoice.subtotal == part + labour
    assert invoice.tax == round((part + labour) * 0.18, 2)
    assert billable["customer_charge"] == invoice.total

    # Tracked until the customer confirms
    ticket_id = covered.json()["id"]
    assert api["support"].post(f"/api/tickets/{ticket_id}/close").status_code == 400
    assert api["support"].post(f"/api/tickets/{ticket_id}/customer-confirm").status_code == 400, "Not resolved yet"
    assert api["support"].post(f"/api/tickets/{ticket_id}/resolve").status_code == 400, "No technician or site visit yet"
    prepare_ticket(api, db, covered.json())
    assert api["support"].post(f"/api/tickets/{ticket_id}/resolve").status_code == 200
    assert api["support"].post(f"/api/tickets/{ticket_id}/customer-confirm").status_code == 200
    assert api["support"].post(f"/api/tickets/{ticket_id}/close").json()["status"] == "Closed"


def test_ticket_for_unknown_or_other_customers_serial_is_refused(api, ids, db):
    order_id, _ = confirmed_order(api, ids, db)
    dispatch_and_deliver(api, order_id)
    ticket = {"customer_id": ids["customer"], "title": "No power", "description": "Fault code E04"}
    assert api["support"].post("/api/tickets", json={**ticket, "equipment_serial": "NOPE-1"}).status_code == 404
    assert api["support"].post("/api/tickets", json={**ticket, "equipment_serial": "INV-T-002"}).status_code == 400, "Still in stock, never delivered"
    other = Customer(name="Other", phone="1", email="o@t.test", address="a", city="c")
    db.add(other)
    db.commit()
    assert api["support"].post("/api/tickets", json={**ticket, "customer_id": other.id, "equipment_serial": "INV-T-001"}).status_code == 403


def test_support_finds_customer_and_serial_in_one_search(api, ids, db):
    order_id, _ = confirmed_order(api, ids, db)
    dispatch_and_deliver(api, order_id)
    for term in ("9876500001", "Ravi", "INV-T-001", "Lake Road"):
        hits = api["support"].get("/api/customers/search", params={"q": term}).json()
        assert len(hits) == 1 and hits[0]["name"] == "Ravi Kumar", term
    equipment = {e["serial_number"]: e for e in hits[0]["equipment"]}
    assert equipment["INV-T-001"]["under_warranty"] is True


def test_cancelling_an_order_frees_its_stock(api, ids, db):
    survey_id = approved_survey(api, ids, db)
    quote = api["sales"].post("/api/quotations", json={"customer_id": ids["customer"], "survey_id": survey_id, "package_id": ids["package"]}).json()
    api["sales"].post(f"/api/quotations/{quote['id']}/send")
    order = api["sales"].post(f"/api/quotations/{quote['id']}/confirm").json()
    api["sales"].post("/api/payments", json={"order_id": order["id"], "customer_id": ids["customer"], "amount": round(order["total_amount"] * 0.3, 2)})
    api["sales"].post(f"/api/orders/{order['id']}/confirm")

    assert api["sales"].post(f"/api/orders/{order['id']}/cancel", json={"reason": "x"}).status_code == 422
    cancelled = api["sales"].post(f"/api/orders/{order['id']}/cancel", json={"reason": "Customer changed their mind"})
    assert cancelled.status_code == 200 and cancelled.json()["status"] == "Cancelled"
    db.expire_all()
    assert all(i.reserved_quantity == 0 for i in db.query(InventoryItem).all())
    assert db.get(SalesOrder, order["id"]).installation is None
    assert api["warehouse"].post(f"/api/orders/{order['id']}/cancel", json={"reason": "no"}).status_code == 403


def test_a_dispatched_order_cannot_be_cancelled(api, ids, db):
    order_id, _ = confirmed_order(api, ids, db)
    dispatch_and_deliver(api, order_id)
    assert api["sales"].post(f"/api/orders/{order_id}/cancel", json={"reason": "Too late now"}).status_code == 400
