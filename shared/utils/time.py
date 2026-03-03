from datetime import date, datetime, timedelta, timezone
from typing import Iterator


def utc_now() -> datetime:
    """Return current UTC datetime with timezone info."""
    return datetime.now(timezone.utc)


def parse_br_date(date_str: str) -> datetime:
    """Parse a Brazilian date string (dd/mm/yyyy) to datetime."""
    for fmt in ("%d/%m/%Y", "%d/%m/%Y %H:%M:%S", "%Y-%m-%d", "%Y-%m-%dT%H:%M:%S"):
        try:
            return datetime.strptime(date_str, fmt).replace(tzinfo=timezone.utc)
        except ValueError:
            continue
    raise ValueError(f"Cannot parse date: {date_str}")


def date_range(
    start: date, end: date, step_days: int = 1
) -> Iterator[tuple[date, date]]:
    """Generate date range chunks of step_days."""
    current = start
    while current < end:
        chunk_end = min(current + timedelta(days=step_days), end)
        yield current, chunk_end
        current = chunk_end
