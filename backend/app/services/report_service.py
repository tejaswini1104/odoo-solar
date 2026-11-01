from datetime import date, datetime, timedelta
from typing import List, Optional, Tuple
from fastapi import HTTPException
from sqlalchemy import func
from sqlalchemy.orm import Session
from backend.app.core.clock import business_today
from backend.app.core.config import settings
from backend.app.models.models import (
    Installation, Invoice, Lead, Payment, Quotation, SalesOrder, ServiceTicket, SiteSurvey,
    StockPurchase, SubsidyApplication, TechnicianPayout,
)
from backend.app.services.order_service import VERIFIED_STATUSES
from backend.app.services.payroll_service import PayrollService
from backend.app.services.profitability_service import day_bounds, order_rows

PERIOD_LABELS = {"today": "Today", "week": "This week", "month": "This month", "custom": "Custom range"}


def resolve_period(period: str, from_date: Optional[date], to_date: Optional[date]) -> Tuple[date, date, str]:
    today = business_today()
    if period == "today":
        return today, today, "Today"
    if period == "week":
        return today - timedelta(days=today.weekday()), today, "This week (Monday to today)"
    if period == "month":
        return today.replace(day=1), today, "This month"
    if period == "custom":
        if not from_date or not to_date:
            raise HTTPException(status_code=400, detail="Choose a start and an end date for a custom range.")
        if from_date > to_date:
            raise HTTPException(status_code=400, detail="The start date is after the end date.")
        if (to_date - from_date).days > 366:
            raise HTTPException(status_code=400, detail="Please choose a range of a year or less.")
        return from_date, to_date, f"{from_date:%d %b %Y} to {to_date:%d %b %Y}"
    raise HTTPException(status_code=400, detail="Period must be today, week, month or custom.")


def _count(db: Session, column, low, high, *extra) -> int:
    query = db.query(func.count()).select_from(column.class_).filter(column >= low, column <= high)
    for condition in extra:
        query = query.filter(condition)
    return query.scalar() or 0


def _sum(db: Session, expression, *conditions) -> float:
    query = db.query(func.coalesce(func.sum(expression), 0.0))
    for condition in conditions:
        query = query.filter(condition)
    return round(float(query.scalar() or 0.0), 2)


