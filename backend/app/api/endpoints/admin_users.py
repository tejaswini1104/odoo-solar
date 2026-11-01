from typing import List
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from backend.app.api.deps import get_current_user
from backend.app.core.database import get_db
from backend.app.core.roles import CUSTOMER
from backend.app.models.models import AuthSession, User
from backend.app.schemas.staff_schemas import StaffCreate, StaffUserResponse
from backend.app.services.user_service import create_staff_user

# Admin only: the access rule is applied where the router is included (api_router.py)
router = APIRouter(prefix="/admin/users", tags=["Admin - Staff accounts"])


def _out(user: User) -> StaffUserResponse:
    return StaffUserResponse(
        id=user.id, name=user.name, email=user.email, phone=user.phone,
        role=user.role, is_active=user.is_active, technician_id=user.technician_id,
    )


@router.get("", response_model=List[StaffUserResponse])
def list_staff(db: Session = Depends(get_db)):
    users = db.query(User).filter(User.role != CUSTOMER).order_by(User.role, User.name).all()
    return [_out(u) for u in users]


@router.post("", response_model=StaffUserResponse, status_code=201)
def create_staff(payload: StaffCreate, db: Session = Depends(get_db)):
    user = create_staff_user(
        db,
        name=payload.name,
        email=payload.email,
        password=payload.password,
        role=payload.role,
        phone=payload.phone,
        technician_id=payload.technician_id,
    )
    return _out(user)


def _set_active(db: Session, user_id: int, active: bool, acting: User) -> StaffUserResponse:
    user = db.query(User).filter(User.id == user_id, User.role != CUSTOMER).first()
    if not user:
        raise HTTPException(status_code=404, detail="Staff account not found.")
    if user.id == acting.id and not active:
        raise HTTPException(status_code=400, detail="You cannot deactivate your own account.")
    user.is_active = active
    if not active:
        # End any sessions they have open
        db.query(AuthSession).filter(AuthSession.user_id == user.id).delete()
    db.commit()
    db.refresh(user)
    return _out(user)


@router.post("/{user_id}/deactivate", response_model=StaffUserResponse)
def deactivate_staff(user_id: int, acting: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return _set_active(db, user_id, False, acting)


@router.post("/{user_id}/activate", response_model=StaffUserResponse)
def activate_staff(user_id: int, acting: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return _set_active(db, user_id, True, acting)
