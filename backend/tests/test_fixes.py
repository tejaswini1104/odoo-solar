"""Rules added after reviewing the build against the SunPower problem statement."""
from datetime import date, timedelta

from backend.app.core.config import settings
from backend.app.models.models import Customer, EquipmentSerial, InventoryItem, Invoice, Notification, Technician, Warranty
from backend.tests.test_lifecycle import approved_survey, confirmed_order, dispatch_and_deliver, make_lead, prepare_ticket

FAULT = {"title": "No power", "description": "Fault code E04 on the display"}


def submitted_survey(api, ids, db):
    """A survey the technician has recorded and that now waits for Sales to decide."""
    lead = make_lead(db, ids["customer"])
    api["sales"].post(f"/api/leads/{lead.id}/status", json={"status": "Contacted", "shadow_free_area": 420, "grid_connection_ok": True})
    survey_id = api["sales"].post("/api/surveys/schedule", json={"customer_id": ids["customer"], "lead_id": lead.id, "scheduled_date": ids["tomorrow"]}).json()["id"]
    api["technician"].put(f"/api/surveys/{survey_id}/complete", json={
        "roof_area": 420, "roof_direction": "South", "roof_tilt": 20, "shading_level": "Low", "cable_distance": 15,
        "grid_suitability": "Suitable", "recommended_capacity": 3, "recommended_system_type": "On-Grid",
    })
    return survey_id


def test_quotation_cannot_use_another_customers_survey(api, ids, db):
    survey_id = approved_survey(api, ids, db)
    other = Customer(name="Anand Sharma", phone="9876500002", email="anand@t.test", address="9 Hill Street", city="Bengaluru")
    db.add(other)
    db.commit()
    refused = api["sales"].post("/api/quotations", json={"customer_id": other.id, "survey_id": survey_id, "package_id": ids["package"]})
    assert refused.status_code == 400 and "different customer" in refused.json()["detail"]
    assert api["sales"].post("/api/quotations", json={"customer_id": ids["customer"], "survey_id": survey_id, "package_id": ids["package"]}).status_code == 200


def test_survey_is_decided_once_and_only_by_sales(api, ids, db):
    survey_id = submitted_survey(api, ids, db)
    assert api["technician"].post(f"/api/surveys/{survey_id}/approve").status_code == 403, "The technician who measured does not approve"
    assert api["technician"].post(f"/api/surveys/{survey_id}/reject").status_code == 403
    assert api["support"].post(f"/api/surveys/{survey_id}/approve").status_code == 403

    assert api["sales"].post(f"/api/surveys/{survey_id}/approve").status_code == 200
    assert api["sales"].post(f"/api/surveys/{survey_id}/reject").status_code == 400, "An approved survey cannot be rejected afterwards"
    assert api["sales"].post(f"/api/surveys/{survey_id}/approve").status_code == 400


def test_survey_not_yet_measured_cannot_be_decided(api, ids, db):
    lead = make_lead(db, ids["customer"])
    api["sales"].post(f"/api/leads/{lead.id}/status", json={"status": "Contacted", "shadow_free_area": 420, "grid_connection_ok": True})
    survey_id = api["sales"].post("/api/surveys/schedule", json={"customer_id": ids["customer"], "lead_id": lead.id, "scheduled_date": ids["tomorrow"]}).json()["id"]
    assert api["sales"].post(f"/api/surveys/{survey_id}/reject").status_code == 400
    assert api["sales"].post(f"/api/surveys/{survey_id}/approve").status_code == 400


def test_rejected_survey_stays_rejected(api, ids, db):
    survey_id = submitted_survey(api, ids, db)
    assert api["sales"].post(f"/api/surveys/{survey_id}/reject").status_code == 200
    assert api["sales"].post(f"/api/surveys/{survey_id}/approve").status_code == 400
    quote = api["sales"].post("/api/quotations", json={"customer_id": ids["customer"], "survey_id": survey_id, "package_id": ids["package"]})
    assert quote.status_code == 400


def test_gst_rate_comes_from_settings(api, ids, db, monkeypatch):
    monkeypatch.setattr(settings, "GST_PERCENT", 12.0)
    survey_id = approved_survey(api, ids, db)
    quote = api["sales"].post("/api/quotations", json={"customer_id": ids["customer"], "survey_id": survey_id, "package_id": ids["package"]}).json()
    assert quote["tax"] == round(quote["subtotal"] * 0.12, 2)


