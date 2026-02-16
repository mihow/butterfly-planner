"""15-minute sunshine forecast from Open-Meteo Forecast API."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from butterfly_planner.datasources.sunshine.models import SunshineSlot
from butterfly_planner.services.http import session

FORECAST_API = "https://api.open-meteo.com/v1/forecast"


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
