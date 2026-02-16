"""Merge sunshine and weather forecasts into a unified 16-day view.

Combines the Open-Meteo daily sunshine forecast with the weather
forecast, producing per-day records that the sunshine renderer can
display directly without cross-datasource knowledge.
"""

from __future__ import annotations

from typing import Any


def merge_sunshine_weather(
    weather_data: dict[str, Any] | None,
) -> dict[str, dict[str, Any]]:
    """Build a date-keyed weather lookup from a weather forecast envelope.

    Extracts daily temperature, precipitation, and weather code from the
    weather forecast and indexes them by ISO date string.

    Args:
        weather_data: Weather forecast envelope with
            ``data.daily.{time, temperature_2m_max, temperature_2m_min,
            precipitation_sum, weather_code}`` arrays.

    Returns:
        Dict mapping ISO date string -> weather record with keys
        ``high_c``, ``low_c``, ``precip_mm``, ``weather_code``.
        Empty dict if no weather data is available.
    """
    if not weather_data:
        return {}

    w_daily = weather_data.get("data", {}).get("daily", {})
    w_dates = w_daily.get("time", [])

    weather_by_date: dict[str, dict[str, Any]] = {}
    for j, w_date in enumerate(w_dates):
        weather_by_date[w_date] = {
            "high_c": w_daily.get("temperature_2m_max", [None])[j],
            "low_c": w_daily.get("temperature_2m_min", [None])[j],
            "precip_mm": w_daily.get("precipitation_sum", [None])[j],
            "weather_code": w_daily.get("weather_code", [None])[j],
        }

    return weather_by_date