def test_panel_warranty_claim_without_a_serial_number(api, ids, db):
    order_id, _ = confirmed_order(api, ids, db)
    dispatch_and_deliver(api, order_id)
    panels = db.query(Warranty).filter_by(order_id=order_id, warranty_type="bulk").one()

    covered = api["support"].post("/api/tickets", json={"customer_id": ids["customer"], "warranty_id": panels.id, **FAULT})
    assert covered.status_code == 200, covered.text
    assert covered.json()["service_type"] == "COVERED" and covered.json()["customer_charge"] == 0
    assert covered.json()["equipment_serial"] == f"PANELS-SO{order_id:04d}"

    # A serial and a warranty together, or neither, is refused
    assert api["support"].post("/api/tickets", json={"customer_id": ids["customer"], "warranty_id": panels.id, "equipment_serial": "INV-T-001", **FAULT}).status_code == 422
    assert api["support"].post("/api/tickets", json={"customer_id": ids["customer"], **FAULT}).status_code == 422

    # Once the 20 years are over the claim is priced from one panel plus labour
    panels.end_date = date.today() - timedelta(days=1)
    db.commit()
    billable = api["support"].post("/api/tickets", json={"customer_id": ids["customer"], "warranty_id": panels.id, **FAULT}).json()
    assert billable["service_type"] == "BILLABLE"
    invoice = db.get(Invoice, billable["invoice_id"])
    assert [i.total for i in invoice.items] == [10000.0, settings.SERVICE_LABOUR_CHARGE]


def test_panel_claim_is_limited_to_the_owner_and_to_bulk_warranties(api, ids, db):
    order_id, _ = confirmed_order(api, ids, db)
    dispatch_and_deliver(api, order_id)
    panels = db.query(Warranty).filter_by(order_id=order_id, warranty_type="bulk").one()
    serialized = db.query(Warranty).filter_by(order_id=order_id, warranty_type="serialized").first()
    other = Customer(name="Anand Sharma", phone="9876500002", email="anand@t.test", address="9 Hill Street", city="Bengaluru")
    db.add(other)
    db.commit()
    assert api["support"].post("/api/tickets", json={"customer_id": other.id, "warranty_id": panels.id, **FAULT}).status_code == 403
    assert api["support"].post("/api/tickets", json={"customer_id": ids["customer"], "warranty_id": serialized.id, **FAULT}).status_code == 404
    assert api["support"].post("/api/tickets", json={"customer_id": ids["customer"], "warranty_id": 9999, **FAULT}).status_code == 404


def test_no_repair_ticket_for_equipment_still_on_the_truck(api, ids, db):
    order_id, _ = confirmed_order(api, ids, db)
    assert api["warehouse"].post(f"/api/dispatch/{order_id}/serials", json={"serial_numbers": ["INV-T-001", "CC-T-001"]}).status_code == 200
    refused = api["support"].post("/api/tickets", json={"customer_id": ids["customer"], "equipment_serial": "INV-T-001", **FAULT})
    assert refused.status_code == 400 and "not marked delivered" in refused.json()["detail"]
    assert api["warehouse"].post(f"/api/dispatch/{order_id}/delivered").status_code == 200
    assert api["support"].post("/api/tickets", json={"customer_id": ids["customer"], "equipment_serial": "INV-T-001", **FAULT}).status_code == 200


