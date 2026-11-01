from datetime import date, datetime, time, timedelta, timezone
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from fastapi import HTTPException

from app.core.config import settings


def reporting_window(start_date: date | None, end_date: date | None) -> tuple[date, date, datetime, datetime]:
    try:
        business_timezone = ZoneInfo(settings.BUSINESS_TIMEZONE)
    except ZoneInfoNotFoundError as exc:
        raise RuntimeError(f"Unknown BUSINESS_TIMEZONE: {settings.BUSINESS_TIMEZONE}") from exc

    today = datetime.now(business_timezone).date()
    start = start_date or today
    end = end_date or start
    if end < start:
        raise HTTPException(422, "end_date must be on or after start_date")
    if (end - start).days > 366:
        raise HTTPException(422, "Date range cannot exceed 367 days")

    start_local = datetime.combine(start, time.min, tzinfo=business_timezone)
    end_local = datetime.combine(end + timedelta(days=1), time.min, tzinfo=business_timezone)
    start_utc = start_local.astimezone(timezone.utc).replace(tzinfo=None)
    end_utc = end_local.astimezone(timezone.utc).replace(tzinfo=None)
    return start, end, start_utc, end_utc
