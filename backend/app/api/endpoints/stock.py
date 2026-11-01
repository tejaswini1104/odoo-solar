from datetime import date
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, Response
from sqlalchemy.orm import Session
from backend.app.api.deps import get_current_user
from backend.app.core.csv_export import csv_response
from backend.app.core.database import get_db
from backend.app.core.qr import qr_png, warranty_url
from backend.app.models.models import EquipmentSerial, Product, StockPurchase, User
from backend.app.services.stock_service import PurchaseIn, StockService

# Access by role is set where this router is included (api_router.py).
router = APIRouter(prefix="/stock", tags=["Stock purchases"])


def _out(purchase: StockPurchase) -> dict:
    return {
        "id": purchase.id,
        "supplier": purchase.supplier,
        "invoice_reference": purchase.invoice_reference,
        "purchased_on": purchase.purchased_on,
        "total_cost": purchase.total_cost,
        "created_at": purchase.created_at,
        "items": [
            {
                "product_id": i.product_id,
                "product_name": i.product.name,
                "category": i.product.category,
                "quantity": i.quantity,
                "unit_cost": i.unit_cost,
                "line_total": round(i.quantity * i.unit_cost, 2),
            }
            for i in purchase.items
        ],
    }


@router.get("/products")
def purchasable_products(db: Session = Depends(get_db)) -> List[dict]:
    """The products that can be bought, so the receiving form knows which ones need serial numbers."""
    return [
        {"id": p.id, "name": p.name, "category": p.category, "unit": p.unit, "is_serialized": p.is_serialized, "cost_price": p.cost_price}
        for p in db.query(Product).order_by(Product.category, Product.name).all()
    ]


@router.get("/serials")
def list_serials(status: str = Query("In Stock", max_length=50), db: Session = Depends(get_db)) -> List[dict]:
    """Serial-numbered units, newest first, for printing QR labels. Use status=all for every unit."""
    query = db.query(EquipmentSerial).join(Product)
    if status.lower() != "all":
        query = query.filter(EquipmentSerial.status == status)
    units = query.order_by(EquipmentSerial.id.desc()).limit(500).all()
    return [
        {"serial_number": u.serial_number, "product_name": u.product.name, "category": u.product.category, "status": u.status}
        for u in units
    ]


@router.get("/qr.png")
def serial_qr(serial: str = Query(min_length=3, max_length=100), db: Session = Depends(get_db)):
    """The QR label image for one unit. Scanning it opens the warranty check and carries the serial number."""
    serial = serial.strip()
    if not db.query(EquipmentSerial).filter(EquipmentSerial.serial_number == serial).first():
        raise HTTPException(status_code=404, detail="No unit with that serial number.")
    return Response(content=qr_png(serial), media_type="image/png", headers={"Cache-Control": "private, max-age=3600"})


@router.get("/purchases")
def list_purchases(
    from_date: Optional[date] = Query(default=None, alias="from"),
    to_date: Optional[date] = Query(default=None, alias="to"),
    db: Session = Depends(get_db),
) -> List[dict]:
    query = db.query(StockPurchase)
    if from_date:
        query = query.filter(StockPurchase.purchased_on >= from_date)
    if to_date:
        query = query.filter(StockPurchase.purchased_on <= to_date)
    return [_out(p) for p in query.order_by(StockPurchase.purchased_on.desc(), StockPurchase.id.desc()).limit(300).all()]


@router.post("/purchases", status_code=201)
def receive_stock(payload: PurchaseIn, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return _out(StockService.receive(db, payload, user))


@router.get("/purchases.csv")
def purchases_csv(
    from_date: Optional[date] = Query(default=None, alias="from"),
    to_date: Optional[date] = Query(default=None, alias="to"),
    db: Session = Depends(get_db),
):
    query = db.query(StockPurchase)
    if from_date:
        query = query.filter(StockPurchase.purchased_on >= from_date)
    if to_date:
        query = query.filter(StockPurchase.purchased_on <= to_date)
    rows = []
    for purchase in query.order_by(StockPurchase.purchased_on.desc()).all():
        for item in purchase.items:
            rows.append([purchase.purchased_on, purchase.supplier, purchase.invoice_reference or "", item.product.name, item.quantity, item.unit_cost, round(item.quantity * item.unit_cost, 2)])
    return csv_response("stock-purchases.csv", ["Date", "Supplier", "Invoice", "Product", "Quantity", "Unit cost", "Line total"], rows)
