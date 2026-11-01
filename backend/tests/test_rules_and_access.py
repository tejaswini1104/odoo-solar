"""Hard gates, duplicate protection, notifications and who may do what."""
from backend.app.models.models import Lead, Notification


def lead_for(db, customer_id, status="New"):
    lead = Lead(
        name="Ravi Kumar", phone="9876500001", email="ravi@t.test", address="12 Lake Road", city="Hyderabad",
        enquiry_source="Call", required_capacity=3, monthly_electricity_bill=4000, roof_area=500,
        grid_type="On-Grid", lead_status=status, customer_id=customer_id,
    )
    db.add(lead)
    db.commit()
    return lead


def test_contacted_needs_roof_space_and_grid_answer(api, ids, db):
    lead = lead_for(db, ids["customer"])
    bare = api["sales"].post(f"/api/leads/{lead.id}/status", json={"status": "Contacted"})
    assert bare.status_code == 422
    ok = api["sales"].post(f"/api/leads/{lead.id}/status", json={"status": "Contacted", "shadow_free_area": 300, "grid_connection_ok": True, "call_notes": "Keen"})
    body = ok.json()
    assert ok.status_code == 200 and body["shadow_free_area"] == 300 and body["grid_connection_ok"] is True and body["contacted_at"]


def test_unsuitable_grid_stops_a_survey_booking(api, ids, db):
    lead = lead_for(db, ids["customer"])
    api["sales"].post(f"/api/leads/{lead.id}/status", json={"status": "Contacted", "shadow_free_area": 300, "grid_connection_ok": False})
    booked = api["sales"].post("/api/surveys/schedule", json={"customer_id": ids["customer"], "lead_id": lead.id, "scheduled_date": ids["tomorrow"]})
    assert booked.status_code == 400 and "grid" in booked.json()["detail"].lower()


def test_no_quotation_without_an_approved_survey(api, ids, db):
    lead = lead_for(db, ids["customer"])
    api["sales"].post(f"/api/leads/{lead.id}/status", json={"status": "Contacted", "shadow_free_area": 300, "grid_connection_ok": True})
    survey = api["sales"].post("/api/surveys/schedule", json={"customer_id": ids["customer"], "lead_id": lead.id, "scheduled_date": ids["tomorrow"]}).json()
    quote = api["sales"].post("/api/quotations", json={"customer_id": ids["customer"], "survey_id": survey["id"], "package_id": ids["package"]})
    assert quote.status_code == 400


def test_survey_booking_alerts_the_technician_and_assigns_automatically(api, ids, db):
    lead = lead_for(db, ids["customer"])
    api["sales"].post(f"/api/leads/{lead.id}/status", json={"status": "Contacted", "shadow_free_area": 300, "grid_connection_ok": True})
    survey = api["sales"].post("/api/surveys/schedule", json={"customer_id": ids["customer"], "lead_id": lead.id, "scheduled_date": ids["tomorrow"]}).json()
    assert survey["technician_name"] == "Tara Tech"
    alerts = api["technician"].get("/api/notifications").json()
    assert alerts["unread"] == 1 and "Survey visit booked" in alerts["items"][0]["title"]
    assert api["sales"].get("/api/notifications").json()["unread"] == 0, "Alerts reach only the people they are for"


def test_notifications_can_be_marked_read(api, ids, db):
    lead = lead_for(db, ids["customer"])
    api["sales"].post(f"/api/leads/{lead.id}/status", json={"status": "Contacted", "shadow_free_area": 300, "grid_connection_ok": True})
    api["sales"].post("/api/surveys/schedule", json={"customer_id": ids["customer"], "lead_id": lead.id, "scheduled_date": ids["tomorrow"]})
    note = api["technician"].get("/api/notifications").json()["items"][0]
    assert api["technician"].post(f"/api/notifications/{note['id']}/read").status_code == 204
    assert api["technician"].get("/api/notifications").json()["unread"] == 0
    assert api["sales"].post(f"/api/notifications/{note['id']}/read").status_code == 404, "Not their alert"


def test_duplicate_customers_are_refused(api, ids):
    body = {"name": "Ravi K", "phone": "9876500001", "email": "new@t.test", "address": "5 Park Street", "city": "Chennai"}
    assert api["sales"].post("/api/customers", json=body).status_code == 409
    body["phone"] = "9999999999"
    body["email"] = "RAVI@t.test"
    assert api["sales"].post("/api/customers", json=body).status_code == 409, "Email matches regardless of case"
    body["email"] = "fresh@t.test"
    assert api["sales"].post("/api/customers", json=body).status_code == 200


def test_converting_a_lead_reuses_the_existing_customer(api, ids, db):
    lead = lead_for(db, ids["customer"])
    lead.customer_id = None
    db.commit()
    converted = api["sales"].post(f"/api/leads/{lead.id}/convert")
    assert converted.status_code == 200 and converted.json()["id"] == ids["customer"]


def test_converting_does_not_skip_the_first_call(api, ids, db):
    lead = lead_for(db, ids["customer"])
    lead.customer_id = None
    db.commit()
    assert api["sales"].post(f"/api/leads/{lead.id}/convert").status_code == 200
    db.refresh(lead)
    assert lead.customer_id == ids["customer"] and lead.lead_status == "New", "Converting must not mark an uncalled lead as done"
    booked = api["sales"].post("/api/surveys/schedule", json={"customer_id": ids["customer"], "lead_id": lead.id, "scheduled_date": ids["tomorrow"]})
    assert booked.status_code == 400 and "Call" in booked.json()["detail"]

    # Once the call is recorded the lead can be converted and the survey booked
    api["sales"].post(f"/api/leads/{lead.id}/status", json={"status": "Contacted", "shadow_free_area": 300, "grid_connection_ok": True})
    lead.customer_id = None
    db.commit()
    api["sales"].post(f"/api/leads/{lead.id}/convert")
    db.refresh(lead)
    assert lead.lead_status == "Converted"
    assert api["sales"].post("/api/surveys/schedule", json={"customer_id": ids["customer"], "lead_id": lead.id, "scheduled_date": ids["tomorrow"]}).status_code == 201


def test_role_gates(api, ids):
    assert api["technician"].get("/api/reports/summary").status_code == 403
    assert api["sales"].get("/api/reports/summary").status_code == 403
    assert api["admin"].get("/api/reports/summary", params={"period": "today"}).status_code == 200
    assert api["admin"].get("/api/reports/pipeline").status_code == 200
    assert api["warehouse"].post("/api/leads", json={}).status_code == 403
    assert api["support"].post("/api/orders/1/confirm").status_code == 403


def test_staff_endpoints_need_a_session(db):
    from fastapi.testclient import TestClient
    from backend.app.main import app
    assert TestClient(app).get("/api/leads").status_code == 401


def test_director_period_filters(api):
    for period in ("today", "week", "month"):
        data = api["admin"].get("/api/reports/summary", params={"period": period}).json()
        assert {"activity", "money", "profit", "open_now"} <= set(data)
    assert api["admin"].get("/api/reports/summary", params={"period": "custom"}).status_code == 400
    assert api["admin"].get("/api/reports/summary.csv", params={"period": "month"}).headers["content-type"].startswith("text/csv")
