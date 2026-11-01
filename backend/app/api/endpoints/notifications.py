from typing import List
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import or_
from sqlalchemy.orm import Session
from backend.app.api.deps import get_current_user
from backend.app.core.database import get_db
from backend.app.models.models import Notification, User

# Every signed-in user sees only the alerts meant for their role, their technician record or their customer account.
router = APIRouter(prefix="/notifications", tags=["Notifications"])


def _mine(db: Session, user: User):
    if user.role == "customer":
        return db.query(Notification).filter(Notification.customer_id == user.customer_id)
    conditions = [Notification.role == user.role]
    if user.technician_id:
        conditions.append(Notification.technician_id == user.technician_id)
    return db.query(Notification).filter(or_(*conditions))


def _out(n: Notification) -> dict:
    return {
        "id": n.id, "title": n.title, "body": n.body, "link": n.link,
        "is_read": n.is_read, "created_at": n.created_at,
    }


@router.get("")
def list_notifications(user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> dict:
    query = _mine(db, user)
    unread = query.filter(Notification.is_read.is_(False)).count()
    rows = query.order_by(Notification.created_at.desc()).limit(30).all()
    return {"unread": unread, "items": [_out(n) for n in rows]}


@router.post("/read-all", status_code=204)
def read_all(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    ids = [n.id for n in _mine(db, user).filter(Notification.is_read.is_(False)).all()]
    if ids:
        db.query(Notification).filter(Notification.id.in_(ids)).update({"is_read": True}, synchronize_session=False)
        db.commit()


@router.post("/{notification_id}/read", status_code=204)
def read_one(notification_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    note = _mine(db, user).filter(Notification.id == notification_id).first()
    if not note:
        raise HTTPException(status_code=404, detail="Notification not found.")
    note.is_read = True
    db.commit()