def test_replacement_unit_is_tracked_and_inherits_the_remaining_warranty(api, ids, db):
    order_id, _ = confirmed_order(api, ids, db)
    dispatch_and_deliver(api, order_id)
    original = db.query(Warranty).filter_by(serial_number="INV-T-001").one()
    original_end = original.end_date
    on_hand = db.query(InventoryItem).join(InventoryItem.product).filter_by(name="3kW Inverter").one().quantity_on_hand

    ticket = api["support"].post("/api/tickets", json={"customer_id": ids["customer"], "equipment_serial": "INV-T-001", **FAULT}).json()
    assert ticket["service_type"] == "COVERED"

    # Nothing can be dispatched or resolved before a technician has inspected
    assert api["warehouse"].post(f"/api/dispatch/replacements/{ticket['id']}/send", json={"serial_number": "INV-T-002"}).status_code == 400
    assert api["support"].post(f"/api/tickets/{ticket['id']}/resolve").status_code == 400
    prepare_ticket(api, db, ticket)  # inspection finds no replacement is needed...
    assert api["warehouse"].post(f"/api/dispatch/replacements/{ticket['id']}/send", json={"serial_number": "INV-T-002"}).status_code == 400
    db.expire_all()
    assert db.query(EquipmentSerial).filter_by(serial_number="INV-T-002").one().status == "In Stock"

    # ...so use a second ticket where the technician does ask for a replacement
    ticket = api["support"].post("/api/tickets", json={"customer_id": ids["customer"], "equipment_serial": "INV-T-001", **FAULT}).json()
    tech = db.query(Technician).first()
    api["support"].post(f"/api/tickets/{ticket['id']}/assign", json={"technician_id": tech.id})
    api["technician"].post(f"/api/repair-visits/{ticket['id']}/report", json={"needs_replacement": True})
    assert api["support"].post(f"/api/tickets/{ticket['id']}/resolve").status_code == 400, "Replacement not dispatched yet"
    # The request goes to the warehouse: support cannot pick stock, the warehouse can see the request
    assert api["support"].get("/api/tickets").json()[0]["status"] == "Awaiting Dispatch"
    assert api["support"].post(f"/api/dispatch/replacements/{ticket['id']}/send", json={"serial_number": "INV-T-002"}).status_code == 403
    waiting = api["warehouse"].get("/api/dispatch/replacements/list").json()
    assert [w["ticket_id"] for w in waiting] == [ticket["id"]] and "INV-T-002" in waiting[0]["available_serials"]
    assert any(n.title.startswith("Replacement to dispatch") for n in db.query(Notification).filter_by(role="warehouse"))
    # Wrong product, a unit that is not in stock, and an unknown serial are all refused and change nothing
    assert api["warehouse"].post(f"/api/dispatch/replacements/{ticket['id']}/send", json={"serial_number": "CC-T-002"}).status_code == 400
    assert api["warehouse"].post(f"/api/dispatch/replacements/{ticket['id']}/send", json={"serial_number": "INV-T-001"}).status_code == 400
    assert api["warehouse"].post(f"/api/dispatch/replacements/{ticket['id']}/send", json={"serial_number": "NOPE-1"}).status_code == 404
    db.expire_all()
    assert db.query(EquipmentSerial).filter_by(serial_number="INV-T-002").one().status == "In Stock"

    sent = api["warehouse"].post(f"/api/dispatch/replacements/{ticket['id']}/send", json={"serial_number": "INV-T-002"})
    assert sent.status_code == 200 and sent.json()["status"] == "Dispatched", sent.text
    db.expire_all()
    assert db.query(EquipmentSerial).filter_by(serial_number="INV-T-002").one().status == "Dispatched"
    assert db.query(InventoryItem).join(InventoryItem.product).filter_by(name="3kW Inverter").one().quantity_on_hand == on_hand - 1

    resolved = api["support"].post(f"/api/tickets/{ticket['id']}/resolve")
    assert resolved.status_code == 200, resolved.text
    assert resolved.json()["status"] == "Resolved" and resolved.json()["replacement_serial"] == "INV-T-002"

    db.expire_all()
    old = db.query(EquipmentSerial).filter_by(serial_number="INV-T-001").one()
    new = db.query(EquipmentSerial).filter_by(serial_number="INV-T-002").one()
    assert old.status == "Replaced"
    assert new.status == "Installed" and new.order_id == order_id and new.installation_id == old.installation_id
    assert db.query(InventoryItem).join(InventoryItem.product).filter_by(name="3kW Inverter").one().quantity_on_hand == on_hand - 1
    warranty = db.query(Warranty).filter_by(serial_number="INV-T-002").one()
    assert warranty.end_date == original_end and warranty.start_date == original.start_date, "A free replacement carries on with the original cover"
    assert warranty.status == "Active"
    assert db.query(Warranty).filter_by(serial_number="INV-T-001").one().status == "Replaced"

    # The swapped-out unit can no longer take tickets; its replacement can
    gone = api["support"].post("/api/tickets", json={"customer_id": ids["customer"], "equipment_serial": "INV-T-001", **FAULT})
    assert gone.status_code == 400 and "INV-T-001" in gone.json()["detail"]
    assert api["support"].post("/api/tickets", json={"customer_id": ids["customer"], "equipment_serial": "INV-T-002", **FAULT}).json()["service_type"] == "COVERED"


