"""
Prefect flow for fetching data from external sources.

Each registered location is fetched with its own weather point, observation
box and timezone, and cached under its own slug (see ``flows/paths.py``).

Run locally (fetches every location):
    python -m butterfly_planner.flows.fetch

Run with Prefect dashboard:
    prefect server start &
    python -m butterfly_planner.flows.fetch
"""

from __future__ import annotations

import sys
from datetime import UTC, date, datetime, timedelta
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo

from prefect import flow, task

from butterfly_planner.datasources import gdd, inaturalist, sunshine
from butterfly_planner.datasources.weather import forecast as weather_forecast
from butterfly_planner.datasources.weather import historical as weather_historical
from butterfly_planner.flows.paths import location_paths
from butterfly_planner.reference.geography import (
    DEFAULT_LOCATION,
    LOCATIONS,
    Location,
    get_location,
)
from butterfly_planner.reference.viewing import OBS_WINDOW_DAYS_AHEAD, OBS_WINDOW_DAYS_BACK
from butterfly_planner.store import DataStore

# Data store with tiered directories
store = DataStore(Path("data"))


def local_today(timezone: str, now: datetime | None = None) -> date:
    """Return the calendar date in ``timezone``.

    The fetch job runs on a UTC machine, so the runner's own date can be a
    day ahead of the location's date during its evening.
    """
    instant = now or datetime.now(UTC)
    return instant.astimezone(ZoneInfo(timezone)).date()


@task(name="fetch-weather", retries=2, retry_delay_seconds=5)
def fetch_weather(loc: Location) -> dict[str, Any]:
    """Fetch 16-day weather forecast from Open-Meteo."""
    return weather_forecast.fetch_forecast(loc.lat, loc.lon, timezone=loc.timezone)


@task(name="fetch-sunshine-15min", retries=2, retry_delay_seconds=5)
def fetch_sunshine_15min(loc: Location) -> dict[str, Any]:
    """Fetch 15-minute sunshine forecast for the next 3 days."""
    slots = sunshine.fetch_today_15min_sunshine(
        loc.lat, loc.lon, timezone=loc.timezone, forecast_days=3
    )
    return {
        "minutely_15": {
            "time": [s.time.isoformat() for s in slots],
            "sunshine_duration": [s.duration_seconds for s in slots],
            "is_day": [1 if s.is_day else 0 for s in slots],
        }
    }


@task(name="fetch-sunshine-16day", retries=2, retry_delay_seconds=5)
def fetch_sunshine_16day(loc: Location) -> dict[str, Any]:
    """Fetch 16-day daily sunshine forecast."""
    forecasts = sunshine.fetch_16day_sunshine(loc.lat, loc.lon, timezone=loc.timezone)
    return {
        "daily": {
            "time": [f.date.isoformat() for f in forecasts],
            "sunshine_duration": [f.sunshine_seconds for f in forecasts],
            "daylight_duration": [f.daylight_seconds for f in forecasts],
        }
    }


@task(name="save-weather")
def save_weather(weather: dict[str, Any], loc: Location) -> Path:
    """Save weather data via store."""
    return store.write(
        location_paths(loc).weather,
        weather,
        source="open-meteo.com",
        valid_until=datetime.now(UTC) + timedelta(hours=6),
        location=loc.slug,
    )


@task(name="save-sunshine")
def save_sunshine(
    sunshine_15min: dict[str, Any], sunshine_16day: dict[str, Any], loc: Location
) -> Path:
    """Save sunshine 15-min and 16-day data via store."""
    paths = location_paths(loc)
    store.write(
        paths.sunshine_16day,
        sunshine_16day,
        source="open-meteo.com",
        valid_until=datetime.now(UTC) + timedelta(hours=6),
        location=loc.slug,
    )
    return store.write(
        paths.sunshine_15min,
        sunshine_15min,
        source="open-meteo.com",
        valid_until=datetime.now(UTC) + timedelta(hours=1),
        location=loc.slug,
    )


@task(name="fetch-inaturalist", retries=2, retry_delay_seconds=5)
def fetch_inaturalist(loc: Location, today: date | None = None) -> dict[str, Any]:
    """Fetch butterfly species and observations for the current week ± 1.

    Observations are filtered to 14 days prior and 7 days after today
    (by month-day, across all years).  The iNaturalist API only supports
    month-level filtering, so this post-filter narrows the window.

    Args:
        loc: The location whose bounding box is searched.
        today: The date the window is centred on. Defaults to today's date
            in the location's timezone.
    """
    today = today or local_today(loc.timezone)
    summary = inaturalist.get_current_week_species(bbox=loc.bbox.as_dict(), today=today)

    window_start = today - timedelta(days=OBS_WINDOW_DAYS_BACK)
    window_end = today + timedelta(days=OBS_WINDOW_DAYS_AHEAD)

    start_md = (window_start.month, window_start.day)
    end_md = (window_end.month, window_end.day)

    def _in_window(obs_date: date) -> bool:
        """Check if an observation's month-day falls within the date window."""
        obs_md = (obs_date.month, obs_date.day)
        if start_md <= end_md:
            # Normal case: window does not wrap around year boundary
            return start_md <= obs_md <= end_md
        # Window wraps year boundary (e.g. Dec 20 - Jan 10)
        return obs_md >= start_md or obs_md <= end_md

    return {
        "month": summary.month,
        "weeks": summary.weeks,
        "date_start": window_start.isoformat(),
        "date_end": window_end.isoformat(),
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
            if _in_window(obs.observed_on)
        ],
    }


