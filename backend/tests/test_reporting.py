from datetime import date, datetime

import pytest
from fastapi import HTTPException

from app.api.v1.endpoints.reports import safe_csv_cell
from app.services.reporting import reporting_window


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        ("=HYPERLINK(\"https://example.test\")", "'=HYPERLINK(\"https://example.test\")"),
        (" +SUM(A1:A2)", "' +SUM(A1:A2)"),
        ("\t=1+1", "'\t=1+1"),
        ("DHAKA METRO GA 12-3456", "DHAKA METRO GA 12-3456"),
        (42, 42),
    ],
)
def test_csv_cells_are_safe_for_spreadsheet_import(value, expected):
    assert safe_csv_cell(value) == expected


def test_reporting_window_uses_dhaka_local_midnight():
    start, end, utc_start, utc_end = reporting_window(
        date(2026, 1, 1),
        date(2026, 1, 1),
    )
    assert (start, end) == (date(2026, 1, 1), date(2026, 1, 1))
    assert utc_start == datetime(2025, 12, 31, 18)
    assert utc_end == datetime(2026, 1, 1, 18)


def test_reporting_window_rejects_reversed_date_range():
    with pytest.raises(HTTPException) as error:
        reporting_window(date(2026, 1, 2), date(2026, 1, 1))
    assert error.value.status_code == 422
