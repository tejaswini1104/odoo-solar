from typing import Optional
from sqlalchemy.orm import Session
from backend.app.models.models import Notification


def notify(
    db: Session,
    title: str,
    body: Optional[str] = None,
    link: Optional[str] = None,
    role: Optional[str] = None,
    customer_id: Optional[int] = None,
    technician_id: Optional[int] = None,
) -> Notification:
    """Queue an alert in the caller's transaction. It is saved, or rolled back, together with the work it reports."""
    note = Notification(
        title=title, body=body, link=link, role=role, customer_id=customer_id, technician_id=technician_id
    )
    db.add(note)
    return note
