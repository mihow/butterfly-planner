"""
Prefect flow for fetching data from external sources.

Working example using Open-Meteo (free, no API key).

Run locally:
    python -m butterfly_planner.flows.fetch

Run with Prefect dashboard:
    prefect server start &
    python -m butterfly_planner.flows.fetch
"""

from __future__ import annotations

import json
from collections.abc import Callable
from datetime import datetime
from pathlib import Path
from typing import Any, TypeVar

import requests

_F = TypeVar("_F", bound=Callable[..., Any])

# Try to import Prefect, fall back to no-op decorators if unavailable
try:
    from prefect import flow, task
except ImportError:  # pragma: no cover
    # Fallback: simple pass-through decorators
    def task(**_kwargs: Any) -> Callable[[_F], _F]:  # type: ignore[no-redef]
        def decorator(fn: _F) -> _F:
            return fn

        return decorator

    def flow(**_kwargs: Any) -> Callable[[_F], _F]:  # type: ignore[misc]
        def decorator(fn: _F) -> _F:
            return fn

        return decorator


# Data directories
DATA_DIR = Path("data")
RAW_DIR = DATA_DIR / "raw"


@task(name="fetch-weather", retries=2, retry_delay_seconds=5)
def fetch_weather(lat: float = 45.5, lon: float = -122.6) -> dict[str, Any]:
    """
    Fetch 7-day weather forecast from Open-Meteo.

    Args:
        lat: Latitude (default: Portland, OR)
        lon: Longitude

    Returns:
        Weather data dict
    """
    url = "https://api.open-meteo.com/v1/forecast"
    params: dict[str, str | int | float | list[str]] = {
        "latitude": lat,
        "longitude": lon,
        "daily": ["temperature_2m_max", "temperature_2m_min", "precipitation_sum"],
        "timezone": "America/Los_Angeles",
        "forecast_days": 7,
    }

    resp = requests.get(url, params=params, timeout=30)
    resp.raise_for_status()
    result: dict[str, Any] = resp.json()
    return result


@task(name="fetch-sunshine-15min")
def fetch_sunshine_15min(lat: float = 45.5, lon: float = -122.6) -> dict[str, Any]:
    """
    Fetch today's 15-minute sunshine forecast.

    Args:
        lat: Latitude
        lon: Longitude

    Returns:
        Sunshine data dict with 15-minute resolution
    """
    url = "https://api.open-meteo.com/v1/forecast"
    params: dict[str, str | int | float] = {
        "latitude": lat,
        "longitude": lon,
        "minutely_15": "sunshine_duration,is_day",
        "timezone": "America/Los_Angeles",
        "forecast_days": 1,
    }

    resp = requests.get(url, params=params, timeout=30)
    resp.raise_for_status()
    result: dict[str, Any] = resp.json()
    return result


@task(name="fetch-sunshine-16day")
def fetch_sunshine_16day(lat: float = 45.5, lon: float = -122.6) -> dict[str, Any]:
    """
    Fetch 16-day daily sunshine forecast.

    Args:
        lat: Latitude
        lon: Longitude

    Returns:
        Daily sunshine data for 16 days
    """
    url = "https://api.open-meteo.com/v1/forecast"
    params: dict[str, str | int | float] = {
        "latitude": lat,
        "longitude": lon,
        "daily": "sunshine_duration,daylight_duration",
        "timezone": "America/Los_Angeles",
        "forecast_days": 16,
    }

    resp = requests.get(url, params=params, timeout=30)
    resp.raise_for_status()
    result: dict[str, Any] = resp.json()
    return result


@task(name="save-weather")
def save_weather(weather: dict[str, Any]) -> Path:
    """Save weather data to JSON file."""
    RAW_DIR.mkdir(parents=True, exist_ok=True)

    output_path = RAW_DIR / "weather.json"
    with output_path.open("w") as f:
        json.dump(
            {
                "fetched_at": datetime.now().isoformat(),
                "source": "open-meteo.com",
                "data": weather,
            },
            f,
            indent=2,
        )

    return output_path


@task(name="save-sunshine")
def save_sunshine(sunshine_15min: dict[str, Any], sunshine_16day: dict[str, Any]) -> Path:
    """Save sunshine data to JSON file."""
    RAW_DIR.mkdir(parents=True, exist_ok=True)

    output_path = RAW_DIR / "sunshine.json"
    with output_path.open("w") as f:
        json.dump(
            {
                "fetched_at": datetime.now().isoformat(),
                "source": "open-meteo.com",
                "today_15min": sunshine_15min,
                "daily_16day": sunshine_16day,
            },
            f,
            indent=2,
        )

    return output_path


@flow(name="fetch-data", log_prints=True)
def fetch_all(lat: float = 45.5, lon: float = -122.6) -> dict[str, Any]:
    """
    Fetch all data sources.

    This is the main Prefect flow that orchestrates data fetching.
    """
    print(f"Fetching weather for ({lat}, {lon})...")

    weather = fetch_weather(lat, lon)
    output_path = save_weather(weather)

    days = len(weather.get("daily", {}).get("time", []))
    print(f"Saved {days} days of weather data to {output_path}")

    print(f"Fetching sunshine data for ({lat}, {lon})...")
    sunshine_15min = fetch_sunshine_15min(lat, lon)
    sunshine_16day = fetch_sunshine_16day(lat, lon)
    sunshine_path = save_sunshine(sunshine_15min, sunshine_16day)

    slots = len(sunshine_15min.get("minutely_15", {}).get("time", []))
    print(f"Saved {slots} 15-min sunshine slots and 16 days to {sunshine_path}")

    return {
        "weather_days": days,
        "sunshine_slots": slots,
        "outputs": {"weather": str(output_path), "sunshine": str(sunshine_path)},
    }


if __name__ == "__main__":
    result = fetch_all()
    print(f"Flow complete: {result}")
