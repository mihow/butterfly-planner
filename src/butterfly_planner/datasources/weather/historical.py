"""Historical daily weather from Open-Meteo Archive API."""

from __future__ import annotations

from typing import Any

from butterfly_planner.datasources.weather.client import DAILY_VARS, OPEN_METEO_HISTORICAL
from butterfly_planner.services.http import session


def fetch_historical_daily(
    start_date: str,
    end_date: str,
    lat: float = 45.5,
    lon: float = -122.6,
) -> dict[str, Any]:
    """
    Fetch historical daily weather from Open-Meteo Archive API.

    Args:
        start_date: ISO date string (YYYY-MM-DD).
        end_date: ISO date string (YYYY-MM-DD).
        lat: Latitude (default: Portland, OR).
        lon: Longitude.

    Returns:
        Raw API response dict with ``daily`` key containing arrays.
    """
    params: dict[str, Any] = {
        "latitude": lat,
        "longitude": lon,
        "start_date": start_date,
        "end_date": end_date,
        "daily": DAILY_VARS,
        "timezone": "America/Los_Angeles",
    }
    resp = session.get(OPEN_METEO_HISTORICAL, params=params)
    resp.raise_for_status()
    result: dict[str, Any] = resp.json()
    return result
