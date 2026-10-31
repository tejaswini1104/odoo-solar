from typing import List
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from backend.app.core.database import get_db
from backend.app.models.models import SalesOrder, EquipmentSerial
from backend.app.schemas.schemas import OrderProfitabilityResponse

router = APIRouter(prefix="/profitability", tags=["Profitability"])

@router.get("", response_model=List[OrderProfitabilityResponse])
def get_profitability(db: Session = Depends(get_db)):
    # Profitability is reported per completed installation.
    orders = db.query(SalesOrder).filter(
        SalesOrder.status == "Completed"
    ).order_by(SalesOrder.created_at.desc()).all()

    report = []
    for order in orders:
        # Revenue excludes GST: GST is collected for the government, not earned by the company.
        revenue = round(order.quotation.subtotal, 2) if order.quotation else round(order.total_amount / 1.18, 2)

        # Material cost:
        #  - serialized units: the cost of each unit actually dispatched on this order
        #  - bulk items: BOM quantity x cost price (dispatch does not record bulk quantities per order)
        #  - "Installation Service" is labour, already covered by labour_cost, so it is not counted here
        material_cost = 0.0
        dispatched = db.query(EquipmentSerial).filter(EquipmentSerial.order_id == order.id).all()
        for serial in dispatched:
            material_cost += serial.product.cost_price
        for comp in order.package.components:
            if comp.product.is_serialized or comp.product.category == "Installation Service":
                continue
            material_cost += comp.quantity * comp.product.cost_price

        material_cost = round(material_cost, 2)
        labour_cost = round(order.flat_labour_cost, 2)
        total_cost = round(material_cost + labour_cost, 2)
        profit = round(revenue - total_cost, 2)
        margin = round((profit / revenue * 100), 1) if revenue > 0 else 0.0

        report.append(OrderProfitabilityResponse(
            order_id=order.id,
            customer_name=order.customer.name if order.customer else f"Customer #{order.customer_id}",
            package_name=order.package.name if order.package else f"Package #{order.package_id}",
            revenue=revenue,
            material_cost=material_cost,
            labour_cost=labour_cost,
            total_cost=total_cost,
            profit=profit,
            profit_margin_pct=margin,
            status=order.status
        ))

    return report
