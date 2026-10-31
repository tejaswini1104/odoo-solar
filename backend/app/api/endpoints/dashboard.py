from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from backend.app.core.database import get_db
from backend.app.models.models import Lead, SiteSurvey, SalesOrder, ServiceTicket, Warranty
from backend.app.schemas.schemas import DashboardMetricsResponse
from datetime import date

router = APIRouter(prefix="/dashboard", tags=["Dashboard"])

@router.get("", response_model=DashboardMetricsResponse)
def get_dashboard_metrics(db: Session = Depends(get_db)):
    total_leads = db.query(Lead).count()
    pending_surveys = db.query(SiteSurvey).filter(SiteSurvey.status.in_(["Draft", "Submitted"])).count()
    confirmed_orders = db.query(SalesOrder).filter(SalesOrder.status.in_(["Confirmed", "Dispatched", "Completed"])).count()
    open_tickets = db.query(ServiceTicket).filter(ServiceTicket.status.in_(["Open", "Assigned", "In Progress"])).count()
    
    # Active warranties: end_date >= today and status == 'Active'
    active_warranties = db.query(Warranty).filter(
        Warranty.status == "Active",
        Warranty.end_date >= date.today()
    ).count()

    return DashboardMetricsResponse(
        total_leads=total_leads,
        pending_surveys=pending_surveys,
        confirmed_orders=confirmed_orders,
        open_tickets=open_tickets,
        active_warranties=active_warranties
    )
