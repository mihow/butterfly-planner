"""Open-Meteo weather data source.

Fetches forecast and historical daily weather from Open-Meteo (free, no API key).

Public API:
  - forecast: fetch_forecast (16-day weather forecast)
  - historical: fetch_historical_daily (archive API for past dates)
  - client: API URLs, shared constants
"""

from butterfly_planner.datasources.weather.client import (
    OPEN_METEO_API,
    OPEN_METEO_HISTORICAL,
)
from butterfly_planner.datasources.weather.forecast import fetch_forecast
from butterfly_planner.datasources.weather.historical import fetch_historical_daily

__all__ = [
    "OPEN_METEO_API",
    "OPEN_METEO_HISTORICAL",
    "fetch_forecast",
    "fetch_historical_daily",
]
