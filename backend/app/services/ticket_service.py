from datetime import date, datetime
from sqlalchemy.orm import Session
from fastapi import HTTPException, status
from backend.app.models.models import (
    ServiceTicket, Warranty, EquipmentSerial, Invoice, InvoiceItem, Customer
)
from backend.app.schemas.schemas import ServiceTicketCreate

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

        # Look up warranty for this serial number
        warranty = db.query(Warranty).filter(
            Warranty.serial_number == serial_str
        ).order_by(Warranty.created_at.desc()).first()

        today = date.today()
        is_covered = False

        if warranty:
            # Check date
            if warranty.start_date <= today <= warranty.end_date:
                is_covered = True
                warranty.status = "Active"
            else:
                is_covered = False
                warranty.status = "Expired"
        else:
            # No warranty record found -> BILLABLE
            is_covered = False

        service_type = "COVERED" if is_covered else "BILLABLE"
        customer_charge = 0.0

        # Create ticket
        ticket = ServiceTicket(
            customer_id=customer.id,
            equipment_serial=serial_str,
            installation_id=serial_obj.installation_id if serial_obj else None,
            title=ticket_in.title,
            description=ticket_in.description,
            priority=ticket_in.priority,
            status="Open",
            service_type=service_type,
            customer_charge=customer_charge,
            customer_confirmed=False
        )
        db.add(ticket)
        db.flush()

        # If expired / BILLABLE: create a draft Invoice with placeholder parts/labour line items
        if service_type == "BILLABLE":
            invoice_num = f"INV-SRV-{ticket.id:04d}"
            placeholder_subtotal = 6000.0
            placeholder_tax = round(placeholder_subtotal * 0.18, 2)
            placeholder_total = placeholder_subtotal + placeholder_tax

            draft_invoice = Invoice(
                invoice_number=invoice_num,
                customer_id=customer.id,
                order_id=serial_obj.order_id if serial_obj else None,
                ticket_id=ticket.id,
                subtotal=placeholder_subtotal,
                tax=placeholder_tax,
                total=placeholder_total,
                status="Draft"
            )
            db.add(draft_invoice)
            db.flush()

            # Placeholder line items
            item1 = InvoiceItem(
                invoice_id=draft_invoice.id,
                description="Out-of-Warranty Component Repair / Replacement",
                quantity=1,
                unit_price=4500.0,
                total=4500.0
            )
            item2 = InvoiceItem(
                invoice_id=draft_invoice.id,
                description="Technician Site Visit & Labour Service",
                quantity=1,
                unit_price=1500.0,
                total=1500.0
            )
            db.add_all([item1, item2])

            ticket.customer_charge = placeholder_total
            ticket.invoice_id = draft_invoice.id

        db.commit()
        db.refresh(ticket)
        return ticket

    @staticmethod
    def resolve_ticket(db: Session, ticket_id: int) -> ServiceTicket:
        ticket = db.query(ServiceTicket).filter(ServiceTicket.id == ticket_id).first()
        if not ticket:
            raise HTTPException(status_code=404, detail="Service ticket not found.")
        
        ticket.status = "Resolved"
        db.commit()
        db.refresh(ticket)
        return ticket

    @staticmethod
    def customer_confirm_ticket(db: Session, ticket_id: int) -> ServiceTicket:
        ticket = db.query(ServiceTicket).filter(ServiceTicket.id == ticket_id).first()
        if not ticket:
            raise HTTPException(status_code=404, detail="Service ticket not found.")
        
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
