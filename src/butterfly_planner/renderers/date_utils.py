"""Shared date-formatting helpers for renderers."""

from __future__ import annotations

from datetime import date
from typing import Any


def year_range(observations: list[dict[str, Any]]) -> str:
    """Derive year range string from observation dates, e.g. '2014-2026'."""
    years: set[int] = set()
    for obs in observations:
        observed_on = obs.get("observed_on", "")
        if observed_on and len(observed_on) >= 4 and observed_on[:4].isdigit():
            years.add(int(observed_on[:4]))
    if not years:
        return "all years"
    min_year, max_year = min(years), max(years)
    if min_year == max_year:
        return str(min_year)
    return f"{min_year}\u2013{max_year}"


def date_range_label(date_start: str, date_end: str) -> str:
    """Human-readable date-range label from ISO date strings.

    Returns e.g. ``Feb 10\u201324`` (same month) or ``Feb 24\u2013Mar 10``
    (cross-month).  Falls back to ``this week`` when dates are missing.
    """
    if not date_start or not date_end:
        return "this week"
    start = date.fromisoformat(date_start)
    end = date.fromisoformat(date_end)
    start_str = f"{start.strftime('%b')} {start.day}"
    end_str = str(end.day) if start.month == end.month else f"{end.strftime('%b')} {end.day}"
    return f"{start_str}\u2013{end_str}"
