"""
Weather data integration.

Uses Open-Meteo (free, no API key): https://open-meteo.com/
Backup: National Weather Service API

Example:
    from butterfly_planner.services import weather
    forecast = weather.get_forecast(lat=45.5, lon=-122.6)
"""

OPEN_METEO_API = "https://api.open-meteo.com/v1/forecast"
OPEN_METEO_HISTORICAL = "https://archive-api.open-meteo.com/v1/archive"

# TODO: Implement forecast and historical weather fetching
