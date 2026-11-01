"""Add a demo workforce and 100 customers at every stage of the business to an existing database.

    python backend/seed_demo.py

Nothing is deleted. Run `python backend/seed.py` first on an empty database (it creates the catalogue, stock and the five
staff logins). This script then adds:

  * 20 technicians who can sign in: tech1@gmail.com ... tech20@gmail.com
  * 100 customers, each with an enquiry, spread over every stage from "new enquiry" to "installed and under warranty"
  * supplier stock purchases big enough for those orders, with a serial number for every inverter, battery and controller
  * after-sales tickets, repair invoices, subsidy files and technician payouts

Every record is created by calling the real API as the person who would do it (the customer, Sales, a technician, the
warehouse, Support, the administrator), so all the business rules apply exactly as they do in the app. The dates are
then moved into the past so the reports have history. At the end an audit re-checks the rules against the data.
"""
import base64
import io
import math
import os
import random
import struct
import sys
import zlib
from datetime import date, datetime, time, timedelta

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, ROOT)

from dateutil.relativedelta import relativedelta  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

from backend.app.core.config import settings  # noqa: E402
from backend.app.core.database import SessionLocal  # noqa: E402
from backend.app.main import app  # noqa: E402
from backend.app.models.models import (  # noqa: E402
    Customer, EquipmentSerial, InstallationPhoto, Installation, InventoryItem, Invoice, Lead, Notification, Payment,
    Product, Quotation, SalesOrder, ServiceTicket, SiteSurvey, SolarPackage, StockPurchase, SubsidyApplication,
    SubsidyEvent, Technician, TechnicianPayout, User, Warranty,
)

PASSWORD = "SunPower@123"
RNG = random.Random(20261101)
NOW = datetime.utcnow()
IST = timedelta(minutes=settings.BUSINESS_UTC_OFFSET_MINUTES)
TODAY = (NOW + IST).date()


# ------------------------------------------------------------------ helpers
def stamp(days_ago: int, hour: float = None) -> datetime:
    """A moment `days_ago` days back on the company clock, stored the way the database stores it (UTC)."""
    hour = RNG.uniform(9.5, 18.0) if hour is None else hour
    local = datetime.combine(TODAY - timedelta(days=max(days_ago, 0)), time(0)) + timedelta(hours=hour)
    return min(local - IST, NOW - timedelta(minutes=2))


def local_date(moment: datetime) -> date:
    return (moment + IST).date()


def req(client, method, url, ok=(200, 201, 204), **kwargs):
    response = client.request(method.upper(), url, **kwargs)
    if response.status_code not in ok:
        raise RuntimeError(f"{method.upper()} {url} -> {response.status_code}: {response.text[:400]}")
    return response


def login(email: str) -> TestClient:
    client = TestClient(app)
    req(client, "post", "/api/auth/login", json={"email": email, "password": PASSWORD})
    return client


# ------------------------------------------------------------------ pictures (a finished roof, a signature)
def _png(width, height, pixels) -> bytes:
    rows = b"".join(b"\x00" + bytes(pixels[y * width * 3:(y + 1) * width * 3]) for y in range(height))

    def chunk(kind, data):
        body = kind + data
        return struct.pack(">I", len(data)) + body + struct.pack(">I", zlib.crc32(body) & 0xFFFFFFFF)

    return (b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", struct.pack(">IIBBBBB", width, height, 8, 2, 0, 0, 0))
            + chunk(b"IDAT", zlib.compress(rows, 6)) + chunk(b"IEND", b""))


