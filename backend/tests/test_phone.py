"""Phone numbers must be real 10 digit mobile numbers wherever an account, customer or lead is created."""
import pytest

from backend.app.core.validators import clean_phone


@pytest.mark.parametrize("typed,saved", [
    ("9876543210", "9876543210"),
    ("98765 43210", "9876543210"),
    ("+91 98765-43210", "9876543210"),
    ("919876543210", "9876543210"),
    ("09876543210", "9876543210"),
])
def test_valid_numbers_are_cleaned(typed, saved):
    assert clean_phone(typed) == saved


@pytest.mark.parametrize("typed", ["12345", "987654321", "98765432101", "1234567890", "abcdefghij", "", "+91 12345"])
def test_short_or_invalid_numbers_are_refused(typed):
    with pytest.raises(ValueError):
        clean_phone(typed)


def test_registration_rejects_a_short_number(db):
    from fastapi.testclient import TestClient
    from backend.app.main import app
    client = TestClient(app)
    body = {"name": "Asha Rao", "email": "asha@example.com", "phone": "98765", "password": "Password@123", "address": "12 Lake Road", "city": "Hyderabad"}
    bad = client.post("/api/auth/register", json=body)
    assert bad.status_code == 422 and bad.json()["detail"][0]["loc"][-1] == "phone"
    body["phone"] = "+91 98765 43211"
    ok = client.post("/api/auth/register", json=body)
    assert ok.status_code == 201, ok.text


def test_staff_forms_reject_a_short_number(api, ids):
    def rejected_for_phone(client, url, body):
        response = client.post(url, json=body)
        return response.status_code == 422 and response.json()["detail"][0]["loc"][-1] == "phone"

    customer = {"name": "New Person", "phone": "98765", "email": "np@t.test", "address": "5 Park Street", "city": "Chennai"}
    assert rejected_for_phone(api["sales"], "/api/customers", customer)
    lead = {**customer, "phone": "123", "required_capacity": 3, "monthly_electricity_bill": 3000, "roof_area": 400}
    assert rejected_for_phone(api["sales"], "/api/leads", lead)
    staff = {"name": "New Staff", "email": "ns@example.com", "phone": "555", "password": "Password@123", "role": "sales"}
    assert rejected_for_phone(api["admin"], "/api/admin/users", staff)