def test_paid_replacement_gets_a_full_new_warranty(api, ids, db):
    order_id, _ = confirmed_order(api, ids, db)
    dispatch_and_deliver(api, order_id)
    db.query(Warranty).filter_by(serial_number="CC-T-001").one().end_date = date.today() - timedelta(days=1)
    db.commit()
    ticket = api["support"].post("/api/tickets", json={"customer_id": ids["customer"], "equipment_serial": "CC-T-001", **FAULT}).json()
    assert ticket["service_type"] == "BILLABLE"
    prepare_ticket(api, db, ticket, replacement="CC-T-002")
    assert api["support"].post(f"/api/tickets/{ticket['id']}/resolve").status_code == 200
    db.expire_all()
    warranty = db.query(Warranty).filter_by(serial_number="CC-T-002").one()
    assert warranty.duration_months == 24 and warranty.end_date > date.today() + timedelta(days=700)


def test_panel_replacement_is_dispatched_without_a_serial_number(api, ids, db):
    order_id, _ = confirmed_order(api, ids, db)
    dispatch_and_deliver(api, order_id)
    panels = db.query(Warranty).filter_by(order_id=order_id, warranty_type="bulk").one()
    on_hand = db.query(InventoryItem).filter_by(product_id=panels.product_id).one().quantity_on_hand
    ticket = api["support"].post("/api/tickets", json={"customer_id": ids["customer"], "warranty_id": panels.id, **FAULT}).json()
    tech = db.query(Technician).first()
    api["support"].post(f"/api/tickets/{ticket['id']}/assign", json={"technician_id": tech.id})
    api["technician"].post(f"/api/repair-visits/{ticket['id']}/report", json={"needs_replacement": True})
    assert api["warehouse"].post(f"/api/dispatch/replacements/{ticket['id']}/send").status_code == 200
    db.expire_all()
    assert db.query(InventoryItem).filter_by(product_id=panels.product_id).one().quantity_on_hand == on_hand - 1
    resolved = api["support"].post(f"/api/tickets/{ticket['id']}/resolve")
    assert resolved.status_code == 200 and resolved.json()["replacement_serial"] is None


def test_repair_invoice_is_sent_to_the_customer_when_the_repair_is_done(api, ids, db):
    order_id, _ = confirmed_order(api, ids, db)
    dispatch_and_deliver(api, order_id)
    db.query(Warranty).filter_by(serial_number="CC-T-001").one().end_date = date.today() - timedelta(days=1)
    db.commit()
    ticket = api["support"].post("/api/tickets", json={"customer_id": ids["customer"], "equipment_serial": "CC-T-001", **FAULT}).json()
    assert db.get(Invoice, ticket["invoice_id"]).status == "Draft", "Support can still edit it before the repair is done"

    prepare_ticket(api, db, ticket)
    api["support"].post(f"/api/tickets/{ticket['id']}/resolve")
    db.expire_all()
    invoice = db.get(Invoice, ticket["invoice_id"])
    assert invoice.status == "Sent"
    assert db.query(Notification).filter(Notification.customer_id == ids["customer"], Notification.title.like("Invoice INV-SRV%")).count() == 1
    assert api["support"].put(f"/api/invoices/{invoice.id}/items", json=[{"description": "Extra cable and fittings", "quantity": 1, "unit_price": 500}]).status_code == 400, "No edits after the customer has seen it"


def test_approving_a_survey_drafts_the_quotation_for_sales_to_send(api, ids, db):
    from backend.app.models.models import Quotation
    survey_id = submitted_survey(api, ids, db)
    assert db.query(Quotation).count() == 0
    assert api["sales"].post(f"/api/surveys/{survey_id}/approve").status_code == 200

    db.expire_all()
    drafts = db.query(Quotation).filter_by(survey_id=survey_id).all()
    assert len(drafts) == 1 and drafts[0].status == "Draft", "Drafted, never sent automatically"
    assert drafts[0].package_id == ids["package"] and drafts[0].customer_id == ids["customer"]
    assert len(drafts[0].items) == 5, "The full parts list comes from the package template"
    assert drafts[0].tax == round(drafts[0].subtotal * settings.GST_PERCENT / 100, 2)
    titles = [n.title for n in db.query(Notification).filter_by(role="sales").all()]
    assert any(t.startswith("Draft quotation QTN-") for t in titles)
    assert db.query(Notification).filter_by(customer_id=ids["customer"]).filter(Notification.title.like("%uotation%")).count() == 0, "The customer hears nothing until Sales send it"

    # Sales review and send it
    assert api["sales"].post(f"/api/quotations/{drafts[0].id}/send").status_code == 200


