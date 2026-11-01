"""Every form must refuse nonsense on the server, not just in the browser."""
import pytest

CUSTOMER = {"name": "Meera Iyer", "phone": "9123456780", "email": "meera@t.test", "address": "5 Park Street", "city": "Chennai"}
LEAD = {**CUSTOMER, "enquiry_source": "Call", "required_capacity": 3, "monthly_electricity_bill": 3500, "roof_area": 450, "grid_type": "On-Grid"}
SURVEY = {"customer_id": None, "technician_name": "Tara Tech", "roof_area": 400, "roof_direction": "South", "roof_tilt": 20,
          "shading_level": "Low", "cable_distance": 15, "grid_suitability": "Suitable", "recommended_capacity": 3, "status": "Draft"}


def post_status(client, url, body):
    return client.post(url, json=body).status_code


@pytest.mark.parametrize("change", [
    {"email": "not-an-email"}, {"email": "a@b"}, {"name": "   "}, {"name": "A"}, {"city": " "}, {"address": "abc"},
    {"phone": "12345"},
])
def test_customer_form_rejects(api, change):
    assert post_status(api["sales"], "/api/customers", {**CUSTOMER, **change}) == 422


def test_customer_form_accepts_and_cleans(api):
    ok = api["sales"].post("/api/customers", json={**CUSTOMER, "name": "  Meera Iyer  ", "email": " MEERA@t.test "})
    assert ok.status_code == 200 and ok.json()["name"] == "Meera Iyer" and ok.json()["email"] == "meera@t.test"


@pytest.mark.parametrize("change", [
    {"required_capacity": 0}, {"required_capacity": 9}, {"required_capacity": -3}, {"monthly_electricity_bill": -1},
    {"monthly_electricity_bill": 10**9}, {"roof_area": 0}, {"roof_area": -50}, {"grid_type": "Nuclear"},
    {"enquiry_source": "Telepathy"}, {"lead_status": "Converted"}, {"email": "bad"},
])
def test_lead_form_rejects(api, change):
    assert post_status(api["sales"], "/api/leads", {**LEAD, **change}) == 422


def test_lead_form_accepts(api):
    assert post_status(api["sales"], "/api/leads", LEAD) == 200


@pytest.mark.parametrize("change", [
    {"roof_area": 0}, {"roof_area": -5}, {"roof_tilt": 120}, {"roof_tilt": -1}, {"cable_distance": -2}, {"cable_distance": 5000},
    {"roof_direction": "Up"}, {"shading_level": "Total"}, {"grid_suitability": "Maybe"}, {"recommended_capacity": 0},
    {"recommended_capacity": 50}, {"status": "Approved"}, {"technician_name": ""},
])
def test_manual_survey_rejects(api, ids, change):
    body = {**SURVEY, "customer_id": ids["customer"], **change}
    assert post_status(api["sales"], "/api/surveys", body) == 422


def test_manual_survey_cannot_be_born_approved(api, ids):
    body = {**SURVEY, "customer_id": ids["customer"], "status": "Approved"}
    assert post_status(api["technician"], "/api/surveys", body) == 422
    assert post_status(api["technician"], "/api/surveys", {**body, "status": "Submitted"}) == 200


@pytest.mark.parametrize("amount", [0, -100, 10**9])
def test_staff_payment_amount_is_bounded(api, ids, amount):
    body = {"quotation_id": None, "order_id": None, "customer_id": ids["customer"], "amount": amount}
    assert post_status(api["sales"], "/api/payments", body) == 422


def test_payment_type_is_checked(api, ids):
    assert post_status(api["sales"], "/api/payments", {"customer_id": ids["customer"], "amount": 10, "payment_type": "free"}) == 422


@pytest.mark.parametrize("item", [
    {"description": "Part", "quantity": 0, "unit_price": 10}, {"description": "Part", "quantity": -1, "unit_price": 10},
    {"description": "Part", "quantity": 1, "unit_price": -10}, {"description": " ", "quantity": 1, "unit_price": 10},
    {"description": "Part", "quantity": 5000, "unit_price": 10}, {"description": "Part", "quantity": 1, "unit_price": 10**9},
])
def test_invoice_lines_reject(api, item):
    assert api["sales"].put("/api/invoices/1/items", json=[item]).status_code == 422


def test_invoice_needs_at_least_one_line(api):
    assert api["sales"].put("/api/invoices/1/items", json=[]).status_code == 422


@pytest.mark.parametrize("change", [
    {"title": "ab"}, {"title": "   "}, {"description": "bad"}, {"priority": "Whenever"}, {"equipment_serial": "x"},
])
def test_ticket_form_rejects(api, ids, change):
    body = {"customer_id": ids["customer"], "equipment_serial": "INV-T-001", "title": "No power", "description": "Fault code E04", **change}
    assert post_status(api["support"], "/api/tickets", body) == 422


