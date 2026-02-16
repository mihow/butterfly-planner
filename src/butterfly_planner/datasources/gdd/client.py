"""GDD data fetching from Open-Meteo archive API."""

from __future__ import annotations

from datetime import date, timedelta

import requests

from butterfly_planner.datasources.gdd.compute import compute_accumulated_gdd
from butterfly_planner.datasources.gdd.models import (
    DEFAULT_BASE_TEMP_F,
    DEFAULT_UPPER_CUTOFF_F,
    YearGDD,
)

# Open-Meteo archive endpoint for historical daily temperatures
ARCHIVE_API = "https://archive-api.open-meteo.com/v1/archive"


def fetch_temperature_data(
    lat: float,
    lon: float,
    start: date,
    end: date,
) -> list[tuple[date, float, float]]:
    """Fetch daily min/max temperatures from the Open-Meteo archive API.

    Args:
        lat: Latitude of the location.
        lon: Longitude of the location.
        start: Start date (inclusive).
        end: End date (inclusive).

    Returns:
        List of (date, tmax_f, tmin_f) tuples.

    Raises:
        requests.HTTPError: If the API request fails.
    """
    params: dict[str, str | float] = {
        "latitude": lat,
        "longitude": lon,
        "start_date": start.isoformat(),
        "end_date": end.isoformat(),
        "daily": "temperature_2m_max,temperature_2m_min",
        "temperature_unit": "fahrenheit",
        "timezone": "America/Los_Angeles",
    }

    resp = requests.get(ARCHIVE_API, params=params, timeout=30)
    resp.raise_for_status()
    data = resp.json()

    daily = data.get("daily", {})
    dates = daily.get("time", [])
    tmax_values = daily.get("temperature_2m_max", [])
    tmin_values = daily.get("temperature_2m_min", [])

    results: list[tuple[date, float, float]] = []
    for i, date_str in enumerate(dates):
        dt = date.fromisoformat(date_str)
        tmax = tmax_values[i] if tmax_values[i] is not None else 0.0
        tmin = tmin_values[i] if tmin_values[i] is not None else 0.0
        results.append((dt, tmax, tmin))

    return results


def fetch_year_gdd(
    lat: float,
    lon: float,
    year: int,
    through: date | None = None,
    base_temp_f: float = DEFAULT_BASE_TEMP_F,
    upper_cutoff_f: float = DEFAULT_UPPER_CUTOFF_F,
) -> YearGDD:
    """Fetch temperatures and compute GDD for a full year (or year-to-date).

    Args:
        lat: Latitude.
        lon: Longitude.
        year: Calendar year to fetch.
        through: End date (defaults to Dec 31 or yesterday if current year).
        base_temp_f: Base temperature for GDD computation.
        upper_cutoff_f: Upper cutoff temperature.

    Returns:
        YearGDD with daily GDD entries.
    """
    start = date(year, 1, 1)
    if through is None:
        today = date.today()
        through = today - timedelta(days=1) if year == today.year else date(year, 12, 31)

    temps = fetch_temperature_data(lat, lon, start, through)
    daily = compute_accumulated_gdd(temps, base_temp_f, upper_cutoff_f)
    return YearGDD(year=year, daily=daily)
