import csv
import io
from typing import Iterable, List
from fastapi.responses import Response


def _safe(value):
    """Stop spreadsheet programs from running a cell as a formula, for example a customer named '=1+1'."""
    if isinstance(value, str) and value[:1] in ("=", "+", "-", "@", "\t", "\r"):
        return "'" + value
    return value


def csv_response(filename: str, header: List[str], rows: Iterable[Iterable]) -> Response:
    """A downloadable CSV. A byte-order mark is added so Excel reads the rupee sign and other characters correctly."""
    buffer = io.StringIO()
    writer = csv.writer(buffer)
    writer.writerow(header)
    for row in rows:
        writer.writerow([_safe(cell) for cell in row])
    body = "﻿" + buffer.getvalue()
    return Response(
        content=body.encode("utf-8"),
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