def test_no_draft_when_no_single_package_matches_the_survey(api, ids, db):
    from backend.app.models.models import Quotation, SiteSurvey
    survey_id = submitted_survey(api, ids, db)
    db.get(SiteSurvey, survey_id).recommended_capacity = 4.0  # the test catalogue only has a 3 kW package
    db.commit()
    assert api["sales"].post(f"/api/surveys/{survey_id}/approve").status_code == 200
    db.expire_all()
    assert db.query(Quotation).count() == 0
    assert any("create the quotation" in n.title for n in db.query(Notification).filter_by(role="sales").all())


def test_qr_label_for_a_unit_carries_the_warranty_check_address(api, ids, db):
    from urllib.parse import parse_qs, urlparse
    from backend.app.core.qr import warranty_url
    png = api["warehouse"].get("/api/stock/qr.png", params={"serial": "INV-T-001"})
    assert png.status_code == 200 and png.headers["content-type"] == "image/png" and png.content.startswith(b"\x89PNG")
    assert api["warehouse"].get("/api/stock/qr.png", params={"serial": "NOPE-1"}).status_code == 404
    assert api["support"].get("/api/stock/qr.png", params={"serial": "INV-T-001"}).status_code == 403, "Labels are printed by the warehouse"

    # The address in the QR code names the serial, even one with characters that need escaping
    url = warranty_url("AB/12 3")
    assert urlparse(url).path == "/check" and parse_qs(urlparse(url).query)["serial"] == ["AB/12 3"]

    listed = api["warehouse"].get("/api/stock/serials").json()
    assert {u["serial_number"] for u in listed} == {"INV-T-001", "INV-T-002", "INV-T-003", "CC-T-001", "CC-T-002", "CC-T-003"}
    assert len(api["warehouse"].get("/api/stock/serials", params={"status": "Dispatched"}).json()) == 0


def test_public_warranty_check_needs_no_sign_in_and_hides_the_owner(api, ids, db):
    from fastapi.testclient import TestClient
    from backend.app.main import app
    public = TestClient(app)
    check = lambda serial: public.get("/api/public/warranty", params={"serial": serial})

    assert check("INV-T-001").json()["state"] == "not_started", "Still in the warehouse"
    assert check("NOPE-1").status_code == 404

    order_id, _ = confirmed_order(api, ids, db)
    dispatch_and_deliver(api, order_id)
    live = check("INV-T-001").json()
    assert live["state"] == "active" and live["days_left"] > 700 and live["product_name"] == "3kW Inverter"
    assert "Ravi" not in str(live) and "customer" not in str(live).lower(), "A public page never shows who owns the unit"

    db.query(Warranty).filter_by(serial_number="CC-T-001").one().end_date = date.today() - timedelta(days=1)
    db.commit()
    assert check("CC-T-001").json()["state"] == "expired"

    ticket = api["support"].post("/api/tickets", json={"customer_id": ids["customer"], "equipment_serial": "INV-T-001", **FAULT}).json()
    prepare_ticket(api, db, ticket, replacement="INV-T-002")
    api["support"].post(f"/api/tickets/{ticket['id']}/resolve")
    assert check("INV-T-001").json()["state"] == "replaced"
    assert check("INV-T-002").json()["state"] == "active"


def test_rejected_quotation_closes_the_ticket_with_no_charge(api, ids, db):
    order_id, _ = confirmed_order(api, ids, db)
    dispatch_and_deliver(api, order_id)
    db.query(Warranty).filter_by(serial_number="CC-T-001").one().end_date = date.today() - timedelta(days=1)
    db.commit()
    ticket = api["support"].post("/api/tickets", json={"customer_id": ids["customer"], "equipment_serial": "CC-T-001", **FAULT}).json()
    tid = ticket["id"]
    assert api["support"].post(f"/api/tickets/{tid}/quote", json={"approved": True}).status_code == 400, "Nothing to approve before the visit"

    tech = db.query(Technician).first()
    assert ticket["status"] == "Assigned" and ticket["technician_id"] == tech.id, "A technician is sent automatically"
    visit = api["technician"].post(f"/api/repair-visits/{tid}/report", json={"needs_replacement": True}).json()
    assert visit["status"] == "Quotation Sent" and visit["quote_status"] == "Pending" and visit["customer_charge"] > 0
    assert api["warehouse"].post(f"/api/dispatch/replacements/{tid}/send", json={"serial_number": "CC-T-002"}).status_code == 400, "Not approved yet"

    rejected = api["support"].post(f"/api/tickets/{tid}/quote", json={"approved": False}).json()
    assert rejected["status"] == "Closed" and rejected["quote_status"] == "Rejected" and rejected["customer_charge"] == 0
    assert rejected["invoice_id"] is None
    db.expire_all()
    assert db.query(Invoice).filter_by(ticket_id=tid).count() == 0
    assert db.query(EquipmentSerial).filter_by(serial_number="CC-T-002").one().status == "In Stock"


