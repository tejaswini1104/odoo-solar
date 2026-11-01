from datetime import date
from typing import List, Optional
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from backend.app.core.csv_export import csv_response
from backend.app.core.database import get_db
from backend.app.services.profitability_service import order_rows
from backend.app.services.report_service import ReportService, resolve_period

# Administrator only: the access rule is applied where the router is included (api_router.py)
router = APIRouter(prefix="/reports", tags=["Director's reports"])

PeriodQuery = Query(default="month", pattern="^(today|week|month|custom)$")


@router.get("/summary")
def summary(
    period: str = PeriodQuery,
    from_date: Optional[date] = Query(default=None, alias="from"),
    to_date: Optional[date] = Query(default=None, alias="to"),
    db: Session = Depends(get_db),
):
    start, end, label = resolve_period(period, from_date, to_date)
    return ReportService.summary(db, start, end, label)


@router.get("/pipeline")
def pipeline(db: Session = Depends(get_db)) -> List[dict]:
    return ReportService.pipeline(db)


@router.get("/summary.csv")
def summary_csv(
    period: str = PeriodQuery,
    from_date: Optional[date] = Query(default=None, alias="from"),
    to_date: Optional[date] = Query(default=None, alias="to"),
    db: Session = Depends(get_db),
):
    start, end, label = resolve_period(period, from_date, to_date)
    data = ReportService.summary(db, start, end, label)
    names = {
        "new_leads": "New leads", "surveys_scheduled": "Surveys scheduled", "quotations_created": "Quotations created",
        "orders_placed": "Orders placed", "deliveries": "Deliveries confirmed", "installations_completed": "Installations completed",
        "tickets_opened": "Repair tickets opened", "tickets_resolved": "Repair tickets resolved or closed",
        "cash_received": "Cash received (verified payments)", "invoices_paid_count": "Invoices paid (count)",
        "invoices_paid_total": "Invoices paid (value)", "stock_spend": "Stock purchases", "technician_pay_paid": "Technician pay paid",
        "jobs": "Jobs completed", "revenue": "Revenue excluding GST", "material_cost": "Material cost", "labour_cost": "Labour cost",
        "profit": "Profit", "margin_pct": "Margin %", "losing_jobs": "Jobs that lost money",
        "orders_awaiting_advance": "Orders awaiting the advance", "jobs_in_progress": "Installations in progress",
        "surveys_open": "Surveys open", "repairs_open": "Repairs open", "subsidies_open": "Subsidy files open",
        "technician_pay_due": "Technician pay owed",
    }
    rows = [["Period", label, f"{start} to {end}"]]
    for section, title in (("activity", "Activity"), ("money", "Money"), ("profit", "Profit on jobs finished"), ("open_now", "Open right now")):
        for key, value in data[section].items():
            rows.append([title, names.get(key, key), value])
    return csv_response(f"summary-{start}-to-{end}.csv", ["Section", "Measure", "Value"], rows)


@router.get("/pipeline.csv")
def pipeline_csv(db: Session = Depends(get_db)):
    rows = ReportService.pipeline(db)
    return csv_response(
        "unfinished-work.csv",
        ["Type", "Reference", "Customer", "Detail", "Stage", "Waiting for", "Days waiting"],
        [[r["kind"], r["reference"], r["customer"], r["detail"], r["stage"], r["next_step"], r["days_waiting"]] for r in rows],
    )


@router.get("/profitability.csv")
def profitability_csv(
    from_date: Optional[date] = Query(default=None, alias="from"),
    to_date: Optional[date] = Query(default=None, alias="to"),
    db: Session = Depends(get_db),
):
    rows = order_rows(db, from_date, to_date)
    return csv_response(
        "profit-per-job.csv",
        ["Order", "Customer", "Package", "Finished on", "Revenue (excl. GST)", "Material cost", "Labour cost", "Labour basis", "Total cost", "Profit", "Margin %", "Paid so far", "Balance due"],
        [[f"SO-{r['order_id']:04d}", r["customer_name"], r["package_name"], r["finished_on"] or "", r["revenue"], r["material_cost"], r["labour_cost"], r["labour_basis"], r["total_cost"], r["profit"], r["profit_margin_pct"], r["amount_paid"], r["balance_due"]] for r in rows],
    )
