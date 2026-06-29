from datetime import datetime, timedelta, timezone
from typing import Optional


def browser_local_now(
    timezone_offset_minutes: Optional[float],
    *,
    utc_now: Optional[datetime] = None,
) -> datetime:
    """Return current browser-local time from JavaScript's UTC offset."""
    if timezone_offset_minutes is None:
        return datetime.now().astimezone()

    current_utc = utc_now or datetime.now(timezone.utc)
    if current_utc.tzinfo is None:
        current_utc = current_utc.replace(tzinfo=timezone.utc)

    browser_timezone = timezone(
        -timedelta(minutes=float(timezone_offset_minutes))
    )
    return current_utc.astimezone(browser_timezone)
