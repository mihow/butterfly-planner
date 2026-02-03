"""
Prefect flow for fetching data from external sources.

Working example using Open-Meteo (free, no API key).

Run locally:
    python -m butterfly_planner.flows.fetch

Run with Prefect (optional dashboard):
    prefect server start &
    python -m butterfly_planner.flows.fetch
"""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path

import requests

# Data directories
DATA_DIR = Path("data")
RAW_DIR = DATA_DIR / "raw"


def fetch_weather(lat: float = 45.5, lon: float = -122.6) -> dict:
    """
    Fetch 7-day weather forecast from Open-Meteo.

    Args:
        lat: Latitude (default: Portland, OR)
        lon: Longitude

    Returns:
        Weather data dict
    """
    url = "https://api.open-meteo.com/v1/forecast"
    params = {
        "latitude": lat,
        "longitude": lon,
        "daily": ["temperature_2m_max", "temperature_2m_min", "precipitation_sum"],
        "timezone": "America/Los_Angeles",
        "forecast_days": 7,
    }

    resp = requests.get(url, params=params, timeout=30)
    resp.raise_for_status()
    return resp.json()


def run() -> dict:
    """Main entry point - fetch all data sources."""
    RAW_DIR.mkdir(parents=True, exist_ok=True)

    print("Fetching weather data from Open-Meteo...")
    weather = fetch_weather()

    # Save raw data with metadata
    output_path = RAW_DIR / "weather.json"
    with open(output_path, "w") as f:
        json.dump(
            {
                "fetched_at": datetime.now().isoformat(),
                "source": "open-meteo.com",
                "data": weather,
            },
            f,
            indent=2,
        )

    print(f"Saved to {output_path}")
    return {"weather_days": len(weather.get("daily", {}).get("time", []))}


if __name__ == "__main__":
    result = run()
    print(f"Fetch complete: {result}")
