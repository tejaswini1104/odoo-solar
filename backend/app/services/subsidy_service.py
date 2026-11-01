from datetime import date
from typing import Optional
from fastapi import HTTPException
from sqlalchemy.orm import Session
from backend.app.models.models import Lead, SalesOrder, SubsidyApplication, SubsidyEvent, User

# A subsidy file moves through these steps in order. It can also be Rejected at any point before the money arrives.
FLOW = ["Documents pending", "Documents collected", "Applied", "Approved", "Disbursed"]
FINAL = ("Disbursed", "Rejected")


class SubsidyService:
    @staticmethod
    def customer_wants_subsidy(db: Session, customer_id: int) -> bool:
        return (
            db.query(Lead).filter(Lead.customer_id == customer_id, Lead.subsidy_requirement.is_(True)).first()
            is not None
        )

    @staticmethod
    def open_for_order(db: Session, order: SalesOrder, user: Optional[User] = None, force: bool = False):
        """Open the subsidy file for an order. Without `force`, only when the customer asked for the subsidy.

        Adds to the open transaction and does not commit, so it can run inside order confirmation.
        """
        existing = db.query(SubsidyApplication).filter(SubsidyApplication.order_id == order.id).first()
        if existing:
            return existing
        if not force and not SubsidyService.customer_wants_subsidy(db, order.customer_id):
            return None
        application = SubsidyApplication(order_id=order.id, customer_id=order.customer_id, status=FLOW[0])
        db.add(application)
        db.flush()
        db.add(SubsidyEvent(
            subsidy_id=application.id, status=FLOW[0],
            note="File opened" + ("" if force else " because the customer asked for the subsidy"),
            user_id=user.id if user else None,
        ))
        return application

    @staticmethod
    def update(
        db: Session,
        application: SubsidyApplication,
        user: User,
        status: Optional[str] = None,
        reference_number: Optional[str] = None,
        expected_amount: Optional[float] = None,
        received_amount: Optional[float] = None,
        note: Optional[str] = None,
    ) -> SubsidyApplication:
        changing_data = any(v is not None for v in (status, reference_number, expected_amount, received_amount))
        if application.status in FINAL and changing_data:
            raise HTTPException(
                status_code=400,
                detail=f"This subsidy file is '{application.status}', so only notes can be added now.",
            )

        if reference_number is not None:
            application.reference_number = reference_number.strip() or None
        if expected_amount is not None:
            application.expected_amount = expected_amount
        if received_amount is not None:
            application.received_amount = received_amount

        new_status = status if status and status != application.status else None
        if new_status:
            if new_status == "Rejected":
                pass  # allowed from any step that is not final
            else:
                current = FLOW.index(application.status)
                if new_status not in FLOW or FLOW.index(new_status) != current + 1:
                    next_step = FLOW[current + 1] if current + 1 < len(FLOW) else None
                    raise HTTPException(
                        status_code=400,
                        detail=f"A subsidy file moves one step at a time. The next step after '{application.status}' is '{next_step}'.",
                    )
            today = date.today()
            if new_status == "Applied":
                if not application.reference_number:
                    raise HTTPException(status_code=400, detail="Enter the application number from the subsidy portal first.")
                application.applied_on = today
            elif new_status == "Approved":
                if not application.expected_amount or application.expected_amount <= 0:
                    raise HTTPException(status_code=400, detail="Enter the approved subsidy amount first.")
                application.approved_on = today
            elif new_status == "Disbursed":
                if not application.received_amount or application.received_amount <= 0:
                    raise HTTPException(status_code=400, detail="Enter the amount that was received first.")
                application.disbursed_on = today
            application.status = new_status

        if new_status or (note and note.strip()):
            db.add(SubsidyEvent(
                subsidy_id=application.id,
                status=application.status,
                note=(note or "").strip() or None,
                user_id=user.id,
            ))
        db.commit()
        db.refresh(application)
        return application
