from datetime import date, datetime
from dateutil.relativedelta import relativedelta
from sqlalchemy.orm import Session
from backend.app.models.models import Warranty, Installation, EquipmentSerial, Product
from backend.app.core.config import settings

class WarrantyService:
    @staticmethod
    def create_warranties_for_installation(db: Session, installation: Installation):
        """Auto-create warranty records on installation completion."""
        completion_date = installation.finish_time.date() if installation.finish_time else date.today()
        order = installation.sales_order
        durations = settings.WARRANTY_DURATION_MONTHS

        # 1. Serialized products warranty
        serials = db.query(EquipmentSerial).filter(
            EquipmentSerial.installation_id == installation.id
        ).all()

        for serial in serials:
            product = serial.product
            months = durations.get(product.category, 24) # default 24 months
            end_date = completion_date + relativedelta(months=months)
            
            # Check if warranty already exists
            existing = db.query(Warranty).filter(
                Warranty.serial_number == serial.serial_number,
                Warranty.installation_id == installation.id
            ).first()

            if not existing:
                warranty = Warranty(
                    customer_id=installation.customer_id,
                    installation_id=installation.id,
                    order_id=order.id,
                    product_id=product.id,
                    serial_number=serial.serial_number,
                    warranty_type="serialized",
                    duration_months=months,
                    start_date=completion_date,
                    end_date=end_date,
                    status="Active" if end_date >= date.today() else "Expired"
                )
                db.add(warranty)

        # 2. Bulk Solar Panels Warranty (20 years)
        panel_product = None
        for comp in order.package.components:
            if comp.product.category == "Solar Panels":
                panel_product = comp.product
                break

        if panel_product:
            existing_panel_w = db.query(Warranty).filter(
                Warranty.installation_id == installation.id,
                Warranty.warranty_type == "bulk",
                Warranty.product_id == panel_product.id
            ).first()

            if not existing_panel_w:
                panel_months = durations.get("Solar Panels", 240) # 20 years
                panel_end_date = completion_date + relativedelta(months=panel_months)
                panel_warranty = Warranty(
                    customer_id=installation.customer_id,
                    installation_id=installation.id,
                    order_id=order.id,
                    product_id=panel_product.id,
                    serial_number=None, # Bulk category warranty
                    warranty_type="bulk",
                    duration_months=panel_months,
                    start_date=completion_date,
                    end_date=panel_end_date,
                    status="Active" if panel_end_date >= date.today() else "Expired"
                )
                db.add(panel_warranty)
