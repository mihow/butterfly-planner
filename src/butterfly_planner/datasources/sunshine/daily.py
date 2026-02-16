"""16-day daily sunshine forecast from Open-Meteo Forecast API."""

from __future__ import annotations

from datetime import date
from typing import Any

from butterfly_planner.datasources.sunshine.models import DailySunshine
from butterfly_planner.services.http import session

FORECAST_API = "https://api.open-meteo.com/v1/forecast"


def fetch_16day_sunshine(
    lat: float, lon: float, timezone: str = "America/Los_Angeles"
) -> list[DailySunshine]:
    """
    Fetch 16-day daily sunshine forecast.

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
