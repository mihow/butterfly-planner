"""
Weather data integration.

Uses Open-Meteo (free, no API key): https://open-meteo.com/
- Forecast API: https://api.open-meteo.com/v1/forecast
- Historical Archive API: https://archive-api.open-meteo.com/v1/archive

Example:
    from butterfly_planner.services import weather
    data = weather.fetch_historical_daily("2024-06-15", "2024-06-20", 45.5, -122.6)
"""

from __future__ import annotations

from typing import Any

from butterfly_planner.services.http import session

OPEN_METEO_API = "https://api.open-meteo.com/v1/forecast"
OPEN_METEO_HISTORICAL = "https://archive-api.open-meteo.com/v1/archive"

# Daily variables we request from the archive API
_DAILY_VARS = [
    "temperature_2m_max",
    "temperature_2m_min",
    "precipitation_sum",
    "weather_code",
]


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
        "daily": _DAILY_VARS,
        "timezone": "America/Los_Angeles",
    }
    resp = session.get(OPEN_METEO_HISTORICAL, params=params)
    resp.raise_for_status()
    result: dict[str, Any] = resp.json()
    return result
