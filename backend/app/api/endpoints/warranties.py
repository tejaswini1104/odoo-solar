from typing import List, Optional
from datetime import date
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from backend.app.core.database import get_db
from backend.app.models.models import Warranty
from backend.app.schemas.schemas import WarrantyResponse

router = APIRouter(prefix="/warranties", tags=["Warranties"])

def _format_warranty(w: Warranty) -> dict:
    today = date.today()
    is_active = (w.start_date <= today <= w.end_date) and (w.status == "Active")
    return {
        "id": w.id,
        "customer_id": w.customer_id,
        "customer_name": w.customer.name if w.customer else None,
        "installation_id": w.installation_id,
        "order_id": w.order_id,
        "product_id": w.product_id,
        "product_name": w.product.name if w.product else None,
        "category": w.product.category if w.product else None,
        "serial_number": w.serial_number,
        "warranty_type": w.warranty_type,
        "duration_months": w.duration_months,
        "start_date": w.start_date,
        "end_date": w.end_date,
        "status": "Active" if is_active else "Expired",
        "is_currently_active": is_active,
        "created_at": w.created_at
    }

@router.get("", response_model=List[WarrantyResponse])
def list_warranties(
    serial_number: Optional[str] = None,
    db: Session = Depends(get_db)
):
    query = db.query(Warranty)
    if serial_number:
        query = query.filter(Warranty.serial_number.ilike(f"%{serial_number.strip()}%"))
    warranties = query.order_by(Warranty.created_at.desc()).all()
    return [_format_warranty(w) for w in warranties]

@router.get("/{serial_number}", response_model=WarrantyResponse)
def get_warranty_by_serial(serial_number: str, db: Session = Depends(get_db)):
    w = db.query(Warranty).filter(
        Warranty.serial_number == serial_number.strip()
    ).order_by(Warranty.created_at.desc()).first()

    if not w:
        raise HTTPException(
            status_code=404,
            detail=f"No warranty found for serial number '{serial_number}'."
        )
    return _format_warranty(w)
