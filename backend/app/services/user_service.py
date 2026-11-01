from typing import Optional
from fastapi import HTTPException
from sqlalchemy.orm import Session
from backend.app.core.roles import STAFF_ROLES, TECHNICIAN
from backend.app.core.security import hash_password
from backend.app.models.models import Technician, User


def create_staff_user(
    db: Session,
    name: str,
    email: str,
    password: str,
    role: str,
    phone: Optional[str] = None,
    technician_id: Optional[int] = None,
) -> User:
    """Create a staff account. A technician account is linked to a technician record (new, or an existing free one)."""
    role = role.strip().lower()
    if role not in STAFF_ROLES:
        raise HTTPException(status_code=400, detail=f"Role must be one of: {', '.join(STAFF_ROLES)}.")

    email = email.strip().lower()
    if db.query(User).filter(User.email == email).first():
        raise HTTPException(status_code=409, detail="An account with this email already exists.")

    linked_technician_id = None
    if role == TECHNICIAN:
        if technician_id is not None:
            technician = db.get(Technician, technician_id)
            if not technician:
                raise HTTPException(status_code=404, detail="Technician record not found.")
            if db.query(User).filter(User.technician_id == technician_id).first():
                raise HTTPException(status_code=409, detail="That technician record already has a login.")
            linked_technician_id = technician.id
        else:
            technician = Technician(name=name.strip(), phone=phone)
            db.add(technician)
            db.flush()
            linked_technician_id = technician.id
    elif technician_id is not None:
        raise HTTPException(status_code=400, detail="Only technician accounts can be linked to a technician record.")

    user = User(
        name=name.strip(),
        email=email,
        phone=phone,
        password_hash=hash_password(password),
        role=role,
        technician_id=linked_technician_id,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user
