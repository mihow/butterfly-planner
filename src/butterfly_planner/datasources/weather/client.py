"""Open-Meteo API client constants and shared configuration.

API docs:
  - Forecast: https://open-meteo.com/en/docs
  - Archive: https://open-meteo.com/en/docs/historical-weather-api
"""

OPEN_METEO_API = "https://api.open-meteo.com/v1/forecast"
OPEN_METEO_HISTORICAL = "https://archive-api.open-meteo.com/v1/archive"

# Daily variables we request from Open-Meteo
DAILY_VARS = [
    "temperature_2m_max",
    "temperature_2m_min",
    "precipitation_sum",
    "weather_code",
]