def roof_photo(variant: int) -> bytes:
    w, h = 320, 180
    px = bytearray(w * h * 3)
    rng = random.Random(variant)
    for y in range(h):
        for x in range(w):
            i = (y * w + x) * 3
            if y < 70:  # sky
                px[i:i + 3] = bytes((120 + y // 2, 170 + y // 3, 235))
            else:  # roof
                shade = 150 + (y - 70) // 4 + rng.randint(-4, 4)
                px[i:i + 3] = bytes((shade, shade - 6, shade - 14))
    cols, rows_n = 3 + variant % 3, 2 + variant % 2
    pw, ph = 62, 34
    left = (w - cols * (pw + 6)) // 2
    for r in range(rows_n):
        for c in range(cols):
            x0, y0 = left + c * (pw + 6), 84 + r * (ph + 6)
            for y in range(y0, y0 + ph):
                for x in range(x0, x0 + pw):
                    i = (y * w + x) * 3
                    line = (x - x0) % 15 == 0 or (y - y0) % 11 == 0
                    px[i:i + 3] = bytes((190, 205, 225)) if line else bytes((18, 38, 92 + (x - x0) // 3))
    return _png(w, h, px)


def signature_png(variant: int) -> bytes:
    w, h = 300, 100
    px = bytearray(b"\xff" * (w * h * 3))
    rng = random.Random(variant)
    y_mid, amp, freq, phase = 55, rng.randint(14, 26), rng.uniform(0.05, 0.11), rng.uniform(0, 6)
    for x in range(20, w - 20):
        y = int(y_mid + amp * math.sin(x * freq + phase) * math.cos(x * 0.013))
        for dy in (-1, 0, 1):
            for dx in (0, 1):
                if 0 <= y + dy < h:
                    i = ((y + dy) * w + x + dx) * 3
                    px[i:i + 3] = b"\x14\x1e\x4b"
    return _png(w, h, px)


PHOTOS = [roof_photo(v) for v in range(6)]
SIGNATURES = ["data:image/png;base64," + base64.b64encode(signature_png(v)).decode() for v in range(8)]
CAPTIONS = ["Panels mounted on the stands", "Inverter and wiring box", "Earthing and lightning arrester", "Finished roof"]


# ------------------------------------------------------------------ people
FIRST = ["Aarav", "Ananya", "Vivaan", "Diya", "Aditya", "Isha", "Arjun", "Kavya", "Rohan", "Meera", "Karthik", "Lakshmi",
         "Sai", "Priya", "Harsha", "Sneha", "Nikhil", "Pooja", "Varun", "Divya", "Suresh", "Anjali", "Mahesh", "Swathi",
         "Ravi", "Deepa", "Kiran", "Bhavana", "Naveen", "Shruti", "Prasad", "Madhavi", "Venkat", "Rekha", "Srinivas",
         "Tejaswi", "Mohan", "Jyothi", "Ajay", "Padma", "Vikas", "Sowmya", "Raghu", "Anitha", "Gopal", "Sunitha",
         "Chaitanya", "Harini", "Dinesh", "Keerthi"]
LAST = ["Reddy", "Sharma", "Naidu", "Rao", "Iyer", "Patel", "Kumar", "Nair", "Gupta", "Joshi", "Varma", "Menon", "Singh",
        "Yadav", "Chowdary", "Goud", "Pillai", "Mehta", "Bhat", "Kulkarni", "Shetty", "Agarwal", "Das", "Mishra",
        "Prasad", "Murthy", "Raju", "Kapoor", "Desai", "Hegde"]
CITIES = {
    "Hyderabad": ["Gachibowli", "Madhapur", "Kukatpally", "Banjara Hills", "Miyapur", "Uppal", "Begumpet"],
    "Bengaluru": ["Whitefield", "Indiranagar", "Jayanagar", "HSR Layout", "Yelahanka", "Marathahalli"],
    "Chennai": ["Adyar", "Velachery", "Anna Nagar", "Tambaram", "Porur"],
    "Pune": ["Kothrud", "Baner", "Hinjewadi", "Wakad", "Aundh"],
    "Visakhapatnam": ["MVP Colony", "Gajuwaka", "Madhurawada", "Seethammadhara"],
    "Vijayawada": ["Benz Circle", "Gunadala", "Patamata"],
    "Warangal": ["Hanamkonda", "Kazipet", "Subedari"],
}
STREETS = ["Lake View Road", "Temple Street", "Gandhi Road", "Residency Lane", "Park Avenue", "Main Road", "Rose Garden Street"]
TECH_NAMES = [
    "Ramesh Naidu", "Satish Babu", "Mohan Krishna", "Praveen Kumar", "Anil Chowdary", "Rakesh Goud", "Vamsi Krishna",
    "Prakash Rao", "Bharath Reddy", "Kishore Varma", "Ganesh Pillai", "Santosh Yadav", "Lokesh Naik", "Yogesh Patil",
    "Rahul Dev", "Imran Sheikh", "Joseph Thomas", "Sreenivas Raju", "Tarun Mehta", "Nagaraj Hegde",
]


def make_people(count: int, used_phones: set, used_emails: set):
    pairs = [(f, l) for f in FIRST for l in LAST]
    RNG.shuffle(pairs)
    people = []
    for first, last in pairs:
        email = f"{first}.{last}@example.com".lower()
        if email in used_emails:
            continue
        while True:
            phone = f"{RNG.choice('9876')}{RNG.randint(100000000, 999999999)}"
            if phone not in used_phones:
                break
        used_phones.add(phone)
        used_emails.add(email)
        city = RNG.choice(list(CITIES))
        address = f"{RNG.randint(1, 99)}-{RNG.randint(1, 60)}/{RNG.randint(1, 20)}, {RNG.choice(STREETS)}, {RNG.choice(CITIES[city])}"
        people.append({"name": f"{first} {last}", "email": email, "phone": phone, "address": address, "city": city})
        if len(people) == count:
            return people
    raise RuntimeError("Not enough unique names")


# ------------------------------------------------------------------ the plan: how many customers are at each stage
STAGES = [
    ("lead_new", 8), ("lead_contacted", 6), ("lead_lost", 4), ("survey_scheduled", 7), ("survey_submitted", 5),
    ("survey_rejected", 3), ("quote_draft", 5), ("quote_sent", 6), ("order_pending_nopay", 5),
    ("order_pending_reported", 4), ("order_pending_partial", 3), ("order_cancelled_pending", 1),
    ("order_cancelled_confirmed", 2), ("confirmed", 6), ("dispatched", 5), ("delivered", 6), ("completed", 20),
    ("completed_old", 4),
]
assert sum(n for _, n in STAGES) == 100

# Day offsets from the day of the enquiry for each event, so each journey has a believable timeline
OFF = {"lead": 0, "call": 1, "lost": 3, "book": 2, "visit": 5, "decide": 6, "quote_sent": 7, "accept": 9, "pay1": 10,
       "verify1": 11, "confirm": 12, "cancel": 14, "dispatch": 15, "deliver": 16, "finish": 18, "pay2": 22}
_QUOTE = ["lead", "call", "book", "visit", "decide"]
USED = {
    "lead_new": ["lead"], "lead_contacted": ["lead", "call"], "lead_lost": ["lead", "call", "lost"],
    "survey_scheduled": ["lead", "call", "book"], "survey_submitted": ["lead", "call", "book", "visit"],
    "survey_rejected": _QUOTE, "quote_draft": _QUOTE, "quote_sent": _QUOTE + ["quote_sent"],
    "order_pending_nopay": _QUOTE + ["quote_sent", "accept"],
    "order_pending_reported": _QUOTE + ["quote_sent", "accept", "pay1"],
    "order_pending_partial": _QUOTE + ["quote_sent", "accept", "pay1", "verify1"],
    "order_cancelled_pending": _QUOTE + ["quote_sent", "accept", "pay1", "verify1", "cancel"],
    "order_cancelled_confirmed": _QUOTE + ["quote_sent", "accept", "pay1", "verify1", "confirm", "cancel"],
    "confirmed": _QUOTE + ["quote_sent", "accept", "pay1", "verify1", "confirm"],
    "dispatched": _QUOTE + ["quote_sent", "accept", "pay1", "verify1", "confirm", "dispatch"],
    "delivered": _QUOTE + ["quote_sent", "accept", "pay1", "verify1", "confirm", "dispatch", "deliver"],
    "completed": _QUOTE + ["quote_sent", "accept", "pay1", "verify1", "confirm", "dispatch", "deliver", "finish"],
}
USED["completed_old"] = USED["completed"]
EXTRA_DAYS = {  # how long ago the latest event of the journey happened
    "lead_new": (0, 10), "lead_contacted": (0, 12), "lead_lost": (5, 60), "survey_scheduled": (0, 2),
    "survey_submitted": (0, 8), "survey_rejected": (3, 60), "quote_draft": (0, 10), "quote_sent": (0, 20),
    "order_pending_nopay": (0, 15), "order_pending_reported": (0, 4), "order_pending_partial": (0, 15),
    "order_cancelled_pending": (5, 40), "order_cancelled_confirmed": (5, 50), "confirmed": (0, 10),
    "dispatched": (0, 6), "delivered": (0, 8), "completed": (0, 95),
}


class Journey:
    pass


def plan_journeys(packages):
    people = make_people(100, *existing_contacts())
    stages = [s for s, n in STAGES for _ in range(n)]
    RNG.shuffle(stages)
    ongrid = [p for p in packages if p["type"] == "On-Grid"]
    offgrid = [p for p in packages if p["type"] == "Off-Grid"]
    journeys = []
    for idx, (person, stage) in enumerate(zip(people, stages), start=1):
        j = Journey()
        j.idx, j.stage, j.person = idx, stage, person
        j.name, j.email, j.phone = person["name"], person["email"], person["phone"]
        pool = offgrid if RNG.random() < 0.2 else ongrid
        j.pkg = RNG.choices(pool, weights=[{1: 10, 2: 25, 3: 30, 4: 20, 5: 15}[p["kw"]] if p["type"] == "On-Grid" else 1 for p in pool])[0]
        j.kw, j.type = j.pkg["kw"], j.pkg["type"]
        j.roof = int(j.kw * 100 + RNG.randint(150, 450))
        j.bill = int(round((j.kw * 1400 + RNG.randint(-300, 600)) / 100) * 100)
        j.subsidy = j.type == "On-Grid" and RNG.random() < 0.55  # the rooftop subsidy is for grid-connected systems
        j.portal = True
        j.source = "Web"
        j.ids = {"payments": []}
        j.client = None
        journeys.append(j)

    # About one in seven enquiries came by phone, WhatsApp or walk-in and is handled entirely by staff
    candidates = [j for j in journeys if j.stage not in ("order_pending_reported", "completed_old")]
    for j in RNG.sample(candidates, 14):
        j.portal = False
        j.source = RNG.choice(["Call", "WhatsApp", "Manual"])

    # Variation inside a stage
    lost = [j for j in journeys if j.stage == "lead_lost"]
    for j, mode in zip(lost, ["nocall", "grid", "wait", "grid"]):
        j.lost_mode = mode
    for j in journeys:
        j.full_payment_first = RNG.random() < 0.25
        if j.stage == "completed":
            j.final = RNG.choice(["paid", "paid", "paid", "partial", "open"])  # some customers still owe a balance
        elif j.stage == "completed_old":
            j.final = "paid"
        j.hours = RNG.choice([3, 4, 5, 5, 6, 6, 7, 8, 9])
    long_jobs = RNG.sample([j for j in journeys if j.stage == "completed" and j.kw <= 2], min(2, len([j for j in journeys if j.stage == "completed" and j.kw <= 2])))
    for j in long_jobs:
        j.hours = RNG.choice([44, 52])  # a difficult roof: several days on site, so this job barely pays
    delivered = [j for j in journeys if j.stage == "delivered"]
    for j in delivered[:3]:
        j.partial_photos = True

    for j in journeys:
        used = USED.get(j.stage)
        need = max(OFF[e] for e in used)
        if j.stage in ("completed",) and j.final in ("paid", "partial"):
            need = max(need, OFF["pay2"])
        if j.stage == "completed_old":
            j.A = RNG.randint(776, 896)  # delivered 2+ years ago, so the 2 year warranties have ended
            continue
        lo, hi = EXTRA_DAYS[j.stage]
        j.A = need + RNG.randint(lo, hi)
    return journeys


def existing_contacts():
    with SessionLocal() as db:
        phones = {p for (p,) in db.query(Customer.phone).all()} | {p for (p,) in db.query(Lead.phone).all()}
        emails = {e.lower() for (e,) in db.query(Customer.email).all()} | {e.lower() for (e,) in db.query(User.email).all()}
    return phones, emails


# ------------------------------------------------------------------ the journey itself
SERIAL_COUNTERS = {}


def timeline(j):
    used = sorted(set(USED[j.stage]) | ({"pay2"} if getattr(j, "final", None) in ("paid", "partial") else set()), key=lambda e: OFF[e])
    times, previous = {}, None
    for event in used:
        moment = stamp(j.A - OFF[event])
        if previous and moment < previous:
            moment = min(previous + timedelta(minutes=25), NOW - timedelta(minutes=1))
        times[event] = previous = moment
    return times


def run(j, ctx):
    S, W, SUP = ctx["sales"], ctx["warehouse"], ctx["support"]
    ev = j.events = timeline(j)
    stage = j.stage

    # ---- the enquiry
    if j.portal:
        j.client = TestClient(app)
        user = req(j.client, "post", "/api/auth/register", json={
            "name": j.name, "email": j.email, "phone": j.phone, "password": PASSWORD,
            "address": j.person["address"], "city": j.person["city"],
        }).json()
        j.ids["customer"] = user["customer_id"]
        lead = req(j.client, "post", "/api/portal/enquiries", json={
            "required_capacity": j.kw, "grid_type": j.type, "monthly_electricity_bill": j.bill,
            "roof_area": j.roof, "subsidy_requirement": j.subsidy,
        }).json()
    else:
        lead = req(S, "post", "/api/leads", json={
            "name": j.name, "phone": j.phone, "email": j.email, "address": j.person["address"], "city": j.person["city"],
            "enquiry_source": j.source, "required_capacity": j.kw, "monthly_electricity_bill": j.bill,
            "roof_area": j.roof, "grid_type": j.type, "subsidy_requirement": j.subsidy,
        }).json()
    j.ids["lead"] = lead["id"]
    yield
    if stage == "lead_new":
        return

    # ---- the first call
    if stage == "lead_lost" and j.lost_mode == "nocall":
        req(S, "post", f"/api/leads/{j.ids['lead']}/status", json={"status": "Lost", "call_notes": "No answer after three attempts."})
        return
    grid_ok = not (stage == "lead_lost" and j.lost_mode == "grid")
    req(S, "post", f"/api/leads/{j.ids['lead']}/status", json={
        "status": "Contacted", "shadow_free_area": round(j.roof * RNG.uniform(0.7, 0.92)), "grid_connection_ok": grid_ok,
        "call_notes": "Roof is open and unshaded most of the day. Customer is keen." if grid_ok else "Single-phase supply, feeder cannot take a new connection.",
    })
    yield
    if stage == "lead_contacted":
        return
    if stage == "lead_lost":
        note = "Grid connection unsuitable, so we cannot proceed." if not grid_ok else "Customer decided to wait until next year."
        req(S, "post", f"/api/leads/{j.ids['lead']}/status", json={"status": "Lost", "call_notes": note})
        return

    if not j.portal:  # a phone or WhatsApp enquirer becomes a customer once they are keen
        j.ids["customer"] = req(S, "post", f"/api/leads/{j.ids['lead']}/convert").json()["id"]
    yield

    # ---- the site survey
    visit_day = TODAY + timedelta(days=RNG.randint(1, 3))
    survey = req(S, "post", "/api/surveys/schedule", json={
        "customer_id": j.ids["customer"], "lead_id": j.ids["lead"], "scheduled_date": visit_day.isoformat(),
        "notes": "Please call 30 minutes before arriving.",
    }).json()
    j.ids["survey"], j.tech_id = survey["id"], survey["technician_id"]
    yield
    if stage == "survey_scheduled":
        return

    tech = ctx["techs"][j.tech_id]
    rejected = stage == "survey_rejected"
    if rejected:
        findings = {
            "roof_area": round(j.roof * 0.35), "roof_direction": "North", "roof_tilt": RNG.randint(8, 18),
            "shading_level": "High", "cable_distance": RNG.randint(20, 45),
            "grid_suitability": RNG.choice(["Unsuitable", "Needs Upgrade"]), "recommended_capacity": 1,
            "recommended_system_type": j.type, "survey_notes": "North-facing roof, heavily shaded by the neighbouring building.",
        }
    else:
        findings = {
            "roof_area": round(j.roof * 0.9), "roof_direction": RNG.choices(
                ["South", "South-East", "South-West", "East", "West"], weights=[50, 15, 15, 10, 10])[0],
            "roof_tilt": RNG.randint(12, 28), "shading_level": RNG.choice(["None", "Low", "Low", "Medium"]),
            "cable_distance": RNG.randint(6, 35), "grid_suitability": "Suitable",
            "recommended_capacity": j.kw, "recommended_system_type": j.type,
            "survey_notes": "Concrete roof in good condition. Parapet wall on three sides.",
        }
    req(tech, "put", f"/api/surveys/{j.ids['survey']}/complete", json=findings)
    yield
    if stage == "survey_submitted":
        return
    if rejected:
        req(S, "post", f"/api/surveys/{j.ids['survey']}/reject")
        return

    # ---- approval drafts the quotation automatically; Sales review and send it
    req(S, "post", f"/api/surveys/{j.ids['survey']}/approve")
    with SessionLocal() as db:
        quote = db.query(Quotation).filter(Quotation.survey_id == j.ids["survey"]).one()
        j.ids["quote"] = quote.id
    yield
    if stage == "quote_draft":
        return
    req(S, "post", f"/api/quotations/{j.ids['quote']}/send")
    yield
    if stage == "quote_sent":
        return

    # ---- the customer accepts
    if j.portal:
        req(j.client, "post", f"/api/portal/quotations/{j.ids['quote']}/accept")
    else:
        req(S, "post", f"/api/quotations/{j.ids['quote']}/confirm")
    with SessionLocal() as db:
        order = db.query(SalesOrder).filter(SalesOrder.quotation_id == j.ids["quote"]).one()
        j.ids["order"], j.total = order.id, order.total_amount
    yield
    if stage == "order_pending_nopay":
        return

    # ---- payments: customers report a bank transfer and Sales verify it; phone customers pay Sales directly
    counter = {"n": 0}

    def pay(amount, tag, verify=True):
        counter["n"] += 1
        amount = round(amount, 2)
        if j.portal:
            reference = f"UTR{j.idx:03d}{counter['n']}{RNG.randint(100000, 999999)}"
            made = req(j.client, "post", "/api/portal/payments", json={
                "quotation_id": j.ids["quote"], "amount": amount, "reference_number": reference}).json()
            if verify:
                req(S, "post", f"/api/payments/{made['id']}/verify")
            j.ids["payments"].append({"id": made["id"], "tag": tag, "verified_later": verify})
        else:
            ptype = "full" if tag == "pay1" and amount + 0.01 >= j.total else ("balance" if tag == "pay2" else "advance")
            made = req(S, "post", "/api/payments", json={
                "order_id": j.ids["order"], "customer_id": j.ids["customer"], "amount": amount, "payment_type": ptype,
                "reference_notes": RNG.choice(["Cash received at the office", "UPI to the company account", "Cheque deposited"]),
            }).json()
            j.ids["payments"].append({"id": made["id"], "tag": tag, "verified_later": False})

    advance_pct = ctx["advance_pct"]
    if stage == "order_pending_reported":
        pay(j.total * RNG.uniform(advance_pct / 100 + 0.02, 0.5), "pay1", verify=False)
        return
    if stage == "order_pending_partial":
        pay(j.total * RNG.uniform(0.08, advance_pct / 100 - 0.05), "pay1")
        return
    if stage == "order_cancelled_pending":
        pay(j.total * 0.2, "pay1")
        req(S, "post", f"/api/orders/{j.ids['order']}/cancel", json={"reason": "Customer chose another installer"})
        return
    first = round(j.total if j.full_payment_first else j.total * RNG.uniform(advance_pct / 100 + 0.01, 0.6), 2)
    pay(first, "pay1")
    yield

    req(S, "post", f"/api/orders/{j.ids['order']}/confirm")
    with SessionLocal() as db:
        inst = db.query(Installation).filter(Installation.sales_order_id == j.ids["order"]).one()
        j.ids["inst"], j.inst_tech = inst.id, inst.technician_id
        subsidy = db.query(SubsidyApplication).filter(SubsidyApplication.order_id == j.ids["order"]).first()
        j.ids["subsidy"] = subsidy.id if subsidy else None
    yield
    if stage == "order_cancelled_confirmed":
        req(S, "post", f"/api/orders/{j.ids['order']}/cancel", json={"reason": "Customer's housing society refused permission"})
        j.ids["inst"] = None
        return
    if stage == "confirmed":
        if j.ids["subsidy"] and RNG.random() < 0.5:
            req(S, "put", f"/api/subsidies/{j.ids['subsidy']}", json={"status": "Documents collected", "note": "Aadhaar, electricity bill and roof ownership proof received."})
            j.subsidy_target = "Documents collected"
        return

    # ---- dispatch: the warehouse scans a serial number for every inverter, battery and controller
    with SessionLocal() as db:
        order = db.get(SalesOrder, j.ids["order"])
        serials = []
        for comp in order.package.components:
            if comp.product.is_serialized:
                rows = (db.query(EquipmentSerial).filter(EquipmentSerial.product_id == comp.product_id, EquipmentSerial.status == "In Stock")
                        .order_by(EquipmentSerial.id).limit(comp.quantity).all())
                serials += [r.serial_number for r in rows]
    j.serials = serials
    req(W, "post", f"/api/dispatch/{j.ids['order']}/serials", json={"serial_numbers": serials})
    yield
    if stage == "dispatched":
        return
    req(W, "post", f"/api/dispatch/{j.ids['order']}/delivered")
    yield
    install_client = ctx["techs"][j.inst_tech]
    if stage == "delivered":
        if getattr(j, "partial_photos", False):
            for k in range(2):
                req(install_client, "post", f"/api/installations/{j.ids['inst']}/photos",
                    files={"file": ("roof.png", PHOTOS[(j.idx + k) % len(PHOTOS)], "image/png")}, data={"caption": CAPTIONS[k]})
        return

    # ---- on the roof: photos, the homeowner's signature, then the job is closed
    for k in range(RNG.randint(3, 4)):
        req(install_client, "post", f"/api/installations/{j.ids['inst']}/photos",
            files={"file": ("roof.png", PHOTOS[(j.idx + k) % len(PHOTOS)], "image/png")}, data={"caption": CAPTIONS[k]})
    req(install_client, "post", f"/api/installations/{j.ids['inst']}/signature",
        json={"signed_by": j.name, "signature_data_url": SIGNATURES[j.idx % len(SIGNATURES)]})
    finish = NOW - timedelta(minutes=5)
    req(install_client, "post", f"/api/installations/{j.ids['inst']}/complete", json={
        "confirmed_system_size": j.kw, "serial_numbers": serials,
        "start_time": (finish - timedelta(hours=j.hours)).isoformat(), "finish_time": finish.isoformat(),
        "notes": "System tested and generating. Customer shown the monitoring app.",
    })
    yield

    # ---- the balance
    owed = round(j.total - first, 2)
    if owed > 0.005 and j.final == "paid":
        pay(owed, "pay2")
    elif owed > 0.005 and j.final == "partial":
        pay(owed * RNG.uniform(0.3, 0.7), "pay2")
    elif owed <= 0.005:
        j.final = "paid"
    yield

    # ---- the government subsidy file moves on according to how long ago the system went in
    if j.ids["subsidy"]:
        days_since = j.A - OFF["finish"]
        expected = min(78000, 30000 * min(j.kw, 2) + 18000 * max(min(j.kw, 3) - 2, 0))
        steps = [("Documents collected", {})]
        target = "Documents collected"
        if days_since >= 4:
            steps.append(("Applied", {"reference_number": f"PMSG-{RNG.randint(10**9, 10**10 - 1)}"}))
            target = "Applied"
        if days_since >= 35 and RNG.random() < 0.8:
            steps.append(("Approved", {"expected_amount": float(expected)}))
            target = "Approved"
        if days_since >= 70 and target == "Approved" and RNG.random() < 0.65:
            steps.append(("Disbursed", {"received_amount": float(expected)}))
            target = "Disbursed"
        for status, extra in steps:
            req(S, "put", f"/api/subsidies/{j.ids['subsidy']}", json={"status": status, **extra, "note": f"{status}."})
        j.subsidy_target = target


# ------------------------------------------------------------------ move each journey's dates into the past
def apply_timeline(j):
    ev = j.events
    ids = j.ids
    with SessionLocal() as db:
        def touch(row, created, updated=None):
            row.created_at = created
            row.updated_at = updated or created

        t_lead = ev["lead"]
        later = [ev[e] for e in ("lost", "book", "call") if e in ev]
        lead = db.get(Lead, ids["lead"])
        touch(lead, t_lead, max(later) if later else t_lead)
        if "call" in ev:
            lead.contacted_at = ev["call"]

        if ids.get("customer"):
            customer = db.get(Customer, ids["customer"])
            created = t_lead - timedelta(minutes=4) if j.portal else min(ev.get("call", t_lead) + timedelta(minutes=30), NOW - timedelta(minutes=1))
            touch(customer, created)
            account = db.query(User).filter(User.customer_id == customer.id).first()
            if account:
                touch(account, created)

        if ids.get("survey"):
            survey = db.get(SiteSurvey, ids["survey"])
            decided = ev.get("decide")
            touch(survey, ev["book"], decided or ev.get("visit") or ev["book"])
            if j.stage != "survey_scheduled":
                survey.scheduled_date = local_date(ev["visit"])

        if ids.get("quote"):
            quote = db.get(Quotation, ids["quote"])
            touch(quote, ev["decide"], ev.get("accept") or ev.get("quote_sent") or ev["decide"])

        if ids.get("order"):
            order = db.get(SalesOrder, ids["order"])
            last = max(ev[e] for e in ("accept", "pay1", "verify1", "confirm", "cancel", "dispatch", "deliver", "finish", "pay2") if e in ev)
            touch(order, ev["accept"], last)
            if "deliver" in ev:
                order.delivered_at = ev["deliver"]
            for record in ids["payments"]:
                payment = db.get(Payment, record["id"])
                created = ev[record["tag"]]
                done = ev.get("verify1", created) if record["tag"] == "pay1" and record["verified_later"] else (
                    min(created + timedelta(hours=2), NOW - timedelta(minutes=1)) if record["tag"] == "pay2" else created)
                payment.payment_date = created
                touch(payment, created, done)
            settled = ev["pay2"] if any(r["tag"] == "pay2" for r in ids["payments"]) else ev.get("verify1", ev.get("pay1", ev["accept"]))
            for invoice in db.query(Invoice).filter(Invoice.order_id == order.id, Invoice.ticket_id.is_(None)).all():
                touch(invoice, settled)

        if ids.get("inst"):
            inst = db.get(Installation, ids["inst"])
            touch(inst, ev["confirm"], ev.get("finish") or ev.get("deliver") or ev.get("dispatch") or ev["confirm"])
            inst.scheduled_date = local_date(ev["confirm"]) + timedelta(days=3)
            if "finish" in ev:
                inst.finish_time = ev["finish"]
                inst.start_time = ev["finish"] - timedelta(hours=j.hours)
                inst.signed_at = ev["finish"] - timedelta(minutes=12)
            for k, photo in enumerate(sorted(inst.photos, key=lambda p: p.id)):
                base = (inst.start_time or ev.get("deliver") or ev["confirm"]) + timedelta(minutes=25 * (k + 1))
                touch(photo, min(base, NOW - timedelta(minutes=1)))
            for serial in db.query(EquipmentSerial).filter(EquipmentSerial.order_id == ids["order"]).all():
                serial.updated_at = ev.get("dispatch", ev["confirm"])

        if "deliver" in ev and ids.get("order"):
            for warranty in db.query(Warranty).filter(Warranty.order_id == ids["order"]).all():
                start = local_date(ev["deliver"])
                warranty.start_date = start
                warranty.end_date = start + relativedelta(months=warranty.duration_months)
                warranty.status = "Active" if warranty.end_date >= TODAY else "Expired"
                touch(warranty, ev["deliver"])

        if ids.get("subsidy"):
            sub = db.get(SubsidyApplication, ids["subsidy"])
            events = sorted(sub.events, key=lambda e: e.id)
            opened = ev["confirm"]
            touch(sub, opened)
            when = {"Documents pending": opened}
            finish_day = local_date(ev["finish"]) if "finish" in ev else None
            if finish_day:
                when["Documents collected"] = ev["finish"] - timedelta(days=2)
                when["Applied"] = datetime.combine(finish_day + timedelta(days=4), time(10)) - IST
                when["Approved"] = datetime.combine(finish_day + timedelta(days=35), time(11)) - IST
                when["Disbursed"] = datetime.combine(finish_day + timedelta(days=70), time(12)) - IST
                sub.applied_on = finish_day + timedelta(days=4) if sub.applied_on else None
                sub.approved_on = finish_day + timedelta(days=35) if sub.approved_on else None
                sub.disbursed_on = finish_day + timedelta(days=70) if sub.disbursed_on else None
            else:
                when["Documents collected"] = opened + timedelta(days=1)
            for e in events:
                touch(e, min(when.get(e.status, opened), NOW - timedelta(minutes=1)))
            sub.updated_at = max(e.created_at for e in events)
        db.commit()


# ------------------------------------------------------------------ stock
def purchase_stock(ctx, journeys):
    """Buy what the plan needs from suppliers, with one serial number for every serial-numbered unit."""
    W = ctx["warehouse"]
    products = req(W, "get", "/api/stock/products").json()
    by_id = {p["id"]: p for p in products}

    with SessionLocal() as db:
        # The register has fewer serial numbers than the legacy demo stock counts. Units on hand must equal the
        # serial-numbered units actually in the warehouse.
        for product in db.query(Product).filter(Product.is_serialized.is_(True)).all():
            in_stock = db.query(EquipmentSerial).filter(EquipmentSerial.product_id == product.id, EquipmentSerial.status == "In Stock").count()
            item = db.query(InventoryItem).filter(InventoryItem.product_id == product.id).first()
            if item:
                item.quantity_on_hand = in_stock
        db.commit()

        needs = {}
        for j in journeys:
            if j.stage not in ("order_cancelled_confirmed", "confirmed", "dispatched", "delivered", "completed", "completed_old"):
                continue
            package = db.get(SolarPackage, j.pkg["id"])
            for comp in package.components:
                if comp.product.category != "Installation Service":
                    needs[comp.product_id] = needs.get(comp.product_id, 0) + comp.quantity
        legacy = {i.product_id: i.quantity_on_hand - i.reserved_quantity for i in db.query(InventoryItem).all()}

    plan = []
    for product_id, needed in needs.items():
        product = by_id[product_id]
        if product["is_serialized"]:
            quantity = needed + 8  # spare units for replacements and for the warehouse to scan
        else:
            quantity = max(0, math.ceil(needed * 1.15) - legacy.get(product_id, 0)) + 10
        if quantity:
            plan.append((product, quantity))

    suppliers = [("Sunrise Solar Distributors", 0.97, 120), ("Bharat Power Components", 1.0, 75), ("Deccan Inverter Traders", 1.06, 30)]
    shares = [0.4, 0.35, 0.25]
    for k, (supplier, factor, days_ago) in enumerate(suppliers):
        items = []
        for product, quantity in plan:
            part = quantity - sum(int(quantity * s) for s in shares[:2]) if k == 2 else int(quantity * shares[k])
            if part < 1:
                continue
            item = {"product_id": product["id"], "quantity": part, "unit_cost": round(product["cost_price"] * factor * RNG.uniform(0.98, 1.02), 2)}
            if product["is_serialized"]:
                prefix = serial_prefix(product)
                item["serial_numbers"] = []
                for _ in range(part):
                    SERIAL_COUNTERS[prefix] = SERIAL_COUNTERS.get(prefix, 1000) + 1
                    item["serial_numbers"].append(f"{prefix}26-{SERIAL_COUNTERS[prefix]:04d}")
            items.append(item)
        bought_on = local_date(stamp(days_ago, 11))
        made = req(W, "post", "/api/stock/purchases", json={
            "supplier": supplier, "invoice_reference": f"SUP-{bought_on:%y%m%d}-{k + 1}", "purchased_on": bought_on.isoformat(), "items": items,
        }).json()
        with SessionLocal() as db:
            purchase = db.get(StockPurchase, made["id"])
            purchase.created_at = purchase.updated_at = datetime.combine(bought_on, time(11)) - IST
            db.commit()
    return len(plan)


def serial_prefix(product):
    name, category = product["name"], product["category"]
    if category == "Inverter":
        for tag in ("5kW", "3kW", "1kW"):
            if tag in name:
                return f"INV{tag[0]}K-"
        return "INV-"
    return {"Battery": "BAT150-", "Charge Controller": "MPPT48-"}.get(category, category[:3].upper() + "-")


# ------------------------------------------------------------------ after-sales
def after_sales(ctx, journeys):
    SUP = ctx["support"]
    done = [j for j in journeys if j.stage == "completed"]
    recent = [j for j in done if (j.A - OFF["finish"]) >= 6]
    old = [j for j in journeys if j.stage == "completed_old"]
    made = []

    def spare_serial(db, serial):
        row = db.query(EquipmentSerial).filter(EquipmentSerial.serial_number == serial).one()
        spare = (db.query(EquipmentSerial).filter(EquipmentSerial.product_id == row.product_id, EquipmentSerial.status == "In Stock")
                 .order_by(EquipmentSerial.id.desc()).first())
        return spare.serial_number

    def raise_ticket(j, serial=None, panels=False, title="", description="", priority="Medium"):
        body = {"customer_id": j.ids["customer"], "title": title, "description": description, "priority": priority}
        if panels:
            with SessionLocal() as db:
                body["warranty_id"] = db.query(Warranty).filter(Warranty.order_id == j.ids["order"], Warranty.warranty_type == "bulk").one().id
        else:
            body["equipment_serial"] = serial
        return req(SUP, "post", "/api/tickets", json=body).json()

    def settle(j, ticket, ticket_days_ago, steps):
        """Walk a ticket forward and give each step a believable date."""
        times = {"open": stamp(ticket_days_ago)}
        for name in ("resolve", "confirm", "close"):
            ticket_days_ago = max(ticket_days_ago - RNG.randint(1, 3), 0)
            times[name] = stamp(ticket_days_ago, 15)
        order = ["open", "resolve", "confirm", "close"]
        prev = None
        for name in order:
            if prev and times[name] < prev:
                times[name] = min(prev + timedelta(hours=3), NOW - timedelta(minutes=1))
            prev = times[name]
        last = "open"
        for step in steps:
            if step[0] == "resolve":
                tid = ticket["id"]
                # The technician was assigned automatically when the ticket was raised, and reports the finding
                req(ctx["techs"][ticket["technician_id"]], "post", f"/api/repair-visits/{tid}/report",
                    json={"needs_replacement": bool(step[1]), "notes": "Checked on site"})
                if ticket["service_type"] == "BILLABLE":
                    req(SUP, "post", f"/api/tickets/{tid}/quote", json={"approved": True})
                if step[1]:
                    req(ctx["warehouse"], "post", f"/api/dispatch/replacements/{tid}/send", json={"serial_number": step[1]})
                req(SUP, "post", f"/api/tickets/{tid}/resolve")
                last = "resolve"
            elif step[0] == "confirm":
                req(SUP, "post", f"/api/tickets/{ticket['id']}/customer-confirm")
                last = "confirm"
            elif step[0] == "close":
                req(SUP, "post", f"/api/tickets/{ticket['id']}/close")
                last = "close"
        with SessionLocal() as db:
            row = db.get(ServiceTicket, ticket["id"])
            row.created_at, row.updated_at = times["open"], times[last]
            if row.invoice_id:
                invoice = db.get(Invoice, row.invoice_id)
                invoice.created_at = times["open"]
                invoice.updated_at = times["resolve"] if invoice.status != "Draft" else times["open"]
            db.commit()
        return times

    with SessionLocal() as db:
        first_serial = {j.idx: db.query(EquipmentSerial).filter(EquipmentSerial.order_id == j.ids["order"]).order_by(EquipmentSerial.id).first().serial_number for j in recent + old}

    # Under warranty: free repairs at different stages, two of them replacing the unit
    plans = [
        ("open", []), ("resolved", [("resolve", None)]), ("closed", [("resolve", None), ("confirm",), ("close",)]),
        ("replaced_resolved", "swap"), ("replaced_closed", "swap_close"), ("open", []), ("resolved", [("resolve", None)]),
    ]
    titles = [("Inverter shows fault code E04", "No output since the morning rain. Display shows E04."),
              ("Inverter beeping continuously", "A continuous beep and the grid light is off."),
              ("Monitoring app shows zero generation", "Panels are clean but the app shows zero units today."),
              ("Inverter not switching on", "No lights on the display after a power cut."),
              ("Charge controller overheating", "The unit is too hot to touch and the fan is not running."),
              ("Display stuck on standby", "The inverter stays on standby even at noon."),
              ("Ground fault warning", "The inverter reports an earth fault after heavy rain.")]
    for j, (_label, plan), (title, description) in zip(recent, plans, titles):
        serial = first_serial[j.idx]
        ticket = raise_ticket(j, serial=serial, title=title, description=description, priority=RNG.choice(["Medium", "High", "Urgent"]))
        assert ticket["service_type"] == "COVERED", (j.name, ticket)
        steps = plan
        if plan == "swap":
            with SessionLocal() as db:
                steps = [("resolve", spare_serial(db, serial))]
        elif plan == "swap_close":
            with SessionLocal() as db:
                steps = [("resolve", spare_serial(db, serial)), ("confirm",), ("close",)]
        settle(j, ticket, max(1, min(j.A - OFF["finish"] - 1, RNG.randint(2, 25))), steps)
        made.append(ticket["id"])

    # A panel on the 20 year warranty
    if len(recent) > len(plans):
        j = recent[len(plans)]
        ticket = raise_ticket(j, panels=True, title="Cracked panel after hailstorm", description="One panel has a visible crack across the cells after last night's hail.", priority="High")
        assert ticket["service_type"] == "COVERED"
        settle(j, ticket, 3, [])

    # Two years on: the 2 year warranties have ended, so repairs are billed (part, labour and GST)
    paid_portal = None
    for k, j in enumerate(old):
        if k == 3:  # the panels are still covered for 20 years
            ticket = raise_ticket(j, panels=True, title="Panel output dropped", description="One string produces far less than the others since the summer.")
            assert ticket["service_type"] == "COVERED"
            settle(j, ticket, 6, [])
            continue
        ticket = raise_ticket(j, serial=first_serial[j.idx], title="Inverter dead, no power", description="Inverter will not start. Warranty ended earlier this year.", priority="High")
        assert ticket["service_type"] == "BILLABLE" and ticket["invoice_id"], (j.name, ticket)
        if k == 0:  # repaired, billed and paid through the portal
            times = settle(j, ticket, 12, [("resolve", None), ("confirm",), ("close",)])
            invoice = req(j.client, "get", "/api/portal/invoices").json()
            invoice = next(i for i in invoice if i["id"] == ticket["invoice_id"])
            made_payment = req(j.client, "post", f"/api/portal/invoices/{invoice['id']}/payments", json={
                "amount": invoice["payable_now"], "reference_number": f"UTR{j.idx:03d}9{RNG.randint(100000, 999999)}"}).json()
            req(SUP, "post", f"/api/payments/{made_payment['id']}/verify")
            with SessionLocal() as db:
                paid_at = min(times["resolve"] + timedelta(days=1), NOW - timedelta(minutes=1))
                pay = db.get(Payment, made_payment["id"])
                pay.payment_date = pay.created_at = pay.updated_at = paid_at
                db.get(Invoice, ticket["invoice_id"]).updated_at = paid_at
                db.commit()
        elif k == 1:  # repaired and billed, not yet paid
            settle(j, ticket, 8, [("resolve", None)])
        else:  # reported today, still open, draft invoice waiting
            settle(j, ticket, 1, [])
        made.append(ticket["id"])
    return made


def pay_technicians(ctx):
    """Pay every technician for jobs finished before last month. Last month and this month stay due."""
    admin = ctx["admin"]
    month_start = TODAY.replace(day=1)
    paid_to = (month_start - relativedelta(months=1)) - timedelta(days=1)  # the end of the month before last
    count = 0
    with SessionLocal() as db:
        rows = db.query(Installation.technician_id).filter(
            Installation.status == "Completed", Installation.payout_id.is_(None)).distinct().all()
        tech_ids = [t for (t,) in rows if t]
    for tech_id in tech_ids:
        with SessionLocal() as db:
            first = db.query(Installation.finish_time).filter(
                Installation.technician_id == tech_id, Installation.status == "Completed", Installation.payout_id.is_(None)
            ).order_by(Installation.finish_time).first()
        start = local_date(first[0])
        if start > paid_to:
            continue
        response = admin.post("/api/payroll/payouts", json={
            "technician_id": tech_id, "from_date": start.isoformat(), "to_date": paid_to.isoformat(),
            "reference": f"NEFT-{paid_to:%Y%m}-{tech_id:03d}"})
        if response.status_code == 201:
            payout_id = response.json()["id"]
            with SessionLocal() as db:
                payout = db.get(TechnicianPayout, payout_id)
                payout.paid_on = payout.created_at = payout.updated_at = datetime.combine(paid_to + timedelta(days=5), time(15)) - IST
                db.commit()
            count += 1
    return count


def tidy_notifications(journeys):
    """Everything is read except what still needs someone's attention."""
    waiting = {"lead_new": "New enquiry", "survey_submitted": "is ready for approval", "quote_draft": "Draft quotation",
               "order_pending_reported": "reported for", "confirmed": "Pack order"}
    with SessionLocal() as db:
        db.query(Notification).update({Notification.is_read: True})
        for j in journeys:
            key = waiting.get(j.stage)
            if not key:
                continue
            for note in db.query(Notification).filter(Notification.role.isnot(None)).all():
                text = f"{note.title} {note.body or ''}"
                if key in text and j.name in text:
                    note.is_read = False
        # Place each alert on the day its journey reached that point
        by_name = {j.name: j for j in journeys}
        for note in db.query(Notification).all():
            text = f"{note.title} {note.body or ''}"
            for name, j in by_name.items():
                if name in text:
                    last = max(j.events.values())
                    note.created_at = note.updated_at = last
                    break
        db.commit()


# ------------------------------------------------------------------ audit
def audit(journeys):
    """Re-check the business rules against the rows this script created. Returns a list of problems."""
    problems = []
    demo = {j.ids["customer"] for j in journeys if j.ids.get("customer")}
    demo_leads = {j.ids["lead"] for j in journeys}
    with SessionLocal() as db:
        advance = settings.ADVANCE_PERCENT / 100
        verified = ("Verified", "Recorded")
        for order in db.query(SalesOrder).filter(SalesOrder.customer_id.in_(demo)).all():
            ref = f"SO-{order.id:04d}"
            quote = order.quotation
            if not quote or not quote.survey or quote.survey.status != "Approved":
                problems.append(f"{ref}: order without an approved survey")
            elif quote.survey.customer_id != order.customer_id:
                problems.append(f"{ref}: survey belongs to another customer")
            paid = sum(p.amount for p in order.payments if p.status in verified)
            held = sum(p.amount for p in order.payments if p.status in verified + ("Pending Verification",))
            if held > order.total_amount + 0.01:
                problems.append(f"{ref}: payments exceed the order total")
            if order.status in ("Confirmed", "Dispatched", "Completed") and paid + 0.01 < order.total_amount * advance:
                problems.append(f"{ref}: {order.status} without a verified advance")
            if order.status in ("Dispatched", "Completed"):
                needed = {}
                for comp in order.package.components:
                    if comp.product.is_serialized:
                        needed[comp.product_id] = needed.get(comp.product_id, 0) + comp.quantity
                got = {}
                for s in order.dispatched_serials:
                    got[s.product_id] = got.get(s.product_id, 0) + 1
                live = {pid: sum(1 for s in order.dispatched_serials if s.product_id == pid and s.status != "Replaced") for pid in needed}
                if live != needed:
                    problems.append(f"{ref}: serial numbers {live} do not match the package {needed}")
            if order.status in ("Dispatched", "Completed") and not order.installation:
                problems.append(f"{ref}: no installation job")
            if order.status == "Completed":
                inst = order.installation
                if inst.status != "Completed" or not inst.signature_path or not inst.signed_by_name:
                    problems.append(f"{ref}: completed without the homeowner's signature")
                if not inst.photos:
                    problems.append(f"{ref}: completed without photos")
                if not (inst.start_time and inst.finish_time and inst.start_time < inst.finish_time):
                    problems.append(f"{ref}: bad start and finish times")
                if inst.finish_time and inst.finish_time > NOW:
                    problems.append(f"{ref}: finished in the future")
                if not order.delivered_at:
                    problems.append(f"{ref}: completed but never delivered")
                elif not (order.created_at <= order.delivered_at <= inst.finish_time):
                    problems.append(f"{ref}: delivery and finish dates are out of order")
                if not (quote.created_at <= order.created_at):
                    problems.append(f"{ref}: order is older than its quotation")
                if quote.survey.created_at > quote.created_at:
                    problems.append(f"{ref}: quotation is older than its survey")
                if paid + 0.01 >= order.total_amount and not db.query(Invoice).filter(Invoice.order_id == order.id, Invoice.ticket_id.is_(None)).first():
                    problems.append(f"{ref}: fully paid but no invoice")
            if order.delivered_at:
                if not order.installation or order.installation.technician_id is None:
                    problems.append(f"{ref}: delivered with no technician")
                serials = [s for s in order.dispatched_serials]
                for s in serials:
                    w = db.query(Warranty).filter(Warranty.serial_number == s.serial_number).first()
                    if not w:
                        problems.append(f"{ref}: {s.serial_number} has no warranty")
                    elif w.end_date != w.start_date + relativedelta(months=w.duration_months):
                        problems.append(f"{ref}: {s.serial_number} warranty dates are wrong")
                panel = db.query(Warranty).filter(Warranty.order_id == order.id, Warranty.warranty_type == "bulk").first()
                if not panel or panel.duration_months != 240:
                    problems.append(f"{ref}: panels lack a 20 year warranty")
            elif db.query(Warranty).filter(Warranty.order_id == order.id).count():
                problems.append(f"{ref}: warranty exists before delivery")
            if order.status == "Cancelled" and (order.installation or any(s.status != "In Stock" for s in order.dispatched_serials)):
                problems.append(f"{ref}: cancelled order still holds a job or units")

        for lead in db.query(Lead).filter(Lead.id.in_(demo_leads)).all():
            has_progress = lead.surveys or lead.lead_status in ("Survey Scheduled", "Converted")
            if has_progress and not lead.contacted_at:
                problems.append(f"lead {lead.id}: moved on without the first call")
            if lead.surveys and lead.grid_connection_ok is False:
                problems.append(f"lead {lead.id}: survey despite an unsuitable grid")
            if lead.created_at > NOW:
                problems.append(f"lead {lead.id}: created in the future")
        for quote in db.query(Quotation).filter(Quotation.customer_id.in_(demo)).all():
            if quote.survey.status != "Approved":
                problems.append(f"QTN-{quote.id:05d}: quotation from a survey that is {quote.survey.status}")
            if quote.survey.recommended_capacity and abs(quote.package.capacity_kw - quote.survey.recommended_capacity) > 0.01:
                problems.append(f"QTN-{quote.id:05d}: package differs from the survey recommendation without a reason")
            if quote.survey.technician_id is None:
                problems.append(f"survey {quote.survey_id}: no technician")
        for survey in db.query(SiteSurvey).filter(SiteSurvey.customer_id.in_(demo)).all():
            if survey.status == "Scheduled" and survey.scheduled_date and survey.scheduled_date < TODAY:
                problems.append(f"survey {survey.id}: still 'Scheduled' with a visit date in the past")
            if survey.status in ("Submitted", "Approved", "Rejected") and survey.roof_area is None:
                problems.append(f"survey {survey.id}: {survey.status} with no measurements")

        for item in db.query(InventoryItem).all():
            if item.reserved_quantity < 0 or item.quantity_on_hand < item.reserved_quantity:
                problems.append(f"stock: {item.product.name} on hand {item.quantity_on_hand}, reserved {item.reserved_quantity}")
            if item.product.is_serialized:
                in_stock = db.query(EquipmentSerial).filter(EquipmentSerial.product_id == item.product_id, EquipmentSerial.status == "In Stock").count()
                if in_stock != item.quantity_on_hand:
                    problems.append(f"stock: {item.product.name} on hand {item.quantity_on_hand} but {in_stock} serial numbers in stock")

        for ticket in db.query(ServiceTicket).filter(ServiceTicket.customer_id.in_(demo)).all():
            ref = f"TCK-{ticket.id:04d}"
            if ticket.service_type == "COVERED" and ticket.customer_charge != 0:
                problems.append(f"{ref}: covered but charged")
            if ticket.service_type == "BILLABLE" and not ticket.invoice_id:
                problems.append(f"{ref}: billable with no invoice")
            if ticket.status == "Closed" and not ticket.customer_confirmed:
                problems.append(f"{ref}: closed without customer confirmation")
            if ticket.invoice_id and ticket.status in ("Resolved", "Customer Confirmed", "Closed") and ticket.invoice.status == "Draft":
                problems.append(f"{ref}: resolved but the repair invoice was never sent")
            if ticket.created_at > NOW:
                problems.append(f"{ref}: created in the future")
        for sub in db.query(SubsidyApplication).filter(SubsidyApplication.customer_id.in_(demo)).all():
            if sub.order.package.system_type != "On-Grid":
                problems.append(f"subsidy {sub.id}: file for an off-grid system")
        for w in db.query(Warranty).filter(Warranty.customer_id.in_(demo)).all():
            if w.start_date > TODAY:
                problems.append(f"warranty {w.id}: starts in the future")

        techs = db.query(User).filter(User.email.like("tech%@gmail.com")).count()
        if techs < 20:
            problems.append(f"only {techs} technician logins")
    return problems


def summary():
    with SessionLocal() as db:
        def count(model, *where):
            return db.query(model).filter(*where).count()
        lines = {
            "customers": count(Customer), "leads": count(Lead), "surveys": count(SiteSurvey), "quotations": count(Quotation),
            "orders": count(SalesOrder), "installations completed": count(Installation, Installation.status == "Completed"),
            "payments": count(Payment), "warranties": count(Warranty), "tickets": count(ServiceTicket),
            "invoices": count(Invoice), "subsidy files": count(SubsidyApplication), "technician payouts": count(TechnicianPayout),
            "stock serial numbers": count(EquipmentSerial),
        }
        by_status = {}
        for (status,) in db.query(SalesOrder.status).all():
            by_status[status] = by_status.get(status, 0) + 1
        jobs = {}
        for (tid,) in db.query(Installation.technician_id).all():
            jobs[tid] = jobs.get(tid, 0) + 1
        logins = {t.email: t.technician_id for t in db.query(User).filter(User.email.like("tech%@gmail.com")).all()}
    print("\nWhat is in the database now")
    for key, value in lines.items():
        print(f"  {key:<26}{value}")
    print("  orders by status:", ", ".join(f"{k} {v}" for k, v in sorted(by_status.items())))
    spread = [jobs.get(t, 0) for t in logins.values()]
    print(f"  installation jobs per technician login: min {min(spread)}, max {max(spread)}, total {sum(spread)}")


# ------------------------------------------------------------------ main
def main():
    with SessionLocal() as db:
        if db.query(User).filter(User.email == "tech1@gmail.com").first():
            print("The demo technicians already exist, so this data has been added before. Nothing was changed.")
            return
        if not db.query(SolarPackage).count():
            sys.exit("The catalogue is empty. Run `python backend/seed.py` first.")
        packages = [{"id": p.id, "kw": p.capacity_kw, "type": p.system_type} for p in db.query(SolarPackage).all()]
    print("Signing in the staff...")
    ctx = {
        "admin": login("admin@sunpower.test"), "sales": login("sales@sunpower.test"),
        "support": login("support@sunpower.test"), "warehouse": login("warehouse@sunpower.test"),
        "advance_pct": settings.ADVANCE_PERCENT,
    }

    print("Creating 20 technicians with logins (tech1@gmail.com ... tech20@gmail.com)...")
    used_phones, _ = existing_contacts()
    rates = [250, 260, 275, 280, 300, 300, 320, 325, 340, 350, 250, 270, 290, 310, 330, 350, 360, 380, 400, 420]
    for n, name in enumerate(TECH_NAMES, start=1):
        while True:
            phone = f"{RNG.choice('9876')}{RNG.randint(100000000, 999999999)}"
            if phone not in used_phones:
                used_phones.add(phone)
                break
        created = req(ctx["admin"], "post", "/api/admin/users", json={
            "name": name, "email": f"tech{n}@gmail.com", "phone": phone, "password": PASSWORD, "role": "technician"}).json()
        req(ctx["admin"], "put", f"/api/payroll/technicians/{created['technician_id']}/rate", json={"hourly_rate": float(rates[n - 1])})
    with SessionLocal() as db:
        logins = db.query(User).filter(User.role == "technician").all()
        ids = [(u.email, u.technician_id) for u in logins]
    ctx["techs"] = {tid: login(email) for email, tid in ids}

    print("Planning 100 customers...")
    journeys = plan_journeys(packages)
    print("Buying stock from suppliers...")
    purchase_stock(ctx, journeys)

    print("Running the journeys (everyone moves one step at a time, so the work spreads across the technicians)...")
    active = [(j, drive(j, ctx)) for j in journeys]
    rounds = 0
    while active:
        rounds += 1
        still = []
        for j, gen in active:
            try:
                next(gen)
                still.append((j, gen))
            except StopIteration:
                pass
            except Exception as error:
                raise RuntimeError(f"Customer {j.idx} ({j.name}, stage {j.stage}) failed: {error}") from error
        active = still
        if rounds % 5 == 0:
            print(f"  round {rounds}: {len(active)} customers still in progress")

    print("After-sales tickets and repair invoices...")
    tickets = after_sales(ctx, journeys)
    print(f"  {len(tickets)} tickets")
    paid = pay_technicians(ctx)
    print(f"Paid {paid} technicians for earlier months")
    tidy_notifications(journeys)

    print("\nChecking the data against the business rules...")
    problems = audit(journeys)
    summary()
    if problems:
        print(f"\n{len(problems)} problem(s):")
        for p in problems[:60]:
            print("  -", p)
        sys.exit(1)
    print("\nAudit passed: no rule is contradicted.")
    print("\nLogins (password for all of them: SunPower@123)")
    print("  Technicians: tech1@gmail.com ... tech20@gmail.com")
    print("  Customers:   any customer's email, for example", journeys[0].email)


def drive(j, ctx):
    yield from run(j, ctx)
    apply_timeline(j)
    yield


if __name__ == "__main__":
    main()
