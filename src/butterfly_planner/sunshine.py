"""
Sunshine duration forecasting module.

Fetches and processes sunshine forecast data from Open-Meteo API.
Butterflies are most active during sunny periods, so this helps identify
optimal viewing times.

Three main features:
1. Today's 15-minute sunshine breakdown (high resolution)
2. 16-day daily sunshine totals
3. Ensemble confidence analysis (stub for future implementation)

API Documentation: https://open-meteo.com/en/docs
"""

from __future__ import annotations

import statistics
from dataclasses import dataclass
from datetime import date, datetime
from typing import Any

from butterfly_planner.services.http import session

# Open-Meteo API endpoints
FORECAST_API = "https://api.open-meteo.com/v1/forecast"
ENSEMBLE_API = "https://ensemble-api.open-meteo.com/v1/ensemble"


@dataclass
class SunshineSlot:
    """A single 15-minute sunshine measurement."""

    time: datetime
    duration_seconds: int
    is_day: bool

    @property
    def duration_minutes(self) -> float:
        """Duration in minutes (0-15)."""
        return self.duration_seconds / 60

    @property
    def percentage(self) -> float:
        """Percentage of the 15-min slot that was sunny (0-100)."""
        return (self.duration_seconds / 900) * 100  # 900 sec = 15 min


@dataclass
class DailySunshine:
    """Daily sunshine summary."""

    date: date
    sunshine_seconds: int
    daylight_seconds: int

    @property
    def sunshine_hours(self) -> float:
        """Total sunshine in hours."""
        return self.sunshine_seconds / 3600

    @property
    def sunshine_percent(self) -> float:
        """Percentage of daylight that was sunny (0-100)."""
        if self.daylight_seconds == 0:
            return 0.0
        return (self.sunshine_seconds / self.daylight_seconds) * 100

    @property
    def is_good_butterfly_weather(self) -> bool:
        """
        Whether this day has good butterfly viewing conditions.

        Good = >3 hours of sun OR >40% of daylight is sunny.
        """
        return self.sunshine_hours > 3.0 or self.sunshine_percent > 40.0


@dataclass
class EnsembleSunshine:
    """Sunshine forecast with ensemble member statistics."""

    time: datetime
    member_values: list[int]  # sunshine_duration seconds from each ensemble member

    @property
    def mean(self) -> float:
        """Mean sunshine duration across all members (seconds)."""
        return statistics.mean(self.member_values)

    @property
    def std(self) -> float:
        """Standard deviation (seconds)."""
        return statistics.stdev(self.member_values) if len(self.member_values) > 1 else 0.0

    @property
    def min(self) -> int:
        """Minimum value across members."""
        return min(self.member_values)

    @property
    def max(self) -> int:
        """Maximum value across members."""
        return max(self.member_values)

    @property
    def p10(self) -> float:
        """10th percentile (low estimate)."""
        if len(self.member_values) < 2:
            return float(self.member_values[0]) if self.member_values else 0.0
        return statistics.quantiles(self.member_values, n=10)[0]

    @property
    def p50(self) -> float:
        """50th percentile (median)."""
        return statistics.median(self.member_values)

    @property
    def p90(self) -> float:
        """90th percentile (high estimate)."""
        if len(self.member_values) < 2:
            return float(self.member_values[0]) if self.member_values else 0.0
        return statistics.quantiles(self.member_values, n=10)[8]

    @property
    def confidence_width(self) -> float:
        """
        Width of 80% confidence interval (p90 - p10).

        Smaller values indicate higher forecast confidence.
        """
        return self.p90 - self.p10


# =============================================================================
# API Fetching Functions
# =============================================================================


