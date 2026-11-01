from datetime import date, datetime, time, timedelta
from typing import Optional, Tuple
from backend.app.core.config import settings


def _offset() -> timedelta:
    return timedelta(minutes=settings.BUSINESS_UTC_OFFSET_MINUTES)


def business_today() -> date:
    """Today's date on the company's clock, whatever time zone the server itself is set to."""
    return (datetime.utcnow() + _offset()).date()


def business_date(utc_moment: Optional[datetime]) -> Optional[date]:
    """The company-clock date of a moment stored in UTC."""
    return (utc_moment + _offset()).date() if utc_moment else None


def utc_bounds(start: Optional[date], end: Optional[date]) -> Tuple[Optional[datetime], Optional[datetime]]:
    """Turn an inclusive range of company-clock days into the UTC moments the database stores."""
    low = datetime.combine(start, time.min) - _offset() if start else None
    high = datetime.combine(end, time.max) - _offset() if end else None
    return low, high