@task(name="save-inaturalist")
def save_inaturalist(inat_data: dict[str, Any], loc: Location) -> Path:
    """Save iNaturalist data via store."""
    return store.write(
        location_paths(loc).inaturalist,
        inat_data,
        source="inaturalist.org",
        valid_until=datetime.now(UTC) + timedelta(hours=6),
        location=loc.slug,
    )


@task(name="fetch-historical-weather", retries=2, retry_delay_seconds=5)
def fetch_historical_weather(
    observations: list[dict[str, Any]],
    loc: Location,
) -> dict[str, dict[str, Any]]:
    """
    Fetch historical daily weather for each unique observation date.

    Uses the Open-Meteo Archive API at the location's weather point (all
    observations are in roughly the same geographic area).  Batches dates
    into contiguous year-ranges to minimise API calls.

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
        data = weather_historical.fetch_historical_daily(
            start, end, loc.lat, loc.lon, timezone=loc.timezone
        )
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
def save_historical_weather(weather_by_date: dict[str, dict[str, Any]], loc: Location) -> Path:
    """Save historical weather cache via store."""
    return store.write(
        location_paths(loc).historical_weather,
        {"by_date": weather_by_date},
        source="open-meteo.com (archive)",
        valid_until=datetime.now(UTC) + timedelta(hours=24),
        location=loc.slug,
    )


@task(name="fetch-gdd", retries=2, retry_delay_seconds=5)
def fetch_gdd(
    loc: Location,
    base_temp_f: float = 50.0,
    upper_cutoff_f: float = 86.0,
) -> dict[str, Any]:
    """Fetch temperature data and compute GDD for current and previous year.

    Fetches daily min/max temperatures from the Open-Meteo archive API,
    computes daily and accumulated GDD using the modified average method.

    Args:
        loc: The location whose weather point and timezone are used. The
            current year is taken from the location's local date.
        base_temp_f: GDD base temperature in Fahrenheit.
        upper_cutoff_f: GDD upper cutoff temperature in Fahrenheit.

    Returns:
        Dict with current_year, previous_year, and location metadata.
    """
    year = local_today(loc.timezone).year
    current = gdd.fetch_year_gdd(
        loc.lat,
        loc.lon,
        year,
        base_temp_f=base_temp_f,
        upper_cutoff_f=upper_cutoff_f,
        timezone=loc.timezone,
    )
    previous = gdd.fetch_year_gdd(
        loc.lat,
        loc.lon,
        year - 1,
        base_temp_f=base_temp_f,
        upper_cutoff_f=upper_cutoff_f,
        timezone=loc.timezone,
    )

    return {
        "location": {"slug": loc.slug, "lat": loc.lat, "lon": loc.lon},
        "base_temp_f": base_temp_f,
        "upper_cutoff_f": upper_cutoff_f,
        "current_year": gdd.year_gdd_to_dict(current),
        "previous_year": gdd.year_gdd_to_dict(previous),
    }


@task(name="save-gdd")
def save_gdd(gdd_data: dict[str, Any], loc: Location) -> Path:
    """Save GDD data via store."""
    return store.write(
        location_paths(loc).gdd,
        gdd_data,
        source="open-meteo.com (archive)",
        valid_until=datetime.now(UTC) + timedelta(hours=24),
        location=loc.slug,
    )


def _fetch_location(loc: Location) -> dict[str, Any]:  # noqa: PLR0915
    """Fetch every data source for one location, skipping fresh caches."""
    paths = location_paths(loc)
    results: dict[str, Any] = {}

    # --- Weather forecast ---
    if store.is_fresh(paths.weather):
        print(f"[{loc.slug}] Weather data is fresh, skipping fetch.")
        weather = store.read(paths.weather) or {}
    else:
        print(f"[{loc.slug}] Fetching weather for ({loc.lat}, {loc.lon})...")
        weather = fetch_weather(loc)
        output_path = save_weather(weather, loc)
        days = len(weather.get("daily", {}).get("time", []))
        print(f"[{loc.slug}] Saved {days} days of weather data to {output_path}")

    results["weather_days"] = len(weather.get("daily", {}).get("time", []))

    # --- Sunshine ---
    if store.is_fresh(paths.sunshine_15min) and store.is_fresh(paths.sunshine_16day):
        print(f"[{loc.slug}] Sunshine data is fresh, skipping fetch.")
        sunshine_15min = store.read(paths.sunshine_15min) or {}
        sunshine_16day = store.read(paths.sunshine_16day) or {}
    else:
        print(f"[{loc.slug}] Fetching sunshine data for ({loc.lat}, {loc.lon})...")
        sunshine_15min = fetch_sunshine_15min(loc)
        sunshine_16day = fetch_sunshine_16day(loc)
        save_sunshine(sunshine_15min, sunshine_16day, loc)

    results["sunshine_slots"] = len(sunshine_15min.get("minutely_15", {}).get("time", []))

    # --- iNaturalist ---
    if store.is_fresh(paths.inaturalist):
        print(f"[{loc.slug}] iNaturalist data is fresh, skipping fetch.")
        inat_data = store.read(paths.inaturalist) or {}
    else:
        print(f"[{loc.slug}] Fetching iNaturalist butterfly sightings...")
        inat_data = fetch_inaturalist(loc)
        inat_path = save_inaturalist(inat_data, loc)
        species_count = len(inat_data.get("species", []))
        print(f"[{loc.slug}] Saved {species_count} butterfly species to {inat_path}")

    results["inat_species"] = len(inat_data.get("species", []))

    # --- Historical weather ---
    obs_list = inat_data.get("observations", [])
    if store.is_fresh(paths.historical_weather):
        print(f"[{loc.slug}] Historical weather is fresh, skipping fetch.")
        hist_raw = store.read(paths.historical_weather) or {}
        hist_weather = hist_raw.get("by_date", {}) if isinstance(hist_raw, dict) else {}
    else:
        print(f"[{loc.slug}] Fetching historical weather for observation dates...")
        hist_weather = fetch_historical_weather(obs_list, loc)
        hist_path = save_historical_weather(hist_weather, loc)
        print(
            f"[{loc.slug}] Cached historical weather for {len(hist_weather)} dates to {hist_path}"
        )

    results["historical_weather_dates"] = len(hist_weather)

    # --- GDD ---
    if store.is_fresh(paths.gdd):
        print(f"[{loc.slug}] GDD data is fresh, skipping fetch.")
        gdd_data = store.read(paths.gdd) or {}
    else:
        print(f"[{loc.slug}] Fetching GDD data for ({loc.lat}, {loc.lon})...")
        gdd_data = fetch_gdd(loc)
        gdd_path = save_gdd(gdd_data, loc)
        current_gdd = gdd_data.get("current_year", {}).get("total_gdd", 0)
        print(f"[{loc.slug}] Saved GDD data ({current_gdd:.0f} accumulated) to {gdd_path}")

    results["current_gdd"] = gdd_data.get("current_year", {}).get("total_gdd", 0)

    return results


@flow(name="fetch-data", log_prints=True)
def fetch_all(location_slug: str = DEFAULT_LOCATION.slug) -> dict[str, Any]:
    """
    Fetch all data sources for one location.

    Checks freshness before fetching — skips sources that are still valid.

    Raises:
        KeyError: If ``location_slug`` is not a registered location.
    """
    return _fetch_location(get_location(location_slug))


@flow(name="fetch-all-locations", log_prints=True)
def fetch_all_locations() -> dict[str, dict[str, Any]]:
    """
    Fetch every registered location, one after another.

    Locations run in sequence so that they share the iNaturalist request
    throttle. A failure in one location is recorded as ``{"error": ...}``
    in its result and does not stop the others, so one broken data source
    cannot block every page from updating.
    """
    results: dict[str, dict[str, Any]] = {}
    for slug, loc in LOCATIONS.items():
        try:
            results[slug] = _fetch_location(loc)
        except Exception as exc:
            # GitHub Actions shows this line as a warning on the run summary,
            # so the failure stays visible while the job continues. It is
            # written to stderr directly because the flow's ``log_prints``
            # would add a log prefix, and the annotation must start the line.
            sys.stderr.write(f"::warning::Fetching {slug} failed: {exc!r}\n")
            results[slug] = {"error": repr(exc)}
    return results


def all_locations_failed(results: dict[str, dict[str, Any]] | None) -> bool:
    """Return True if ``fetch_all_locations`` recorded an error for every location.

    Entry points exit non-zero only in this case, so one failed location does
    not stop the others from updating.
    """
    return bool(results) and all("error" in r for r in results.values())


def main() -> int:
    """Fetch every location; return exit code 1 only if all of them failed."""
    results = fetch_all_locations()
    print(f"Flow complete: {results}")
    return 1 if all_locations_failed(results) else 0


if __name__ == "__main__":
    sys.exit(main())
