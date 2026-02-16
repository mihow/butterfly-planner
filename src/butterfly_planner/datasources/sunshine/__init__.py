"""Open-Meteo sunshine data source.

Fetches and processes sunshine forecast data from Open-Meteo API.
Butterflies are most active during sunny periods, so this helps identify
optimal viewing times.

Public API:
  - models: SunshineSlot, DailySunshine, EnsembleSunshine
  - today: fetch_today_15min_sunshine (high-resolution 15-min data)
  - daily: fetch_16day_sunshine (daily totals)
  - ensemble: fetch_ensemble_sunshine (confidence analysis)
  - Utility: get_daylight_slots, get_total_sunshine_minutes,
             get_peak_sunshine_window, summarize_weekly_sunshine
"""

from datetime import datetime
from typing import Any

from butterfly_planner.datasources.sunshine.daily import fetch_16day_sunshine
from butterfly_planner.datasources.sunshine.ensemble import (
    ENSEMBLE_API,
    fetch_ensemble_sunshine,
)
from butterfly_planner.datasources.sunshine.models import (
    DailySunshine,
    EnsembleSunshine,
    SunshineSlot,
)
from butterfly_planner.datasources.sunshine.today import (
    FORECAST_API,
    fetch_today_15min_sunshine,
)

__all__ = [
    "ENSEMBLE_API",
    "FORECAST_API",
    "DailySunshine",
    "EnsembleSunshine",
    "SunshineSlot",
    "fetch_16day_sunshine",
    "fetch_ensemble_sunshine",
    "fetch_today_15min_sunshine",
    "get_daylight_slots",
    "get_peak_sunshine_window",
    "get_total_sunshine_minutes",
    "summarize_weekly_sunshine",
]


# ---------------------------------------------------------------------------
# Utility / analysis functions
# ---------------------------------------------------------------------------


def get_daylight_slots(slots: list[SunshineSlot]) -> list[SunshineSlot]:
    """Filter to only daylight hours."""
    return [s for s in slots if s.is_day]


def get_total_sunshine_minutes(slots: list[SunshineSlot]) -> float:
    """Calculate total sunshine minutes from a list of slots."""
    return sum(s.duration_minutes for s in slots)


def get_peak_sunshine_window(
    slots: list[SunshineSlot], window_hours: int = 1
) -> tuple[datetime, float]:
    """
    Find the time window with the most sunshine.

    Args:
        slots: List of sunshine slots
        window_hours: Size of rolling window in hours

    Returns:
        Tuple of (start_time, total_minutes_in_window)
    """
    if not slots:
        raise ValueError("Empty slots list")

    window_slots = window_hours * 4  # 4 slots per hour (15 min each)

    # Handle case where window_size > available slots
    if window_slots > len(slots):
        total = sum(s.duration_minutes for s in slots)
        return slots[0].time, total

    best_start_time = slots[0].time
    best_total = 0.0

    for i in range(len(slots) - window_slots + 1):
        window = slots[i : i + window_slots]
        total = sum(s.duration_minutes for s in window)
        if total > best_total:
            best_total = total
            best_start_time = window[0].time

    return best_start_time, best_total


def summarize_weekly_sunshine(forecasts: list[DailySunshine]) -> dict[str, Any]:
    """
    Summarize sunshine forecast into this week vs next week.

    Args:
        forecasts: List of daily forecasts (should be 14-16 days)

    Returns:
        Dictionary with summary statistics
    """
    this_week = forecasts[:7]
    next_week = forecasts[7:14] if len(forecasts) >= 14 else []

    def calc_stats(days: list[DailySunshine]) -> dict[str, Any]:
        if not days:
            return {}
        good_days = sum(1 for d in days if d.is_good_butterfly_weather)
        avg_hours = sum(d.sunshine_hours for d in days) / len(days)
        avg_percent = sum(d.sunshine_percent for d in days) / len(days)
        return {
            "total_days": len(days),
            "good_days": good_days,
            "avg_sunshine_hours": round(avg_hours, 1),
            "avg_sunshine_percent": round(avg_percent, 1),
        }

    return {
        "this_week": calc_stats(this_week),
        "next_week": calc_stats(next_week),
        "total_days": len(forecasts),
        "good_days": sum(1 for d in forecasts if d.is_good_butterfly_weather),
    }