def fetch_today_15min_sunshine(
    lat: float, lon: float, timezone: str = "America/Los_Angeles", forecast_days: int = 1
) -> list[SunshineSlot]:
    """
    Fetch 15-minute sunshine forecast.

    Args:
        lat: Latitude
        lon: Longitude
        timezone: Timezone name (e.g., "America/Los_Angeles")
        forecast_days: Number of days to fetch (1-16, default 1)

    Returns:
        List of SunshineSlot objects

    Note:
        15-minute data is only available for Central Europe and North America.
        Outside these regions, data is interpolated from hourly forecasts.
    """
    params: dict[str, str | int | float] = {
        "latitude": lat,
        "longitude": lon,
        "minutely_15": "sunshine_duration,is_day",
        "timezone": timezone,
        "forecast_days": forecast_days,
    }

    resp = session.get(FORECAST_API, params=params)
    resp.raise_for_status()
    data: dict[str, Any] = resp.json()

    # Parse response
    minutely = data.get("minutely_15", {})
    times = minutely.get("time", [])
    durations = minutely.get("sunshine_duration", [])
    is_day = minutely.get("is_day", [])

    slots = []
    for i, time_str in enumerate(times):
        dt = datetime.fromisoformat(time_str)
        slots.append(SunshineSlot(time=dt, duration_seconds=durations[i], is_day=bool(is_day[i])))

    return slots


def fetch_16day_sunshine(
    lat: float, lon: float, timezone: str = "America/Los_Angeles"
) -> list[DailySunshine]:
    """
    Fetch 16-day daily sunshine forecast (Module 2).

    Args:
        lat: Latitude
        lon: Longitude
        timezone: Timezone name

    Returns:
        List of DailySunshine objects for the next 16 days
    """
    params: dict[str, str | int | float] = {
        "latitude": lat,
        "longitude": lon,
        "daily": "sunshine_duration,daylight_duration",
        "timezone": timezone,
        "forecast_days": 16,
    }

    resp = session.get(FORECAST_API, params=params)
    resp.raise_for_status()
    data: dict[str, Any] = resp.json()

    # Parse response
    daily = data.get("daily", {})
    dates = daily.get("time", [])
    sunshine_secs = daily.get("sunshine_duration", [])
    daylight_secs = daily.get("daylight_duration", [])

    forecasts = []
    for i, date_str in enumerate(dates):
        dt = date.fromisoformat(date_str)
        forecasts.append(
            DailySunshine(
                date=dt, sunshine_seconds=sunshine_secs[i], daylight_seconds=daylight_secs[i]
            )
        )

    return forecasts


def fetch_ensemble_sunshine(
    lat: float, lon: float, timezone: str = "America/Los_Angeles", forecast_days: int = 7
) -> list[EnsembleSunshine]:
    """
    Fetch ensemble sunshine forecast for confidence analysis (Module 3 - STUB).

    This provides uncertainty estimates by running multiple weather model variations.

    Args:
        lat: Latitude
        lon: Longitude
        timezone: Timezone name
        forecast_days: Number of days (max 35 for ensemble)

    Returns:
        List of EnsembleSunshine objects with hourly forecasts

    Note:
        Ensemble API counts as ~4x API calls due to computational cost.
        Use sparingly.

    TODO:
        - Add visualization of confidence bands
        - Implement caching to reduce API usage
        - Consider only fetching for specific days of interest
    """
    params: dict[str, str | int | float] = {
        "latitude": lat,
        "longitude": lon,
        "hourly": "sunshine_duration",
        "models": "gfs_seamless",  # 31 ensemble members
        "timezone": timezone,
        "forecast_days": forecast_days,
    }

    resp = session.get(ENSEMBLE_API, params=params, timeout=60)
    resp.raise_for_status()
    data: dict[str, Any] = resp.json()

    # Parse ensemble response
    hourly = data.get("hourly", {})
    times = hourly.get("time", [])

    # Extract all member data
    # Keys are like: sunshine_duration_member00, sunshine_duration_member01, ...
    member_keys = [k for k in hourly if k.startswith("sunshine_duration_member")]
    member_keys.sort()  # Ensure consistent ordering

    forecasts = []
    for i, time_str in enumerate(times):
        dt = datetime.fromisoformat(time_str)
        member_values = [hourly[key][i] for key in member_keys]
        forecasts.append(EnsembleSunshine(time=dt, member_values=member_values))

    return forecasts


# =============================================================================
# Analysis and Summary Functions
# =============================================================================


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
