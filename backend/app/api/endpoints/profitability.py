from datetime import date
from typing import List, Optional
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from backend.app.core.database import get_db
from backend.app.schemas.schemas import OrderProfitabilityResponse
from backend.app.services.profitability_service import order_rows

router = APIRouter(prefix="/profitability", tags=["Profitability"])


@router.get("", response_model=List[OrderProfitabilityResponse])
def get_profitability(
    from_date: Optional[date] = Query(default=None, alias="from"),
    to_date: Optional[date] = Query(default=None, alias="to"),
    db: Session = Depends(get_db),
):
    """Profit per completed order. With `from` and `to`, only jobs finished in that range."""
    return order_rows(db, from_date, to_date)
