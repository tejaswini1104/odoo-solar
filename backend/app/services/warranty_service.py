from datetime import date, datetime
from dateutil.relativedelta import relativedelta
from sqlalchemy.orm import Session
from backend.app.models.models import Warranty, Installation, EquipmentSerial, Product
from backend.app.core.config import settings

class WarrantyService:
    @staticmethod
    def create_warranties_for_delivery(db: Session, order, start_date: date):
        """Start the warranty clock when the goods are delivered, for every serial number and for the panels.

        Completing the installation later creates only what is still missing, so nothing is counted twice.
        """
        installation = order.installation
        if not installation:
            return
        durations = settings.WARRANTY_DURATION_MONTHS

        serials = db.query(EquipmentSerial).filter(EquipmentSerial.order_id == order.id).all()
        for serial in serials:
            if db.query(Warranty).filter(Warranty.serial_number == serial.serial_number).first():
                continue
            months = durations.get(serial.product.category, 24)
            end_date = start_date + relativedelta(months=months)
            db.add(Warranty(
                customer_id=order.customer_id,
                installation_id=installation.id,
                order_id=order.id,
                product_id=serial.product_id,
                serial_number=serial.serial_number,
                warranty_type="serialized",
                duration_months=months,
                start_date=start_date,
                end_date=end_date,
                status="Active" if end_date >= date.today() else "Expired",
            ))

        panel_product = next(
            (comp.product for comp in order.package.components if comp.product.category == "Solar Panels"), None
        )
        if panel_product and not db.query(Warranty).filter(
            Warranty.installation_id == installation.id,
            Warranty.warranty_type == "bulk",
            Warranty.product_id == panel_product.id,
        ).first():
            months = durations.get("Solar Panels", 240)
            end_date = start_date + relativedelta(months=months)
            db.add(Warranty(
                customer_id=order.customer_id,
                installation_id=installation.id,
                order_id=order.id,
                product_id=panel_product.id,
                serial_number=None,
                warranty_type="bulk",
                duration_months=months,
                start_date=start_date,
                end_date=end_date,
                status="Active" if end_date >= date.today() else "Expired",
            ))

    @staticmethod
    def create_warranties_for_installation(db: Session, installation: Installation):
        """Safety net on completion: cover anything the delivery step did not (an order never marked delivered).

        Uses the same logic as delivery, so a serial number or the panels are never warranted twice. When the
        delivery was recorded, the clock already started then and nothing new is created here.
        """
        completion_date = installation.finish_time.date() if installation.finish_time else date.today()
        # Serials are linked to the order at dispatch; make sure the ones installed are covered by it too.
        WarrantyService.create_warranties_for_delivery(db, installation.sales_order, completion_date)
