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

from prefect import flow, task

from butterfly_planner.datasources import gdd, inaturalist, sunshine
from butterfly_planner.datasources.weather import forecast as weather_forecast
from butterfly_planner.datasources.weather import historical as weather_historical

# Data directories
DATA_DIR = Path("data")
RAW_DIR = DATA_DIR / "raw"


@task(name="fetch-weather", retries=2, retry_delay_seconds=5)
def fetch_weather(lat: float = 45.5, lon: float = -122.6) -> dict[str, Any]:
    """
    Fetch 16-day weather forecast from Open-Meteo.

    Args:
        lat: Latitude (default: Portland, OR)
        lon: Longitude

    Returns:
        Weather data dict
    """
    return weather_forecast.fetch_forecast(lat, lon)


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
    """Fetch butterfly species and observations for the current week ± 1."""
    summary = inaturalist.get_current_week_species()
    return {
        "month": summary.month,
        "weeks": summary.weeks,
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
            for s in summary.species
        ],
        "observations": [
            {
                "id": obs.id,
                "species": obs.species,
                "common_name": obs.common_name,
                "observed_on": obs.observed_on.isoformat(),
                "latitude": obs.latitude,
                "longitude": obs.longitude,
                "quality_grade": obs.quality_grade,
                "url": obs.url,
                "photo_url": obs.photo_url,
            }
            for obs in summary.observations
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


@task(name="fetch-historical-weather", retries=2, retry_delay_seconds=5)
def fetch_historical_weather(
    observations: list[dict[str, Any]],
    lat: float = 45.5,
    lon: float = -122.6,
) -> dict[str, dict[str, Any]]:
    """
    Fetch historical daily weather for each unique observation date.

    Uses the Open-Meteo Archive API with the region centroid (all observations
    are in roughly the same geographic area).  Batches dates into contiguous
    year-ranges to minimise API calls.

    Returns:
        Dict keyed by date string (YYYY-MM-DD) → weather row dict.
    """
    dates: set[str] = set()
    for obs in observations:
        observed_on = obs.get("observed_on", "")
        if observed_on:
            dates.add(observed_on)

    if not dates:
        return {}

    # Group dates by year and build contiguous ranges per year
    by_year: dict[str, list[str]] = {}
    for d in sorted(dates):
        year = d[:4]
        by_year.setdefault(year, []).append(d)

    weather_by_date: dict[str, dict[str, Any]] = {}
    for _year, year_dates in by_year.items():
        start = min(year_dates)
        end = max(year_dates)
        data = weather_historical.fetch_historical_daily(start, end, lat, lon)
        daily = data.get("daily", {})
        api_dates = daily.get("time", [])
        for i, api_date in enumerate(api_dates):
            if api_date in dates:
                weather_by_date[api_date] = {
                    "high_c": daily.get("temperature_2m_max", [None])[i],
                    "low_c": daily.get("temperature_2m_min", [None])[i],
                    "precip_mm": daily.get("precipitation_sum", [None])[i],
                    "weather_code": daily.get("weather_code", [None])[i],
                }

    return weather_by_date


@task(name="save-historical-weather")
def save_historical_weather(weather_by_date: dict[str, dict[str, Any]]) -> Path:
    """Save historical weather cache to JSON file."""
    RAW_DIR.mkdir(parents=True, exist_ok=True)

    output_path = RAW_DIR / "historical_weather.json"
    with output_path.open("w") as f:
        json.dump(
            {
                "fetched_at": datetime.now().isoformat(),
                "source": "open-meteo.com (archive)",
                "by_date": weather_by_date,
            },
            f,
            indent=2,
        )

    return output_path


@task(name="fetch-gdd", retries=2, retry_delay_seconds=5)
def fetch_gdd(
    lat: float = 45.5,
    lon: float = -122.6,
    base_temp_f: float = 50.0,
    upper_cutoff_f: float = 86.0,
) -> dict[str, Any]:
    """Fetch temperature data and compute GDD for current and previous year.

    Fetches daily min/max temperatures from the Open-Meteo archive API,
    computes daily and accumulated GDD using the modified average method.

    Args:
        lat: Latitude (default: Portland, OR).
        lon: Longitude.
        base_temp_f: GDD base temperature in Fahrenheit.
        upper_cutoff_f: GDD upper cutoff temperature in Fahrenheit.

    Returns:
        Dict with current_year, previous_year, and location metadata.
    """
    today = date.today()
    current = gdd.fetch_year_gdd(
        lat, lon, today.year, base_temp_f=base_temp_f, upper_cutoff_f=upper_cutoff_f
    )
    previous = gdd.fetch_year_gdd(
        lat, lon, today.year - 1, base_temp_f=base_temp_f, upper_cutoff_f=upper_cutoff_f
    )

    return {
        "location": {"lat": lat, "lon": lon},
        "base_temp_f": base_temp_f,
        "upper_cutoff_f": upper_cutoff_f,
        "current_year": gdd.year_gdd_to_dict(current),
        "previous_year": gdd.year_gdd_to_dict(previous),
    }


@task(name="save-gdd")
def save_gdd(gdd_data: dict[str, Any]) -> Path:
    """Save GDD data to JSON file."""
    RAW_DIR.mkdir(parents=True, exist_ok=True)

    output_path = RAW_DIR / "gdd.json"
    with output_path.open("w") as f:
        json.dump(
            {
                "fetched_at": datetime.now().isoformat(),
                "source": "open-meteo.com (archive)",
                "data": gdd_data,
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

    print("Fetching historical weather for observation dates...")
    obs_list = inat_data.get("observations", [])
    hist_weather = fetch_historical_weather(obs_list, lat, lon)
    hist_path = save_historical_weather(hist_weather)
    print(f"Cached historical weather for {len(hist_weather)} dates to {hist_path}")

    print(f"Fetching GDD data for ({lat}, {lon})...")
    gdd_data = fetch_gdd(lat, lon)
    gdd_path = save_gdd(gdd_data)

    current_gdd = gdd_data.get("current_year", {}).get("total_gdd", 0)
    print(f"Saved GDD data ({current_gdd:.0f} accumulated) to {gdd_path}")

    return {
        "weather_days": days,
        "sunshine_slots": slots,
        "inat_species": species_count,
        "historical_weather_dates": len(hist_weather),
        "current_gdd": current_gdd,
        "outputs": {
            "weather": str(output_path),
            "sunshine": str(sunshine_path),
            "inaturalist": str(inat_path),
            "historical_weather": str(hist_path),
            "gdd": str(gdd_path),
        },
    }


if __name__ == "__main__":
    result = fetch_all()
    print(f"Flow complete: {result}")
