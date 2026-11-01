from datetime import date
from typing import List, Optional
from sqlalchemy import func
from sqlalchemy.orm import Session
from backend.app.core.clock import business_date, utc_bounds
from backend.app.models.models import EquipmentSerial, SalesOrder, StockPurchaseItem
from backend.app.services.order_service import VERIFIED_STATUSES


def job_hours(installation) -> Optional[float]:
    """Hours worked on a job, from the start and finish times the technician recorded."""
    if installation and installation.start_time and installation.finish_time:
        hours = (installation.finish_time - installation.start_time).total_seconds() / 3600
        if hours > 0:
            return round(hours, 2)
    return None


def day_bounds(start: Optional[date], end: Optional[date]):
    """Turn an inclusive range of company-clock days into datetimes the database can compare against."""
    return utc_bounds(start, end)


def average_unit_costs(db: Session) -> dict:
    """What each product actually cost: the average price paid across the stock purchases recorded for it."""
    rows = (
        db.query(
            StockPurchaseItem.product_id,
            func.sum(StockPurchaseItem.quantity * StockPurchaseItem.unit_cost),
            func.sum(StockPurchaseItem.quantity),
        )
        .group_by(StockPurchaseItem.product_id)
        .all()
    )
    return {pid: spent / qty for pid, spent, qty in rows if qty}


def order_rows(db: Session, start: Optional[date] = None, end: Optional[date] = None) -> List[dict]:
    """Profit for each completed order, optionally only those whose installation finished in the date range.

    Revenue excludes GST. Material is the cost of the serialized units dispatched on the order plus the bulk BOM
    items, priced at the average paid in recorded stock purchases (list cost price for products never purchased). Labour is the hours recorded on the job at the technician's hourly rate, or the order's flat labour
    cost when no hours were recorded.
    """
    orders = db.query(SalesOrder).filter(SalesOrder.status == "Completed").order_by(SalesOrder.created_at.desc()).all()
    low, high = day_bounds(start, end)

    actual = average_unit_costs(db)

    def unit_cost(product) -> float:
        # The price paid to suppliers when purchases are recorded, otherwise the product's list cost price
        return actual.get(product.id, product.cost_price)

    rows = []
    for order in orders:
        installation = order.installation
        finished = installation.finish_time if installation else None
        if low and (finished is None or finished < low):
            continue
        if high and (finished is None or finished > high):
            continue

        revenue = round(order.quotation.subtotal, 2) if order.quotation else round(order.total_amount / 1.18, 2)

        material_cost = 0.0
        for serial in db.query(EquipmentSerial).filter(EquipmentSerial.order_id == order.id).all():
            material_cost += unit_cost(serial.product)
        for comp in order.package.components:
            # "Installation Service" is labour, which is counted separately below
            if comp.product.is_serialized or comp.product.category == "Installation Service":
                continue
            material_cost += comp.quantity * unit_cost(comp.product)
        material_cost = round(material_cost, 2)

        hours = job_hours(installation)
        if hours is not None and installation.technician is not None:
            labour_cost = round(hours * installation.technician.hourly_rate, 2)
            basis = f"{hours:g} h at ₹{installation.technician.hourly_rate:g}/h"
        else:
            labour_cost = round(order.flat_labour_cost, 2)
            basis = "flat rate (no hours recorded)"

        paid = round(sum(p.amount for p in order.payments if p.status in VERIFIED_STATUSES), 2)
        total_cost = round(material_cost + labour_cost, 2)
        profit = round(revenue - total_cost, 2)
        rows.append({
            "order_id": order.id,
            "customer_name": order.customer.name if order.customer else f"Customer #{order.customer_id}",
            "package_name": order.package.name if order.package else f"Package #{order.package_id}",
            "revenue": revenue,
            "amount_paid": paid,
            "balance_due": round(max(order.total_amount - paid, 0.0), 2),
            "material_cost": material_cost,
            "labour_cost": labour_cost,
            "total_cost": total_cost,
            "profit": profit,
            "profit_margin_pct": round(profit / revenue * 100, 1) if revenue > 0 else 0.0,
            "status": order.status,
            "finished_on": business_date(finished),
            "labour_hours": hours,
            "labour_basis": basis,
        })
    return rows
