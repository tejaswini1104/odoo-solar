"""Test setup. The whole app runs against a throwaway SQLite file, never against the real PostgreSQL database."""
import os
import sys
import tempfile
from datetime import date, timedelta

_TMP = tempfile.mkdtemp(prefix="solar_erp_tests_")
os.environ["DATABASE_URL"] = f"sqlite:///{os.path.join(_TMP, 'test.db')}"
os.environ["MEDIA_DIR"] = os.path.join(_TMP, "media")
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

from backend.app.core.database import Base, SessionLocal, engine  # noqa: E402
from backend.app.core.security import hash_password  # noqa: E402
from backend.app.main import app  # noqa: E402
from backend.app.models.models import (  # noqa: E402
    Customer, EquipmentSerial, InventoryItem, PackageComponent, Product, SolarPackage, Technician, User,
)

PASSWORD = "Test@12345"
STAFF = {
    "admin": "admin@t.test", "sales": "sales@t.test", "technician": "tech@t.test",
    "support": "support@t.test", "warehouse": "wh@t.test",
}


@pytest.fixture()
def db():
    """A fresh database with a catalogue, stock, one technician, one customer and one account per role."""
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    session = SessionLocal()

    def product(name, category, cost, price, serialized=False, unit="Nos"):
        p = Product(name=name, category=category, cost_price=cost, unit_price=price, is_serialized=serialized, unit=unit)
        session.add(p)
        session.flush()
        return p

    panels = product("Solar Panel 540W", "Solar Panels", 8000, 10000)
    inverter = product("3kW Inverter", "Inverter", 30000, 40000, serialized=True)
    controller = product("Charge Controller", "Charge Controller", 5000, 7000, serialized=True)
    stands = product("Mounting Stands", "Mounting Stands", 4000, 5000, unit="Set")
    service = product("Installation", "Installation Service", 0, 8000)

    package = SolarPackage(name="3 kW On-Grid", capacity_kw=3.0, system_type="On-Grid", base_price=0)
    session.add(package)
    session.flush()
    for prod, qty in ((panels, 6), (inverter, 1), (controller, 1), (stands, 1), (service, 1)):
        session.add(PackageComponent(package_id=package.id, product_id=prod.id, quantity=qty))

    session.add(InventoryItem(product_id=panels.id, quantity_on_hand=60))
    session.add(InventoryItem(product_id=stands.id, quantity_on_hand=10))
    session.add(InventoryItem(product_id=inverter.id, quantity_on_hand=3))
    session.add(InventoryItem(product_id=controller.id, quantity_on_hand=3))
    for i in range(1, 4):
        session.add(EquipmentSerial(product_id=inverter.id, serial_number=f"INV-T-{i:03d}", status="In Stock"))
        session.add(EquipmentSerial(product_id=controller.id, serial_number=f"CC-T-{i:03d}", status="In Stock"))

    tech = Technician(name="Tara Tech", phone="9000000001", hourly_rate=300)
    session.add(tech)
    session.flush()
    for role, email in STAFF.items():
        session.add(User(
            name=role.title(), email=email, password_hash=hash_password(PASSWORD), role=role,
            technician_id=tech.id if role == "technician" else None,
        ))
    customer = Customer(name="Ravi Kumar", phone="9876500001", email="ravi@t.test", address="12 Lake Road", city="Hyderabad")
    session.add(customer)
    session.commit()
    yield session
    session.close()


def _client_for(email: str) -> TestClient:
    client = TestClient(app)
    response = client.post("/api/auth/login", json={"email": email, "password": PASSWORD})
    assert response.status_code == 200, response.text
    return client


@pytest.fixture()
def api(db):
    """A signed-in API client for every staff role: api['sales'].get(...)."""
    return {role: _client_for(email) for role, email in STAFF.items()}


@pytest.fixture()
def ids(db):
    package = db.query(SolarPackage).first()
    return {
        "customer": db.query(Customer).first().id,
        "package": package.id,
        "tomorrow": (date.today() + timedelta(days=1)).isoformat(),
    }
