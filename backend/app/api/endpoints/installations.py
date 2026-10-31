from typing import List
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from backend.app.core.database import get_db
from backend.app.models.models import Installation, EquipmentSerial
from backend.app.schemas.schemas import InstallationResponse, InstallationCompleteRequest
from backend.app.services.installation_service import InstallationService

router = APIRouter(prefix="/installations", tags=["Installations"])

def _format_installation(inst: Installation) -> dict:
    return {
        "id": inst.id,
        "sales_order_id": inst.sales_order_id,
        "customer_id": inst.customer_id,
        "customer_name": inst.customer.name if inst.customer else None,
        "technician_id": inst.technician_id,
        "technician_name": inst.technician.name if inst.technician else "Assigned Crew",
        "scheduled_date": inst.scheduled_date,
        "system_capacity": inst.system_capacity,
        "confirmed_system_size": inst.confirmed_system_size,
        "status": inst.status,
        "start_time": inst.start_time,
        "finish_time": inst.finish_time,
        "notes": inst.notes,
        "created_at": inst.created_at,
        "updated_at": inst.updated_at
    }

@router.get("", response_model=List[InstallationResponse])
def list_installations(db: Session = Depends(get_db)):
    installations = db.query(Installation).order_by(Installation.scheduled_date.desc()).all()
    return [_format_installation(inst) for inst in installations]

@router.get("/{id}", response_model=InstallationResponse)
def get_installation(id: int, db: Session = Depends(get_db)):
    inst = db.query(Installation).filter(Installation.id == id).first()
    if not inst:
        raise HTTPException(status_code=404, detail="Installation not found")
    return _format_installation(inst)

@router.get("/{id}/serials")
def get_installation_serials(id: int, db: Session = Depends(get_db)):
    inst = db.query(Installation).filter(Installation.id == id).first()
    if not inst:
        raise HTTPException(status_code=404, detail="Installation not found")
    
    # Serials linked to this installation or order
    serials = db.query(EquipmentSerial).filter(
        (EquipmentSerial.installation_id == inst.id) | (EquipmentSerial.order_id == inst.sales_order_id)
    ).all()

    return [
        {
            "id": s.id,
            "product_name": s.product.name,
            "category": s.product.category,
            "serial_number": s.serial_number,
            "status": s.status
        }
        for s in serials
    ]

@router.post("/{id}/complete", response_model=InstallationResponse)
def complete_installation(
    id: int,
    payload: InstallationCompleteRequest,
    db: Session = Depends(get_db)
):
    completed = InstallationService.complete_installation(
        db=db,
        installation_id=id,
        confirmed_system_size=payload.confirmed_system_size,
        serial_numbers=payload.serial_numbers,
        finish_time=payload.finish_time,
        notes=payload.notes
    )
    return _format_installation(completed)
