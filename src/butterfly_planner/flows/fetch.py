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
from datetime import date, datetime
from pathlib import Path
from typing import Any

import requests
from prefect import flow, task

from butterfly_planner import inaturalist, sunshine

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
        "daily": [
            "temperature_2m_max",
            "temperature_2m_min",
            "precipitation_sum",
            "weather_code",
        ],
        "timezone": "America/Los_Angeles",
        "forecast_days": 16,
    }

    resp = requests.get(url, params=params, timeout=30)
    resp.raise_for_status()
    result: dict[str, Any] = resp.json()
    return result


@task(name="fetch-sunshine-15min", retries=2, retry_delay_seconds=5)
def fetch_sunshine_15min(lat: float = 45.5, lon: float = -122.6) -> dict[str, Any]:
    """Fetch 15-minute sunshine forecast for the next 3 days."""
    slots = sunshine.fetch_today_15min_sunshine(lat, lon, forecast_days=3)
    return {
        "minutely_15": {
            "time": [s.time.isoformat() for s in slots],
            "sunshine_duration": [s.duration_seconds for s in slots],
            "is_day": [1 if s.is_day else 0 for s in slots],
        }
    }


@task(name="fetch-sunshine-16day", retries=2, retry_delay_seconds=5)
def fetch_sunshine_16day(lat: float = 45.5, lon: float = -122.6) -> dict[str, Any]:
    """Fetch 16-day daily sunshine forecast."""
    forecasts = sunshine.fetch_16day_sunshine(lat, lon)
    return {
        "daily": {
            "time": [f.date.isoformat() for f in forecasts],
            "sunshine_duration": [f.sunshine_seconds for f in forecasts],
            "daylight_duration": [f.daylight_seconds for f in forecasts],
        }
    }


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


@task(name="fetch-inaturalist", retries=2, retry_delay_seconds=5)
def fetch_inaturalist() -> dict[str, Any]:
    """Fetch butterfly species counts for the current month from iNaturalist."""
    month = date.today().month
    species = inaturalist.fetch_species_counts(month)
    return {
        "month": month,
        "species": [
            {
                "taxon_id": s.taxon_id,
                "scientific_name": s.scientific_name,
                "common_name": s.common_name,
                "rank": s.rank,
                "observation_count": s.observation_count,
                "photo_url": s.photo_url,
                "taxon_url": s.taxon_url,
            }
            for s in species
        ],
    }


@task(name="save-inaturalist")
def save_inaturalist(inat_data: dict[str, Any]) -> Path:
    """Save iNaturalist data to JSON file."""
    RAW_DIR.mkdir(parents=True, exist_ok=True)

    output_path = RAW_DIR / "inaturalist.json"
    with output_path.open("w") as f:
        json.dump(
            {
                "fetched_at": datetime.now().isoformat(),
                "source": "inaturalist.org",
                "data": inat_data,
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

    print("Fetching iNaturalist butterfly sightings...")
    inat_data = fetch_inaturalist()
    inat_path = save_inaturalist(inat_data)

    species_count = len(inat_data.get("species", []))
    print(f"Saved {species_count} butterfly species to {inat_path}")

    return {
        "weather_days": days,
        "sunshine_slots": slots,
        "inat_species": species_count,
        "outputs": {
            "weather": str(output_path),
            "sunshine": str(sunshine_path),
            "inaturalist": str(inat_path),
        },
    }


if __name__ == "__main__":
    result = fetch_all()
    print(f"Flow complete: {result}")
