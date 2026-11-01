from datetime import datetime, date
from typing import List, Optional
from sqlalchemy.orm import Session
from fastapi import HTTPException, status
from backend.app.models.models import Installation, EquipmentSerial, SalesOrder
from backend.app.core.roles import ADMIN
from backend.app.services.notification_service import notify
from backend.app.services.warranty_service import WarrantyService

class InstallationService:
    @staticmethod
    def complete_installation(
        db: Session,
        installation_id: int,
        confirmed_system_size: float,
        serial_numbers: List[str] = [],
        finish_time: Optional[datetime] = None,
        notes: Optional[str] = None,
        start_time: Optional[datetime] = None
    ) -> Installation:
        installation = db.query(Installation).filter(Installation.id == installation_id).first()
        if not installation:
            raise HTTPException(status_code=404, detail=f"Installation job #{installation_id} not found.")

        if installation.status == "Completed":
            return installation

        # Validation of system size
        if confirmed_system_size <= 0:
            raise HTTPException(status_code=400, detail="Confirmed system size must be greater than 0 kW.")

        order = installation.sales_order
        if not order:
            raise HTTPException(status_code=400, detail="Installation has no linked sales order.")

        serials = InstallationService._resolve_installed_serials(db, order, serial_numbers)

        try:
            # Update installation record
            installation.status = "Completed"
            installation.confirmed_system_size = confirmed_system_size
            installation.finish_time = finish_time or datetime.utcnow()
            if start_time:
                installation.start_time = start_time
            elif not installation.start_time:
                installation.start_time = installation.finish_time
            if notes:
                installation.notes = notes

            # Link serials to installation and mark Installed
            for s in serials:
                s.status = "Installed"
                s.installation_id = installation.id

            # Update sales order status
            order.status = "Completed"
            db.flush()

            # AUTO-CREATE WARRANTIES (Warranty Engine)
            WarrantyService.create_warranties_for_installation(db, installation)

            notify(
                db, f"Your solar system at {installation.customer.name if installation.customer else 'your site'} is installed",
                "Your warranties are active. You can see every serial number and warranty date in the portal.",
                link="warranties", customer_id=installation.customer_id,
            )
            notify(
                db, f"Installation SO-{order.id:04d} completed",
                f"{confirmed_system_size:g} kW signed off by the homeowner.", link="installations", role=ADMIN,
            )

            db.commit()
            db.refresh(installation)
            return installation
        except Exception as e:
            db.rollback()
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Installation completion failed: {str(e)}"
            )

    @staticmethod
    def _resolve_installed_serials(db: Session, order: SalesOrder, serial_numbers: List[str]) -> List[EquipmentSerial]:
        """Return the serials that went out on this order and must be installed.

        A serial is only acceptable if it was dispatched on this order (status
        Dispatched, order_id = this order). The per-product count must equal the
        serialized quantities in the package, so nothing is silently skipped.
        """
        cleaned = [s.strip() for s in serial_numbers if s and s.strip()]
        if cleaned:
            if len(cleaned) != len(set(cleaned)):
                raise HTTPException(status_code=400, detail="Duplicate serial numbers in installation submission.")
            serials = db.query(EquipmentSerial).filter(EquipmentSerial.serial_number.in_(cleaned)).all()
            found = {s.serial_number for s in serials}
            unknown = [sn for sn in cleaned if sn not in found]
            if unknown:
                raise HTTPException(
                    status_code=400,
                    detail=f"Installation rejected: unknown serial number(s): {', '.join(unknown)}."
                )
            for s in serials:
                if s.order_id != order.id or s.status != "Dispatched":
                    raise HTTPException(
                        status_code=400,
                        detail=f"Installation rejected: serial '{s.serial_number}' was not dispatched on this order "
                               f"(status '{s.status}', order #{s.order_id})."
                    )
        else:
            serials = db.query(EquipmentSerial).filter(
                EquipmentSerial.order_id == order.id,
                EquipmentSerial.status == "Dispatched"
            ).all()

        if not serials:
            raise HTTPException(
                status_code=400,
                detail="Cannot complete installation: No dispatched serialized equipment found for this order."
            )

        required = {}
        for comp in order.package.components:
            if comp.product.is_serialized:
                required[comp.product_id] = (comp.product.name, required.get(comp.product_id, (None, 0))[1] + comp.quantity)
        assigned = {}
        for s in serials:
            assigned[s.product_id] = assigned.get(s.product_id, 0) + 1
        for product_id, (name, qty) in required.items():
            if assigned.get(product_id, 0) != qty:
                raise HTTPException(
                    status_code=400,
                    detail=f"Installation rejected: '{name}' requires {qty} installed serial(s), "
                           f"but {assigned.get(product_id, 0)} were provided."
                )
        extra = [s.serial_number for s in serials if s.product_id not in required]
        if extra:
            raise HTTPException(
                status_code=400,
                detail=f"Installation rejected: serial(s) {', '.join(extra)} are not serialized items in this package."
            )
        return serials