class ReportService:
    @staticmethod
    def summary(db: Session, start: date, end: date, label: str) -> dict:
        low, high = day_bounds(start, end)

        activity = {
            "new_leads": _count(db, Lead.created_at, low, high),
            "surveys_scheduled": _count(db, SiteSurvey.created_at, low, high, SiteSurvey.scheduled_date.isnot(None)),
            "quotations_created": _count(db, Quotation.created_at, low, high),
            "orders_placed": _count(db, SalesOrder.created_at, low, high),
            "deliveries": _count(db, SalesOrder.delivered_at, low, high),
            "installations_completed": _count(db, Installation.finish_time, low, high, Installation.status == "Completed"),
            "tickets_opened": _count(db, ServiceTicket.created_at, low, high),
            "tickets_resolved": _count(
                db, ServiceTicket.updated_at, low, high,
                ServiceTicket.status.in_(["Resolved", "Customer Confirmed", "Closed"]),
            ),
        }

        paid_invoices = db.query(Invoice).filter(Invoice.status == "Paid", Invoice.updated_at >= low, Invoice.updated_at <= high).all()
        money = {
            "cash_received": _sum(
                db, Payment.amount,
                Payment.status.in_(VERIFIED_STATUSES), Payment.updated_at >= low, Payment.updated_at <= high,
            ),
            "invoices_paid_count": len(paid_invoices),
            "invoices_paid_total": round(sum(i.total for i in paid_invoices), 2),
            "stock_spend": _sum(db, StockPurchase.total_cost, StockPurchase.purchased_on >= start, StockPurchase.purchased_on <= end),
            "technician_pay_paid": _sum(db, TechnicianPayout.amount, TechnicianPayout.paid_on >= low, TechnicianPayout.paid_on <= high),
        }

        rows = order_rows(db, start, end)
        revenue = round(sum(r["revenue"] for r in rows), 2)
        profit = round(sum(r["profit"] for r in rows), 2)
        profit_block = {
            "jobs": len(rows),
            "revenue": revenue,
            "material_cost": round(sum(r["material_cost"] for r in rows), 2),
            "labour_cost": round(sum(r["labour_cost"] for r in rows), 2),
            "profit": profit,
            "margin_pct": round(profit / revenue * 100, 1) if revenue > 0 else 0.0,
            "losing_jobs": sum(1 for r in rows if r["profit"] < 0),
        }

        pay_due = PayrollService.summary(db, date(2000, 1, 1), business_today())
        open_now = {
            "orders_awaiting_advance": db.query(SalesOrder).filter(SalesOrder.status == "Pending Confirmation").count(),
            "jobs_in_progress": db.query(Installation).filter(Installation.status != "Completed").count(),
            "surveys_open": db.query(SiteSurvey).filter(SiteSurvey.status.in_(["Scheduled", "Draft", "Submitted"])).count(),
            "repairs_open": db.query(ServiceTicket).filter(ServiceTicket.status != "Closed").count(),
            "subsidies_open": db.query(SubsidyApplication).filter(SubsidyApplication.status.notin_(["Disbursed", "Rejected"])).count(),
            "technician_pay_due": round(sum(r["amount_due"] for r in pay_due), 2),
        }

        return {
            "period": {"label": label, "from": start, "to": end},
            "activity": activity,
            "money": money,
            "profit": profit_block,
            "open_now": open_now,
        }

    @staticmethod
    def pipeline(db: Session) -> List[dict]:
        """Everything that is not finished, with what it is waiting for, oldest first."""
        now = datetime.utcnow()
        rows: List[dict] = []

        def add(kind, reference, customer, detail, stage, next_step, since):
            rows.append({
                "kind": kind, "reference": reference, "customer": customer, "detail": detail,
                "stage": stage, "next_step": next_step,
                "days_waiting": max((now - since).days, 0) if since else 0,
            })

        for survey in db.query(SiteSurvey).filter(SiteSurvey.status.in_(["Scheduled", "Draft", "Submitted"])).all():
            who = survey.customer.name if survey.customer else f"Customer #{survey.customer_id}"
            if survey.status == "Scheduled":
                add("Survey", f"SURV-{survey.id:04d}", who, f"Technician: {survey.technician_name}", "Survey scheduled",
                    f"{survey.technician_name} visits on {survey.scheduled_date}", survey.created_at)
            else:
                add("Survey", f"SURV-{survey.id:04d}", who, f"Technician: {survey.technician_name}", "Survey awaiting approval",
                    "Approve the survey", survey.updated_at)

        for survey in db.query(SiteSurvey).filter(SiteSurvey.status == "Approved").all():
            if not survey.quotations:
                who = survey.customer.name if survey.customer else f"Customer #{survey.customer_id}"
                add("Survey", f"SURV-{survey.id:04d}", who, f"Recommends {survey.recommended_capacity:g} kW", "Survey approved",
                    "Create the quotation", survey.updated_at)

        for quote in db.query(Quotation).filter(Quotation.status.in_(["Draft", "Sent"])).all():
            who = quote.customer.name if quote.customer else f"Customer #{quote.customer_id}"
            detail = f"{quote.package.name}, total ₹{quote.total:,.0f}"
            if quote.status == "Draft":
                add("Quotation", f"QTN-{quote.id:05d}", who, detail, "Quotation drafted", "Send it to the customer", quote.created_at)
            else:
                add("Quotation", f"QTN-{quote.id:05d}", who, detail, "Waiting for the customer to accept", "Customer accepts in the portal", quote.updated_at)

        for order in db.query(SalesOrder).filter(SalesOrder.status != "Cancelled").all():
            payments = order.payments
            verified = round(sum(p.amount for p in payments if p.status in VERIFIED_STATUSES), 2)
            pending = round(sum(p.amount for p in payments if p.status == "Pending Verification"), 2)
            required = round(order.total_amount * settings.ADVANCE_PERCENT / 100, 2)
            who = order.customer.name if order.customer else f"Customer #{order.customer_id}"
            detail = f"{order.package.name}, paid ₹{verified:,.0f} of ₹{order.total_amount:,.0f}"
            ref = f"SO-{order.id:04d}"
            if order.status == "Pending Confirmation":
                if verified + 0.005 >= required:
                    add("Order", ref, who, detail, "Advance verified", "Sales confirm the order", order.updated_at)
                elif pending > 0:
                    add("Order", ref, who, detail, "Payment waiting for verification", f"Sales verify the ₹{pending:,.0f} the customer reported", order.updated_at)
                else:
                    add("Order", ref, who, detail, "Waiting for the advance", f"Customer pays at least ₹{required:,.0f}", order.updated_at)
            elif order.status == "Confirmed":
                add("Order", ref, who, detail, "Waiting for dispatch", "Warehouse assigns serial numbers and dispatches", order.updated_at)
            elif order.status == "Dispatched":
                tech = order.installation.technician.name if order.installation and order.installation.technician else "the technician"
                if not order.delivered_at:
                    add("Order", ref, who, detail, "Dispatched, awaiting delivery", "Warehouse confirms delivery", order.updated_at)
                else:
                    add("Order", ref, who, detail, "Waiting for installation", f"{tech} installs and completes the job", order.delivered_at)
            elif order.status == "Completed":
                balance = round(order.total_amount - verified, 2)
                if balance > 0.005:
                    add("Order", ref, who, detail, "Balance outstanding", f"Customer pays ₹{balance:,.0f}", order.updated_at)

        for ticket in db.query(ServiceTicket).filter(ServiceTicket.status != "Closed").all():
            who = ticket.customer.name if ticket.customer else f"Customer #{ticket.customer_id}"
            detail = f"{ticket.title} ({ticket.service_type})"
            steps = {
                "Resolved": ("Waiting for the customer to confirm", "Customer confirms the fix"),
                "Customer Confirmed": ("Customer confirmed", "Support closes the ticket"),
            }
            stage, nxt = steps.get(ticket.status, ("Repair open", "Support resolves the ticket"))
            add("Repair", f"TCK-{ticket.id:04d}", who, detail, stage, nxt, ticket.updated_at)

        for invoice in db.query(Invoice).filter(Invoice.ticket_id.isnot(None), Invoice.status == "Sent").all():
            who = invoice.customer.name if invoice.customer else f"Customer #{invoice.customer_id}"
            add("Invoice", invoice.invoice_number, who, f"Repair invoice, ₹{invoice.total:,.0f}", "Repair invoice unpaid", "Customer pays", invoice.updated_at)

        for sub in db.query(SubsidyApplication).filter(SubsidyApplication.status.notin_(["Disbursed", "Rejected"])).all():
            who = sub.customer.name if sub.customer else f"Customer #{sub.customer_id}"
            nxt = {
                "Documents pending": "Collect the customer's documents",
                "Documents collected": "Submit the application",
                "Applied": "Wait for approval",
                "Approved": "Wait for the subsidy to be paid",
            }.get(sub.status, "")
            add("Subsidy", f"SUB-{sub.id:04d}", who, f"Order SO-{sub.order_id:04d}", f"Subsidy: {sub.status}", nxt, sub.updated_at)

        rows.sort(key=lambda r: r["days_waiting"], reverse=True)
        return rows
