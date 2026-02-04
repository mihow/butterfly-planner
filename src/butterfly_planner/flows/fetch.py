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

    return {"weather_days": days, "output": str(output_path)}


if __name__ == "__main__":
    result = fetch_all()
    print(f"Flow complete: {result}")