def test_repair_without_replacement_is_priced_without_the_part(api, ids, db):
    order_id, _ = confirmed_order(api, ids, db)
    dispatch_and_deliver(api, order_id)
    db.query(Warranty).filter_by(serial_number="CC-T-001").one().end_date = date.today() - timedelta(days=1)
    db.commit()
    ticket = api["support"].post("/api/tickets", json={"customer_id": ids["customer"], "equipment_serial": "CC-T-001", **FAULT}).json()
    tech = db.query(Technician).first()
    api["support"].post(f"/api/tickets/{ticket['id']}/assign", json={"technician_id": tech.id})
    visit = api["technician"].post(f"/api/repair-visits/{ticket['id']}/report", json={"needs_replacement": False}).json()
    labour = settings.SERVICE_LABOUR_CHARGE
    assert visit["customer_charge"] == round(labour * (1 + settings.GST_PERCENT / 100), 2), "Only the visit and labour"
    assert api["warehouse"].post(f"/api/dispatch/replacements/{ticket['id']}/send", json={"serial_number": "CC-T-002"}).status_code == 400


def test_technician_is_assigned_automatically_to_the_least_busy(api, ids, db):
    order_id, _ = confirmed_order(api, ids, db)
    dispatch_and_deliver(api, order_id)
    first = db.query(Technician).first()
    second = Technician(name="Sam Spanner", phone="9000000002", hourly_rate=300)
    db.add(second)
    db.commit()

    one = api["support"].post("/api/tickets", json={"customer_id": ids["customer"], "equipment_serial": "INV-T-001", **FAULT}).json()
    two = api["support"].post("/api/tickets", json={"customer_id": ids["customer"], "equipment_serial": "CC-T-001", **FAULT}).json()
    assert one["technician_id"] == first.id and two["technician_id"] == second.id, "The second ticket goes to the free technician"
    assert one["status"] == two["status"] == "Assigned"
    assert db.query(Notification).filter_by(technician_id=second.id).count() == 1


def test_only_the_assigned_technician_reports_and_support_is_told(api, ids, db):
    order_id, _ = confirmed_order(api, ids, db)
    dispatch_and_deliver(api, order_id)
    ticket = api["support"].post("/api/tickets", json={"customer_id": ids["customer"], "equipment_serial": "INV-T-001", **FAULT}).json()
    tid = ticket["id"]

    mine = api["technician"].get("/api/repair-visits").json()
    assert [v["id"] for v in mine] == [tid] and mine[0]["customer_address"]
    assert api["support"].get("/api/repair-visits").status_code == 403
    assert api["support"].post(f"/api/tickets/{tid}/inspect", json={"needs_replacement": True}).status_code in (404, 405), "Support cannot report for the technician"

    # A ticket belonging to some other technician is not visible or reportable
    other = Technician(name="Sam Spanner", phone="9000000002", hourly_rate=300)
    db.add(other)
    db.commit()
    from backend.app.models.models import ServiceTicket
    db.get(ServiceTicket, tid).technician_id = other.id
    db.commit()
    assert api["technician"].get("/api/repair-visits").json() == []
    assert api["technician"].post(f"/api/repair-visits/{tid}/report", json={"needs_replacement": True}).status_code == 404

    db.get(ServiceTicket, tid).technician_id = db.query(Technician).first().id
    db.commit()
    assert api["technician"].post(f"/api/repair-visits/{tid}/report", json={"needs_replacement": True, "notes": "Board burnt"}).status_code == 200
    assert any(n.title == f"Technician's report on TCK-{tid:04d}" and "replacement" in n.body for n in db.query(Notification).filter_by(role="support"))
