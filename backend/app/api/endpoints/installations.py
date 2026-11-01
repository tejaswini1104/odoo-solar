from datetime import datetime, timedelta, timezone
from typing import List
from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session
from backend.app.api.deps import get_current_user, require_roles
from backend.app.core.database import get_db
from backend.app.core.roles import SALES, TECHNICIAN
from backend.app.models.models import Installation, EquipmentSerial, InstallationPhoto, Technician, User
from backend.app.schemas.schemas import InstallationResponse, InstallationCompleteRequest
from backend.app.services.installation_proof_service import InstallationProofService, resolve_file
from backend.app.services.installation_service import InstallationService

# Access by role is set where this router is included (api_router.py).
router = APIRouter(prefix="/installations", tags=["Installations"])


class AssignTechnicianRequest(BaseModel):
    technician_id: int


class SignatureRequest(BaseModel):
    signed_by: str = Field(min_length=2, max_length=255, description="The homeowner's name")
    signature_data_url: str = Field(min_length=30, max_length=600_000)


def _naive_utc(value):
    """The database stores UTC without a time zone. A time sent with a zone (as the browser does) is converted."""
    if value is not None and value.tzinfo is not None:
        return value.astimezone(timezone.utc).replace(tzinfo=None)
    return value


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
        "photo_count": len(inst.photos),
        "signed_by_name": inst.signed_by_name,
        "signed_at": inst.signed_at,
        "created_at": inst.created_at,
        "updated_at": inst.updated_at
    }


def _photo_out(inst_id: int, photo: InstallationPhoto) -> dict:
    return {
        "id": photo.id,
        "caption": photo.caption,
        "original_name": photo.original_name,
        "created_at": photo.created_at,
        "url": f"/api/installations/{inst_id}/photos/{photo.id}/file",
    }


def _own_job_only(user: User, inst: Installation) -> bool:
    """A technician works only on jobs assigned to them. Other roles with access see every job."""
    return user.role != TECHNICIAN or inst.technician_id == user.technician_id


def _get_visible(db: Session, user: User, installation_id: int) -> Installation:
    inst = db.query(Installation).filter(Installation.id == installation_id).first()
    if not inst or not _own_job_only(user, inst):
        raise HTTPException(status_code=404, detail="Installation not found")
    return inst


@router.get("", response_model=List[InstallationResponse])
def list_installations(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    query = db.query(Installation)
    if user.role == TECHNICIAN:
        query = query.filter(Installation.technician_id == user.technician_id)
    installations = query.order_by(Installation.scheduled_date.desc()).all()
    return [_format_installation(inst) for inst in installations]

@router.get("/{id}", response_model=InstallationResponse)
def get_installation(id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return _format_installation(_get_visible(db, user, id))

@router.get("/{id}/serials")
def get_installation_serials(id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    inst = _get_visible(db, user, id)

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

# ----- Proof of the finished work: photos and the homeowner's signature -----
@router.get("/{id}/photos")
def list_photos(id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    inst = _get_visible(db, user, id)
    return [_photo_out(inst.id, p) for p in sorted(inst.photos, key=lambda p: p.id)]

@router.post("/{id}/photos", status_code=201)
async def upload_photo(
    id: int,
    file: UploadFile = File(...),
    caption: str = Form(""),
    user: User = Depends(require_roles(TECHNICIAN)),  # the technician on the job takes the photos
    db: Session = Depends(get_db),
):
    inst = _get_visible(db, user, id)
    photo = await InstallationProofService.save_photo(db, inst, file, caption, user)
    return _photo_out(inst.id, photo)

@router.get("/{id}/photos/{photo_id}/file")
def get_photo_file(id: int, photo_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    inst = _get_visible(db, user, id)
    photo = next((p for p in inst.photos if p.id == photo_id), None)
    if not photo:
        raise HTTPException(status_code=404, detail="Photo not found.")
    return FileResponse(resolve_file(photo.file_path), headers={"Cache-Control": "private, max-age=3600"})

@router.delete("/{id}/photos/{photo_id}", status_code=204)
def delete_photo(
    id: int,
    photo_id: int,
    user: User = Depends(require_roles(TECHNICIAN)),
    db: Session = Depends(get_db),
):
    InstallationProofService.delete_photo(db, _get_visible(db, user, id), photo_id)

@router.post("/{id}/signature", response_model=InstallationResponse)
def save_signature(
    id: int,
    payload: SignatureRequest,
    user: User = Depends(require_roles(TECHNICIAN)),
    db: Session = Depends(get_db),
):
    inst = InstallationProofService.save_signature(db, _get_visible(db, user, id), payload.signed_by, payload.signature_data_url)
    return _format_installation(inst)

@router.get("/{id}/signature/file")
def get_signature_file(id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    inst = _get_visible(db, user, id)
    if not inst.signature_path:
        raise HTTPException(status_code=404, detail="No signature has been recorded.")
    return FileResponse(resolve_file(inst.signature_path), media_type="image/png", headers={"Cache-Control": "private, max-age=3600"})

@router.post("/{id}/assign", response_model=InstallationResponse)
def assign_technician(
    id: int,
    payload: AssignTechnicianRequest,
    _user: User = Depends(require_roles(SALES)),  # Sales decide who goes to which site
    db: Session = Depends(get_db),
):
    inst = db.query(Installation).filter(Installation.id == id).first()
    if not inst:
        raise HTTPException(status_code=404, detail="Installation not found")
    if inst.status == "Completed":
        raise HTTPException(status_code=400, detail="A completed installation cannot be reassigned.")
    technician = db.get(Technician, payload.technician_id)
    if not technician:
        raise HTTPException(status_code=404, detail="Technician not found")
    inst.technician_id = technician.id
    db.commit()
    db.refresh(inst)
    return _format_installation(inst)

@router.post("/{id}/complete", response_model=InstallationResponse)
def complete_installation(
    id: int,
    payload: InstallationCompleteRequest,
    user: User = Depends(require_roles(TECHNICIAN)),  # only the technician on the job marks it complete
    db: Session = Depends(get_db)
):
    inst = _get_visible(db, user, id)  # a technician cannot complete someone else's job
    if inst.status == "Completed":
        return _format_installation(inst)

    start = _naive_utc(payload.start_time) or inst.start_time
    finish = _naive_utc(payload.finish_time) or datetime.utcnow()
    if start is None:
        raise HTTPException(status_code=400, detail="Enter the time the work started.")
    if finish < start:
        raise HTTPException(status_code=400, detail="The finish time cannot be before the start time.")
    if finish > datetime.utcnow() + timedelta(minutes=10):
        raise HTTPException(status_code=400, detail="The finish time cannot be in the future.")
    if finish - start > timedelta(days=7):
        raise HTTPException(status_code=400, detail="A single job cannot run longer than 7 days. Please check the times.")

    InstallationProofService.ensure_proof(db, inst)
    completed = InstallationService.complete_installation(
        db=db,
        installation_id=id,
        confirmed_system_size=payload.confirmed_system_size,
        serial_numbers=payload.serial_numbers,
        finish_time=finish,
        notes=payload.notes,
        start_time=start,
    )
    return _format_installation(completed)
