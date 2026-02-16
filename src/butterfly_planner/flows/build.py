"""
Prefect flow for building static site from raw data.

Transforms raw data into HTML pages for GitHub Pages.

Run locally:
    python -m butterfly_planner.flows.build
"""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo

from prefect import flow, task

from butterfly_planner.renderers import render_template
from butterfly_planner.renderers.gdd import build_gdd_timeline_html, build_gdd_today_html
from butterfly_planner.renderers.sightings_map import build_butterfly_map_html
from butterfly_planner.renderers.sightings_table import build_butterfly_sightings_html
from butterfly_planner.renderers.species_palette import build_species_palette
from butterfly_planner.renderers.sunshine import (
    build_sunshine_16day_html,
    build_sunshine_today_html,
)

# Directories
DATA_DIR = Path("data")
RAW_DIR = DATA_DIR / "raw"
SITE_DIR = Path("site")


# =============================================================================
# Data loading tasks
# =============================================================================


@task(name="load-weather")
def load_weather() -> dict[str, Any] | None:
    """Load raw weather data."""
    path = RAW_DIR / "weather.json"
    if not path.exists():
        return None
    with path.open() as f:
        result: dict[str, Any] = json.load(f)
        return result


@task(name="load-sunshine")
def load_sunshine() -> dict[str, Any] | None:
    """Load raw sunshine data."""
    path = RAW_DIR / "sunshine.json"
    if not path.exists():
        return None
    with path.open() as f:
        result: dict[str, Any] = json.load(f)
        return result


@task(name="load-inaturalist")
def load_inaturalist() -> dict[str, Any] | None:
    """Load raw iNaturalist data."""
    path = RAW_DIR / "inaturalist.json"
    if not path.exists():
        return None
    with path.open() as f:
        result: dict[str, Any] = json.load(f)
        return result


@task(name="load-historical-weather")
def load_historical_weather() -> dict[str, dict[str, Any]] | None:
    """Load cached historical weather keyed by date string."""
    path = RAW_DIR / "historical_weather.json"
    if not path.exists():
        return None
    with path.open() as f:
        raw: dict[str, Any] = json.load(f)
        by_date: dict[str, dict[str, Any]] = raw.get("by_date", {})
        return by_date


@task(name="load-gdd")
def load_gdd() -> dict[str, Any] | None:
    """Load raw GDD data."""
    path = RAW_DIR / "gdd.json"
    if not path.exists():
        return None
    with path.open() as f:
        result: dict[str, Any] = json.load(f)
        return result


# =============================================================================
# Main build task and flow
# =============================================================================


@task(name="build-html")
def build_html(
    weather_data: dict[str, Any],
    sunshine_data: dict[str, Any] | None,
    inat_data: dict[str, Any] | None = None,
    gdd_data: dict[str, Any] | None = None,
) -> str:
    """Build HTML page from weather, sunshine, iNaturalist, and GDD data."""
    fetched_dt = datetime.fromisoformat(weather_data["fetched_at"])
    pst = ZoneInfo("America/Los_Angeles")
    local_dt = fetched_dt.astimezone(pst)
    updated = local_dt.strftime("%Y-%m-%d %H:%M")

    sunshine_today_html = ""
    sunshine_16day_html = ""
    if sunshine_data:
        sunshine_today_html = build_sunshine_today_html(sunshine_data)
        sunshine_16day_html = build_sunshine_16day_html(sunshine_data, weather_data)

    butterfly_sightings_html = ""
    butterfly_map_html = ""
    map_script_html = ""
    if inat_data:
        species_list = inat_data.get("data", {}).get("species", [])
        palette = build_species_palette(species_list)
        butterfly_sightings_html = build_butterfly_sightings_html(inat_data, palette)

        hist_weather = load_historical_weather()
        butterfly_map_html, map_script_html = build_butterfly_map_html(
            inat_data, palette, hist_weather
        )

    gdd_today_html = ""
    gdd_timeline_html = ""
    if gdd_data:
        gdd_today_html = build_gdd_today_html(gdd_data)
        gdd_timeline_html = build_gdd_timeline_html(gdd_data)

    return render_template(
        "base.html.j2",
        updated=updated,
        sunshine_today=sunshine_today_html,
        sunshine_16day=sunshine_16day_html,
        butterfly_sightings=butterfly_sightings_html,
        butterfly_map=butterfly_map_html,
        map_script=map_script_html,
        gdd_today=gdd_today_html,
        gdd_timeline=gdd_timeline_html,
    )


@task(name="write-site")
def write_site(html: str) -> Path:
    """Write HTML to site directory."""
    SITE_DIR.mkdir(parents=True, exist_ok=True)
    output_path = SITE_DIR / "index.html"
    with output_path.open("w") as f:
        f.write(html)
    return output_path


@flow(name="build-site", log_prints=True)
def build_all() -> dict[str, Any]:
    """
    Build static site from raw data.

    This is the main Prefect flow that generates the static site.
    """
    print("Loading weather data...")
    weather = load_weather()

    if not weather:
        print("No weather data found. Run fetch flow first.")
        return {"error": "no data"}

    print("Loading sunshine data...")
    sunshine = load_sunshine()
    if not sunshine:
        print("Warning: No sunshine data found. Building without sunshine modules.")

    print("Loading iNaturalist data...")
    inat = load_inaturalist()
    if not inat:
        print("Warning: No iNaturalist data found. Building without butterfly sightings.")

    print("Loading GDD data...")
    gdd_data = load_gdd()
    if not gdd_data:
        print("Warning: No GDD data found. Building without growing degree days.")

    print("Building HTML...")
    html = build_html(weather, sunshine, inat, gdd_data)

    print("Writing site...")
    output_path = write_site(html)

    print(f"Site built: {output_path}")
    return {"pages": 1, "output": str(output_path)}


if __name__ == "__main__":
    result = build_all()
    print(f"Flow complete: {result}")