@pytest.mark.parametrize("password", ["short1", "allletters", "12345678", "a" * 200])
def test_weak_passwords_are_refused(api, password):
    staff = {"name": "New Staff", "email": "ns@example.com", "password": password, "role": "sales"}
    response = api["admin"].post("/api/admin/users", json=staff)
    assert response.status_code == 422 and response.json()["detail"][0]["loc"][-1] == "password"


def test_strong_password_is_accepted_for_staff(api):
    staff = {"name": "New Staff", "email": "ns2@example.com", "password": "Good1234", "role": "sales", "phone": ""}
    assert post_status(api["admin"], "/api/admin/users", staff) == 201


def test_change_password_rule(api):
    bad = api["sales"].post("/api/auth/change-password", json={"current_password": "Test@12345", "new_password": "onlyletters"})
    assert bad.status_code == 422


def test_registration_rules():
    from fastapi.testclient import TestClient
    from backend.app.main import app
    client = TestClient(app)
    base = {"name": "Asha Rao", "email": "asha2@example.com", "phone": "9876543210", "password": "Password1", "address": "12 Lake Road", "city": "Pune"}
    for change in ({"password": "nodigitshere"}, {"name": "  "}, {"city": " "}, {"address": "     "}, {"email": "nope"}):
        assert client.post("/api/auth/register", json={**base, **change}).status_code == 422, change


def test_dispatch_needs_serials_and_a_sane_list(api):
    assert post_status(api["warehouse"], "/api/dispatch/1/serials", {"serial_numbers": []}) == 422
    assert post_status(api["warehouse"], "/api/dispatch/1/serials", {"serial_numbers": ["SN-123"] * 60}) == 422


@pytest.mark.parametrize("change", [{"confirmed_system_size": 0}, {"confirmed_system_size": -3}, {"confirmed_system_size": 900}, {"notes": "x" * 3000}])
def test_installation_completion_rejects(api, change):
    assert post_status(api["technician"], "/api/installations/1/complete", {"confirmed_system_size": 3, **change}) == 422


def test_stock_purchase_rules(api, db):
    from backend.app.models.models import Product
    inverter = db.query(Product).filter_by(name="3kW Inverter").one()
    base = {"supplier": "Sun Supply", "purchased_on": "2020-01-01", "items": [{"product_id": inverter.id, "quantity": 1, "unit_cost": 100, "serial_numbers": ["GOOD-001"]}]}
    assert post_status(api["warehouse"], "/api/stock/purchases", {**base, "supplier": " "}) == 422
    bad_cost = {**base, "items": [{**base["items"][0], "unit_cost": -5}]}
    assert post_status(api["warehouse"], "/api/stock/purchases", bad_cost) == 422
    bad_serial = {**base, "items": [{**base["items"][0], "serial_numbers": ["bad serial!"]}]}
    assert post_status(api["warehouse"], "/api/stock/purchases", bad_serial) == 400
    assert post_status(api["warehouse"], "/api/stock/purchases", base) == 201


def test_a_payment_cannot_exceed_what_is_owed(api, ids, db):
    from backend.tests.test_lifecycle import approved_survey
    survey_id = approved_survey(api, ids, db)
    quote = api["sales"].post("/api/quotations", json={"customer_id": ids["customer"], "survey_id": survey_id, "package_id": ids["package"]}).json()
    api["sales"].post(f"/api/quotations/{quote['id']}/send")
    order = api["sales"].post(f"/api/quotations/{quote['id']}/confirm").json()
    pay = lambda amount: api["sales"].post("/api/payments", json={"order_id": order["id"], "customer_id": ids["customer"], "amount": amount})
    assert pay(order["total_amount"] + 1).status_code == 400
    assert pay(order["total_amount"]).status_code == 200
    assert pay(1).status_code == 400, "Already fully paid"


def test_only_a_draft_invoice_can_be_edited(api, ids, db):
    from backend.app.models.models import Invoice
    db.add(Invoice(invoice_number="INV-X-1", customer_id=ids["customer"], subtotal=100, tax=18, total=118, status="Sent"))
    db.commit()
    invoice_id = db.query(Invoice).filter_by(invoice_number="INV-X-1").one().id
    refused = api["sales"].put(f"/api/invoices/{invoice_id}/items", json=[{"description": "Changed", "quantity": 1, "unit_price": 1}])
    assert refused.status_code == 400 and "draft" in refused.json()["detail"].lower()
