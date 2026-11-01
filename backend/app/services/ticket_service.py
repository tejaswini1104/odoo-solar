from datetime import date, datetime
from typing import Optional
from dateutil.relativedelta import relativedelta
from sqlalchemy.orm import Session
from fastapi import HTTPException, status
from backend.app.models.models import (
    ServiceTicket, Warranty, EquipmentSerial, Invoice, InvoiceItem, Customer, InventoryItem, Technician
)
from backend.app.core.clock import business_today
from backend.app.core.config import settings
from backend.app.core.roles import SUPPORT, WAREHOUSE
from backend.app.schemas.schemas import ServiceTicketCreate
from backend.app.services.notification_service import notify

class TicketService:
    @staticmethod
    def create_ticket(db: Session, ticket_in: ServiceTicketCreate) -> ServiceTicket:
        customer = db.query(Customer).filter(Customer.id == ticket_in.customer_id).first()
        if not customer:
            raise HTTPException(status_code=404, detail=f"Customer #{ticket_in.customer_id} not found.")

        if ticket_in.warranty_id is not None:
            warranty, product, order, equipment_label, repair_label = TicketService._panel_claim(db, customer, ticket_in.warranty_id)
            installation_id = warranty.installation_id
        else:
            warranty, product, order, equipment_label, repair_label, installation_id = TicketService._serial_claim(
                db, customer, ticket_in.equipment_serial.strip()
            )

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
            equipment_serial=equipment_label,
            installation_id=installation_id,
            warranty_id=ticket_in.warranty_id,
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
            labour = round(settings.SERVICE_LABOUR_CHARGE, 2)
            part = round(product.unit_price, 2)
            subtotal = round(part + labour, 2)
            tax = round(subtotal * settings.GST_PERCENT / 100, 2)
            total = round(subtotal + tax, 2)

            draft_invoice = Invoice(
                invoice_number=f"INV-SRV-{ticket.id:04d}",
                customer_id=customer.id,
                order_id=order.id,
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
                    description=f"Repair or replacement: {repair_label}",
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
            f"{service_type.title()} repair for {equipment_label} ({customer.name}).",
            link="tickets", role=SUPPORT,
        )
        # A technician is sent automatically. With none on the books the ticket stays Open for support to sort out.
        tech = TicketService._least_busy_technician(db)
        if tech:
            TicketService._assign(db, ticket, tech)
        db.commit()
        db.refresh(ticket)
        return ticket

    @staticmethod
    def _serial_claim(db: Session, customer: Customer, serial_str: str):
        """A claim on a serial-numbered unit. Returns (warranty, product, order, equipment label, repair label, installation id)."""
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
        if serial_obj.status == "Replaced":
            raise HTTPException(
                status_code=400,
                detail=f"Unit '{serial_str}' was replaced and is no longer at the customer's site. Raise the ticket on the replacement unit.",
            )
        # Still on the truck: the warranty has not started, so this must not be treated as an expired warranty
        if order.status == "Dispatched" and order.delivered_at is None:
            raise HTTPException(
                status_code=400,
                detail=f"Serial number '{serial_str}' was dispatched but is not marked delivered yet, so its warranty has not started.",
            )

        # Look up warranty for this serial number
        warranty = db.query(Warranty).filter(
            Warranty.serial_number == serial_str
        ).order_by(Warranty.created_at.desc()).first()
        product = serial_obj.product
        return (
            warranty, product, order, serial_str,
            f"{product.name} (serial {serial_str})", serial_obj.installation_id,
        )

    @staticmethod
    def _panel_claim(db: Session, customer: Customer, warranty_id: int):
        """A claim on the solar panels, which are warranted in bulk for the order and have no serial numbers."""
        warranty = db.query(Warranty).filter(Warranty.id == warranty_id).first()
        if not warranty or warranty.warranty_type != "bulk":
            raise HTTPException(status_code=404, detail="That panel warranty was not found.")
        if warranty.customer_id != customer.id:
            raise HTTPException(status_code=403, detail="This warranty belongs to a different customer.")
        order = warranty.order
        product = warranty.product
        return (
            warranty, product, order, f"PANELS-SO{order.id:04d}",
            f"{product.name} (one panel, order SO-{order.id:04d})",
        )

    @staticmethod
    def _get(db: Session, ticket_id: int) -> ServiceTicket:
        ticket = db.query(ServiceTicket).filter(ServiceTicket.id == ticket_id).first()
        if not ticket:
            raise HTTPException(status_code=404, detail="Service ticket not found.")
        return ticket

    @staticmethod
    def assign_technician(db: Session, ticket_id: int, technician_id: int) -> ServiceTicket:
        """Send a technician to the customer. Allowed until the site visit has been recorded."""
        ticket = TicketService._get(db, ticket_id)
        if ticket.status not in ("Open", "Assigned"):
            raise HTTPException(status_code=400, detail=f"A technician can only be assigned before the site visit. This ticket is '{ticket.status}'.")
        tech = db.query(Technician).filter(Technician.id == technician_id).first()
        if not tech:
            raise HTTPException(status_code=404, detail="Technician not found.")
        TicketService._assign(db, ticket, tech)
        return TicketService._finish(db, ticket)

    @staticmethod
    def _assign(db: Session, ticket: ServiceTicket, tech: Technician) -> None:
        ticket.technician_id = tech.id
        ticket.status = "Assigned"
        customer = ticket.customer
        notify(
            db, f"Repair visit assigned: TCK-{ticket.id:04d}",
            f"{ticket.title} at {customer.address}, {customer.city} ({customer.name}, {customer.phone}).",
            link="repairs", technician_id=tech.id,
        )
        notify(
            db, f"Technician assigned to TCK-{ticket.id:04d}",
            f"{tech.name} will visit you about: {ticket.title}.",
            link="support", customer_id=ticket.customer_id,
        )

    @staticmethod
    def _least_busy_technician(db: Session) -> Optional[Technician]:
        """The technician with the fewest repair tickets still open; the lowest id breaks a tie."""
        finished = ("Resolved", "Customer Confirmed", "Closed")
        best, best_load = None, None
        for tech in db.query(Technician).order_by(Technician.id).all():
            load = db.query(ServiceTicket).filter(
                ServiceTicket.technician_id == tech.id, ServiceTicket.status.notin_(finished)
            ).count()
            if best is None or load < best_load:
                best, best_load = tech, load
        return best

    @staticmethod
    def record_inspection(db: Session, ticket_id: int, needs_replacement: bool, notes: Optional[str]) -> ServiceTicket:
        """The technician's site visit. Under warranty the work goes ahead; otherwise the customer is quoted first."""
        ticket = TicketService._get(db, ticket_id)
        if ticket.status != "Assigned" or not ticket.technician_id:
            raise HTTPException(status_code=400, detail="Assign a technician first. The site visit can only be recorded on an assigned ticket.")
        if needs_replacement and ticket.warranty_id is None:
            unit = db.query(EquipmentSerial).filter(EquipmentSerial.serial_number == ticket.equipment_serial).first()
            if not unit:
                raise HTTPException(status_code=404, detail="The faulty unit is no longer registered.")

        ticket.needs_replacement = needs_replacement
        ticket.inspection_notes = notes
        ref = f"TCK-{ticket.id:04d}"
        verdict = "needs a replacement unit" if needs_replacement else "can be repaired on site"
        notify(
            db, f"Technician's report on {ref}",
            f"{ticket.technician.name if ticket.technician else 'The technician'} found it {verdict}." + (f" {notes}" if notes else ""),
            link="tickets", role=SUPPORT,
        )

        if ticket.service_type == "COVERED":
            TicketService._work_approved(db, ticket)
            return TicketService._finish(db, ticket)

        # Out of warranty: re-price from what the technician found, then ask the customer
        invoice = ticket.invoice
        if invoice and invoice.status == "Draft":
            if not needs_replacement:
                invoice.items = [i for i in invoice.items if not i.description.startswith("Repair or replacement")]
                subtotal = round(sum(i.total for i in invoice.items), 2)
                invoice.subtotal = subtotal
                invoice.tax = round(subtotal * settings.GST_PERCENT / 100, 2)
                invoice.total = round(subtotal + invoice.tax, 2)
                ticket.customer_charge = invoice.total
        ticket.quote_status = "Pending"
        ticket.status = "Quotation Sent"
        notify(
            db, f"Quotation for repair {ref}",
            f"Total ₹{ticket.customer_charge:,.2f} including GST. Please approve or reject it in Support.",
            link="support", customer_id=ticket.customer_id,
        )
        return TicketService._finish(db, ticket)

    @staticmethod
    def _work_approved(db: Session, ticket: ServiceTicket) -> None:
        """The repair may go ahead (covered, or the customer approved the quotation). A replacement goes to the warehouse."""
        if ticket.needs_replacement:
            ticket.status = "Awaiting Dispatch"
            what = "one solar panel" if ticket.warranty_id is not None else f"a replacement for {ticket.equipment_serial}"
            notify(
                db, f"Replacement to dispatch: TCK-{ticket.id:04d}",
                f"Send {what} to {ticket.customer.name}, {ticket.customer.address}, {ticket.customer.city}.",
                link="dispatch", role=WAREHOUSE,
            )
        else:
            ticket.status = "In Progress"

    @staticmethod
    def _finish(db: Session, ticket: ServiceTicket) -> ServiceTicket:
        db.commit()
        db.refresh(ticket)
        return ticket

    @staticmethod
    def decide_quote(db: Session, ticket_id: int, approved: bool) -> ServiceTicket:
        ticket = TicketService._get(db, ticket_id)
        if ticket.status != "Quotation Sent" or ticket.quote_status != "Pending":
            raise HTTPException(status_code=400, detail="There is no quotation waiting for a decision on this ticket.")
        ref = f"TCK-{ticket.id:04d}"
        if approved:
            ticket.quote_status = "Approved"
            TicketService._work_approved(db, ticket)
            if ticket.technician_id:
                notify(db, f"Quotation approved: {ref}", "The customer approved the repair. Carry on.", link="repairs", technician_id=ticket.technician_id)
            notify(db, f"Quotation approved: {ref}", "Repair approved by the customer.", link="tickets", role=SUPPORT)
        else:
            # Nothing was done, so nothing is charged: the draft invoice is withdrawn and the ticket closes
            ticket.quote_status = "Rejected"
            ticket.status = "Closed"
            invoice = ticket.invoice
            ticket.invoice_id = None
            ticket.customer_charge = 0.0
            if invoice and invoice.status == "Draft":
                db.flush()
                db.delete(invoice)
            notify(db, f"Quotation rejected: {ref}", "The customer declined the repair. The ticket is closed with no charge.", link="tickets", role=SUPPORT)
        return TicketService._finish(db, ticket)

    @staticmethod
    def dispatch_replacement(db: Session, ticket_id: int, serial_number: Optional[str]) -> ServiceTicket:
        """Send out the replacement unit. Stock is taken now; the unit is fitted and registered when the ticket is resolved."""
        ticket = TicketService._get(db, ticket_id)
        if not ticket.needs_replacement:
            raise HTTPException(status_code=400, detail="The technician did not ask for a replacement on this ticket.")
        if ticket.status != "Awaiting Dispatch":
            raise HTTPException(
                status_code=400,
                detail=f"A replacement can be dispatched once the work is approved. This ticket is '{ticket.status}'.",
            )

        if ticket.warranty_id is not None:
            # Panels have no serial numbers: one panel leaves the stock
            warranty = db.query(Warranty).filter(Warranty.id == ticket.warranty_id).first()
            product_id = warranty.product_id
        else:
            sn = (serial_number or "").strip()
            if not sn:
                raise HTTPException(status_code=422, detail="Choose the serial number of the replacement unit being sent.")
            old = db.query(EquipmentSerial).filter(EquipmentSerial.serial_number == ticket.equipment_serial).first()
            if not old:
                raise HTTPException(status_code=404, detail="The faulty unit is no longer registered.")
            new = db.query(EquipmentSerial).filter(EquipmentSerial.serial_number == sn).first()
            if not new:
                raise HTTPException(status_code=404, detail=f"Replacement serial '{sn}' does not exist in inventory.")
            if new.product_id != old.product_id:
                raise HTTPException(status_code=400, detail=f"'{sn}' is a {new.product.name}. The replacement must be a {old.product.name}.")
            if new.status != "In Stock":
                raise HTTPException(status_code=400, detail=f"Replacement serial '{sn}' is not in stock (status '{new.status}').")
            new.status = "Dispatched"
            ticket.dispatch_serial = new.serial_number
            product_id = new.product_id

        inventory = db.query(InventoryItem).filter(InventoryItem.product_id == product_id).first()
        if inventory:
            inventory.quantity_on_hand = max(0, inventory.quantity_on_hand - 1)

        ticket.dispatched_at = datetime.utcnow()
        ticket.status = "Dispatched"
        ref = f"TCK-{ticket.id:04d}"
        notify(db, f"Replacement on its way: {ref}", "Your replacement unit has been dispatched. Our technician will fit it.", link="support", customer_id=ticket.customer_id)
        notify(db, f"Replacement dispatched: {ref}", "The warehouse has sent the unit. Once it is fitted, resolve the ticket.", link="tickets", role=SUPPORT)
        if ticket.technician_id:
            notify(db, f"Replacement dispatched: {ref}", "Fit the replacement at the customer's site, then tell Support.", link="repairs", technician_id=ticket.technician_id)
        return TicketService._finish(db, ticket)

    @staticmethod
    def resolve_ticket(db: Session, ticket_id: int) -> ServiceTicket:
        ticket = TicketService._get(db, ticket_id)

        if ticket.status in ("Resolved", "Customer Confirmed", "Closed"):
            raise HTTPException(status_code=400, detail=f"This ticket is already '{ticket.status}'.")
        if ticket.status in ("Open", "Assigned"):
            raise HTTPException(status_code=400, detail="Assign a technician and record the site visit before resolving.")
        if ticket.status == "Quotation Sent":
            raise HTTPException(status_code=400, detail="The customer has not approved the quotation yet.")
        if ticket.status == "Awaiting Dispatch":
            raise HTTPException(status_code=400, detail="The warehouse has not dispatched the replacement unit yet.")

        if ticket.dispatch_serial:
            TicketService._swap_unit(db, ticket, ticket.dispatch_serial)
        ticket.status = "Resolved"
        note = "Please confirm that everything works so we can close it."
        if ticket.replacement_serial:
            note = f"Your unit was replaced (new serial {ticket.replacement_serial}). {note}"
        notify(
            db, f"Your repair ticket TCK-{ticket.id:04d} was marked fixed", note,
            link="support", customer_id=ticket.customer_id,
        )

        # An out-of-warranty repair is billed as soon as it is done. Support can edit the draft until then.
        invoice = ticket.invoice
        if invoice and invoice.status == "Draft":
            invoice.status = "Sent"
            notify(
                db, f"Invoice {invoice.invoice_number} for your repair",
                f"Total ₹{invoice.total:,.2f} including GST. You can pay it from Invoices.",
                link="invoices", customer_id=ticket.customer_id,
            )
        db.commit()
        db.refresh(ticket)
        return ticket

    @staticmethod
    def _swap_unit(db: Session, ticket: ServiceTicket, new_serial: str) -> None:
        """Fit the dispatched unit in place of the faulty one: location and a warranty for the new unit. Stock left at dispatch."""
        old = db.query(EquipmentSerial).filter(EquipmentSerial.serial_number == ticket.equipment_serial).first()
        if not old:
            raise HTTPException(status_code=404, detail="The faulty unit is no longer registered.")
        new = db.query(EquipmentSerial).filter(EquipmentSerial.serial_number == new_serial).first()
        if not new:
            raise HTTPException(status_code=404, detail=f"Replacement serial '{new_serial}' does not exist in inventory.")
        if new.product_id != old.product_id:
            raise HTTPException(
                status_code=400,
                detail=f"'{new_serial}' is a {new.product.name}. The replacement must be a {old.product.name}.",
            )
        if new.status != "Dispatched":
            raise HTTPException(status_code=400, detail=f"Replacement serial '{new_serial}' was not dispatched for this repair (status '{new.status}').")

        today = business_today()
        old_warranty = db.query(Warranty).filter(
            Warranty.serial_number == old.serial_number
        ).order_by(Warranty.created_at.desc()).first()

        old.status = "Replaced"
        if old_warranty:
            old_warranty.status = "Replaced"
        new.status = "Installed"
        new.order_id = old.order_id
        new.installation_id = old.installation_id

        # Under warranty the new unit carries on with the original cover, with the same start and end dates. A paid
        # replacement starts a full new warranty today.
        if ticket.service_type == "COVERED" and old_warranty:
            months, start_date, end_date = old_warranty.duration_months, old_warranty.start_date, old_warranty.end_date
        else:
            months = settings.WARRANTY_DURATION_MONTHS.get(new.product.category, 24)
            start_date = today
            end_date = today + relativedelta(months=months)
        if old_warranty:
            db.add(Warranty(
                customer_id=old_warranty.customer_id,
                installation_id=old_warranty.installation_id,
                order_id=old_warranty.order_id,
                product_id=new.product_id,
                serial_number=new.serial_number,
                warranty_type="serialized",
                duration_months=months,
                start_date=start_date,
                end_date=end_date,
                status="Active" if end_date >= date.today() else "Expired",
            ))
        ticket.replacement_serial = new.serial_number

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
