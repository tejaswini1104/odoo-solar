from sqlalchemy.orm import Session
from fastapi import HTTPException, status
from backend.app.models.models import (
    ServiceTicket, Warranty, EquipmentSerial, Invoice, InvoiceItem, Customer
)
from backend.app.core.clock import business_today
from backend.app.core.config import settings
from backend.app.core.roles import SUPPORT
from backend.app.schemas.schemas import ServiceTicketCreate
from backend.app.services.notification_service import notify

class TicketService:
    @staticmethod
    def create_ticket(db: Session, ticket_in: ServiceTicketCreate) -> ServiceTicket:
        customer = db.query(Customer).filter(Customer.id == ticket_in.customer_id).first()
        if not customer:
            raise HTTPException(status_code=404, detail=f"Customer #{ticket_in.customer_id} not found.")

        serial_str = ticket_in.equipment_serial.strip()
        serial_obj = db.query(EquipmentSerial).filter(
            EquipmentSerial.serial_number == serial_str
        ).first()
        if not serial_obj:
            raise HTTPException(
                status_code=404,
                detail=f"No equipment with serial number '{serial_str}' is registered. Check the serial printed on the unit.",
            )
        if serial_obj.order_id is None:
            raise HTTPException(
                status_code=400,
                detail=f"Serial number '{serial_str}' has not been delivered to a customer yet, so it cannot have a repair ticket.",
            )
        order = serial_obj.order
        if order and order.customer_id != customer.id:
            raise HTTPException(status_code=403, detail="This serial number belongs to a different customer.")

        # Look up warranty for this serial number
        warranty = db.query(Warranty).filter(
            Warranty.serial_number == serial_str
        ).order_by(Warranty.created_at.desc()).first()

        today = business_today()
        is_covered = False

        if warranty:
            # Check date
            if warranty.start_date <= today <= warranty.end_date:
                is_covered = True
                warranty.status = "Active"
            else:
                warranty.status = "Expired"
        # No warranty record found -> BILLABLE

        service_type = "COVERED" if is_covered else "BILLABLE"

        ticket = ServiceTicket(
            customer_id=customer.id,
            equipment_serial=serial_str,
            installation_id=serial_obj.installation_id,
            title=ticket_in.title,
            description=ticket_in.description,
            priority=ticket_in.priority,
            status="Open",
            service_type=service_type,
            customer_charge=0.0,
            customer_confirmed=False
        )
        db.add(ticket)
        db.flush()

        # Out of warranty: bill the faulty part at its list price plus the visit and labour charge, with GST
        if service_type == "BILLABLE":
            product = serial_obj.product
            labour = round(settings.SERVICE_LABOUR_CHARGE, 2)
            part = round(product.unit_price, 2)
            subtotal = round(part + labour, 2)
            tax = round(subtotal * settings.GST_PERCENT / 100, 2)
            total = round(subtotal + tax, 2)

            draft_invoice = Invoice(
                invoice_number=f"INV-SRV-{ticket.id:04d}",
                customer_id=customer.id,
                order_id=serial_obj.order_id,
                ticket_id=ticket.id,
                subtotal=subtotal,
                tax=tax,
                total=total,
                status="Draft"
            )
            db.add(draft_invoice)
            db.flush()
            db.add_all([
                InvoiceItem(
                    invoice_id=draft_invoice.id,
                    description=f"Repair or replacement: {product.name} (serial {serial_str})",
                    quantity=1, unit_price=part, total=part,
                ),
                InvoiceItem(
                    invoice_id=draft_invoice.id,
                    description="Technician site visit and labour",
                    quantity=1, unit_price=labour, total=labour,
                ),
            ])
            ticket.customer_charge = total
            ticket.invoice_id = draft_invoice.id

        notify(
            db,
            f"New repair ticket TCK-{ticket.id:04d}: {ticket.title}",
            f"{service_type.title()} repair for serial {serial_str} ({customer.name}).",
            link="tickets", role=SUPPORT,
        )
        db.commit()
        db.refresh(ticket)
        return ticket

    @staticmethod
    def resolve_ticket(db: Session, ticket_id: int) -> ServiceTicket:
        ticket = db.query(ServiceTicket).filter(ServiceTicket.id == ticket_id).first()
        if not ticket:
            raise HTTPException(status_code=404, detail="Service ticket not found.")
        
        if ticket.status in ("Resolved", "Customer Confirmed", "Closed"):
            raise HTTPException(status_code=400, detail=f"This ticket is already '{ticket.status}'.")
        ticket.status = "Resolved"
        notify(
            db, f"Your repair ticket TCK-{ticket.id:04d} was marked fixed",
            "Please confirm that everything works so we can close it.",
            link="support", customer_id=ticket.customer_id,
        )
        db.commit()
        db.refresh(ticket)
        return ticket

    @staticmethod
    def customer_confirm_ticket(db: Session, ticket_id: int) -> ServiceTicket:
        ticket = db.query(ServiceTicket).filter(ServiceTicket.id == ticket_id).first()
        if not ticket:
            raise HTTPException(status_code=404, detail="Service ticket not found.")
        
        if ticket.status != "Resolved":
            raise HTTPException(status_code=400, detail="The ticket must be resolved before the customer confirms.")
        ticket.customer_confirmed = True
        ticket.status = "Customer Confirmed"
        db.commit()
        db.refresh(ticket)
        return ticket

    @staticmethod
    def close_ticket(db: Session, ticket_id: int) -> ServiceTicket:
        ticket = db.query(ServiceTicket).filter(ServiceTicket.id == ticket_id).first()
        if not ticket:
            raise HTTPException(status_code=404, detail="Service ticket not found.")

        # HARD GATE: customer confirmation required
        if not ticket.customer_confirmed:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Ticket cannot be closed without customer confirmation. The customer must confirm resolution first."
            )

        ticket.status = "Closed"
        db.commit()
        db.refresh(ticket)
        return ticket
