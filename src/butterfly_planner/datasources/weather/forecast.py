"""16-day weather forecast from Open-Meteo Forecast API."""

from __future__ import annotations

from typing import Any

from butterfly_planner.datasources.weather.client import DAILY_VARS, OPEN_METEO_API
from butterfly_planner.services.http import session


def fetch_forecast(
    lat: float = 45.5,
    lon: float = -122.6,
    *,
    forecast_days: int = 16,
) -> dict[str, Any]:
    """
    Fetch multi-day weather forecast from Open-Meteo.

    Args:
        lat: Latitude (default: Portland, OR).
        lon: Longitude.
        forecast_days: Number of days to forecast (max 16).

    Returns:
        Raw API response dict with ``daily`` key containing arrays.
    """
    params: dict[str, str | int | float | list[str]] = {
        "latitude": lat,
        "longitude": lon,
        "daily": DAILY_VARS,
        "timezone": "America/Los_Angeles",
        "forecast_days": forecast_days,
    }

    resp = session.get(OPEN_METEO_API, params=params)
    resp.raise_for_status()
    result: dict[str, Any] = resp.json()
    return result
