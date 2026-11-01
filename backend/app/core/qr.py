import io
from urllib.parse import quote
import segno
from backend.app.core.config import settings


def warranty_url(serial: str) -> str:
    """The page a phone camera opens when it scans the label on a unit."""
    return f"{settings.PUBLIC_BASE_URL.rstrip('/')}/check?serial={quote(serial, safe='')}"


def qr_png(serial: str) -> bytes:
    """A QR code for one serial number. It holds the warranty check address, which also carries the serial number."""
    buffer = io.BytesIO()
    segno.make(warranty_url(serial), error="m").save(buffer, kind="png", scale=8, border=2)
    return buffer.getvalue()
