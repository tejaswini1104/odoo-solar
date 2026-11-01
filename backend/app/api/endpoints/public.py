from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from backend.app.core.clock import business_today
from backend.app.core.database import get_db
from backend.app.models.models import EquipmentSerial, Warranty

# No sign-in: this is what a phone shows after scanning the QR label on a unit.
# It reveals the product and its warranty dates only, never who owns it.
router = APIRouter(prefix="/public", tags=["Public warranty check"])


@router.get("/warranty")
def check_warranty(serial: str = Query(min_length=3, max_length=100), db: Session = Depends(get_db)) -> dict:
    serial = serial.strip()
    unit = db.query(EquipmentSerial).filter(EquipmentSerial.serial_number == serial).first()
    if not unit:
        raise HTTPException(status_code=404, detail="We do not have a unit with that serial number.")

    base = {"serial_number": unit.serial_number, "product_name": unit.product.name, "category": unit.product.category}
    if unit.status == "Replaced":
        return {**base, "state": "replaced", "message": "This unit was replaced during a repair. Its replacement carries the warranty now."}

    warranty = (
        db.query(Warranty).filter(Warranty.serial_number == serial).order_by(Warranty.created_at.desc()).first()
    )
    if not warranty:
        return {**base, "state": "not_started", "message": "The warranty starts on the day the unit is delivered to the customer."}

    today = business_today()
    active = warranty.start_date <= today <= warranty.end_date
    return {
        **base,
        "state": "active" if active else "expired",
        "start_date": warranty.start_date,
        "end_date": warranty.end_date,
        "duration_months": warranty.duration_months,
        "days_left": max((warranty.end_date - today).days, 0),
        "message": "This unit is under warranty." if active else "The warranty on this unit has ended.",
    }
