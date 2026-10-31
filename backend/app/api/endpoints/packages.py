from typing import List
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from backend.app.core.database import get_db
from backend.app.models.models import SolarPackage, PackageComponent, Product
from backend.app.schemas.schemas import SolarPackageResponse, BOMResponse, BOMItemResponse

router = APIRouter(prefix="/packages", tags=["Packages & BOM"])

@router.get("", response_model=List[SolarPackageResponse])
def list_packages(db: Session = Depends(get_db)):
    return db.query(SolarPackage).order_by(SolarPackage.capacity_kw.asc(), SolarPackage.system_type.asc()).all()

@router.get("/{id}", response_model=SolarPackageResponse)
def get_package(id: int, db: Session = Depends(get_db)):
    pkg = db.query(SolarPackage).filter(SolarPackage.id == id).first()
    if not pkg:
        raise HTTPException(status_code=404, detail="Solar package not found")
    return pkg

@router.get("/{id}/bom", response_model=BOMResponse)
def get_package_bom(id: int, db: Session = Depends(get_db)):
    pkg = db.query(SolarPackage).filter(SolarPackage.id == id).first()
    if not pkg:
        raise HTTPException(status_code=404, detail="Solar package not found")

    items = []
    subtotal = 0.0

    for comp in pkg.components:
        product = comp.product
        item_total = comp.quantity * product.unit_price
        subtotal += item_total
        items.append(
            BOMItemResponse(
                product_id=product.id,
                product_name=product.name,
                category=product.category,
                unit=product.unit,
                quantity=comp.quantity,
                cost_price=product.cost_price,
                unit_price=product.unit_price,
                total_price=item_total,
                is_serialized=product.is_serialized
            )
        )

    tax = round(subtotal * 0.18, 2)
    total = round(subtotal + tax, 2)

    return BOMResponse(
        package_id=pkg.id,
        package_name=pkg.name,
        capacity_kw=pkg.capacity_kw,
        system_type=pkg.system_type,
        items=items,
        subtotal=subtotal,
        tax=tax,
        total=total
    )
