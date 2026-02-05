"""
Prefect flow for building static site from raw data.

Transforms raw data into HTML pages for GitHub Pages.

Run locally:
    python -m butterfly_planner.flows.build
"""

from __future__ import annotations

import json
from collections.abc import Callable
from datetime import datetime
from pathlib import Path
from typing import Any, TypeVar
from zoneinfo import ZoneInfo

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


# Directories
DATA_DIR = Path("data")
RAW_DIR = DATA_DIR / "raw"
SITE_DIR = Path("site")

HTML_TEMPLATE = """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Butterfly Planner - Weather & Sunshine</title>
    <style>
        body {{ font-family: system-ui, sans-serif; max-width: 900px; margin: 2rem auto; padding: 0 1rem; }}
        h1 {{ color: #2d5016; }}
        h2 {{ color: #3d6026; margin-top: 2rem; }}
        table {{ border-collapse: collapse; width: 100%; }}
        th, td {{ border: 1px solid #ddd; padding: 8px; text-align: left; }}
        th {{ background: #f5f5f5; }}
        .meta {{ color: #666; font-size: 0.9rem; }}
        .temp-high {{ color: #c00; }}
        .temp-low {{ color: #00c; }}
        .sunshine-bar {{ display: inline-block; height: 20px; background: #ffd700; border-radius: 3px; }}
        .sunshine-grid {{ display: grid; grid-template-columns: repeat(12, 1fr); gap: 2px; margin: 1rem 0; }}
        .sunshine-slot {{ height: 30px; border-radius: 2px; }}
        .sunshine-none {{ background: #e0e0e0; }}
        .sunshine-low {{ background: #fff9c4; }}
        .sunshine-med {{ background: #ffeb3b; }}
        .sunshine-high {{ background: #ffc107; }}
        .sunshine-full {{ background: #ff9800; }}
        .good-day {{ background: #e8f5e9; }}
        .poor-day {{ background: #ffebee; }}
        .legend {{ display: flex; gap: 1rem; margin: 1rem 0; font-size: 0.85rem; }}
        .legend-item {{ display: flex; align-items: center; gap: 0.5rem; }}
        .legend-box {{ width: 20px; height: 20px; border-radius: 2px; }}
        .species-card {{ display: flex; align-items: center; gap: 1rem; padding: 0.75rem; border: 1px solid #e0e0e0; border-radius: 6px; margin-bottom: 0.5rem; }}
        .species-photo {{ width: 60px; height: 60px; border-radius: 4px; object-fit: cover; }}
        .species-photo-placeholder {{ width: 60px; height: 60px; border-radius: 4px; background: #f0f0f0; display: flex; align-items: center; justify-content: center; color: #999; font-size: 1.5rem; }}
        .species-info {{ flex: 1; }}
        .species-name {{ font-weight: 600; color: #2d5016; }}
        .species-scientific {{ font-style: italic; color: #666; font-size: 0.9rem; }}
        .species-count {{ color: #888; font-size: 0.85rem; }}
        .obs-bar {{ display: inline-block; height: 14px; background: #8bc34a; border-radius: 3px; margin-right: 0.5rem; vertical-align: middle; }}
    </style>
</head>
<body>
    <h1>🦋 Butterfly Planner</h1>
    <p class="meta">Weather forecast for Portland, OR | Last updated: {updated}</p>

    {sunshine_today}

    {sunshine_16day}

    {butterfly_sightings}

    <h2>7-Day Weather Forecast</h2>
    <table>
        <tr>
            <th>Date</th>
            <th>High</th>
            <th>Low</th>
            <th>Precip</th>
        </tr>
        {weather_rows}
    </table>

    <h2>About</h2>
    <p>This page shows sunshine forecasts to help plan butterfly viewing trips. Butterflies are most active during sunny periods.</p>
    <p><strong>Good butterfly weather:</strong> &gt;3 hours of sunshine OR &gt;40% of daylight is sunny.</p>
    <ul>
        <li>Butterfly hotspots by week</li>
        <li>Species diversity maps</li>
        <li>Drive-time isochrones</li>
        <li>Nearby campgrounds</li>
    </ul>

    <p class="meta">Data from <a href="https://open-meteo.com">Open-Meteo</a> and <a href="https://www.inaturalist.org">iNaturalist</a></p>
</body>
</html>
"""


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


def c_to_f(celsius: float) -> float:
    """Convert Celsius to Fahrenheit."""
    return celsius * 9 / 5 + 32


def build_sunshine_today_html(sunshine_data: dict[str, Any]) -> str:
    """Build HTML for Module 1: Today's 15-minute sunshine."""
    minutely = sunshine_data["today_15min"].get("minutely_15", {})
    times = minutely.get("time", [])
    durations = minutely.get("sunshine_duration", [])
    is_day = minutely.get("is_day", [])

    if not times:
        return "<p>No 15-minute sunshine data available.</p>"

    # Filter to daylight hours only
    daylight_slots = [(times[i], durations[i]) for i in range(len(times)) if is_day[i]]

    if not daylight_slots:
        return "<p>No daylight hours in forecast.</p>"

    # Calculate total sunshine
    total_sunshine_sec = sum(dur for _, dur in daylight_slots)
    total_sunshine_hours = total_sunshine_sec / 3600

    # Build grid visualization
    grid_html = []
    for time_str, duration in daylight_slots:
        dt = datetime.fromisoformat(time_str)
        pct = (duration / 900) * 100  # 900 sec = 15 min

        # Color based on percentage
        if pct == 0:
            color_class = "sunshine-none"
        elif pct < 25:
            color_class = "sunshine-low"
        elif pct < 50:
            color_class = "sunshine-med"
        elif pct < 75:
            color_class = "sunshine-high"
        else:
            color_class = "sunshine-full"

        title = f"{dt.strftime('%I:%M %p')}: {duration / 60:.0f} min"
        grid_html.append(f'<div class="sunshine-slot {color_class}" title="{title}"></div>')

    # Legend
    legend = """
    <div class="legend">
        <div class="legend-item"><div class="legend-box sunshine-none"></div> None</div>
        <div class="legend-item"><div class="legend-box sunshine-low"></div> 0-25%</div>
        <div class="legend-item"><div class="legend-box sunshine-med"></div> 25-50%</div>
        <div class="legend-item"><div class="legend-box sunshine-high"></div> 50-75%</div>
        <div class="legend-item"><div class="legend-box sunshine-full"></div> 75-100%</div>
    </div>
    """

    today_date = datetime.fromisoformat(daylight_slots[0][0]).strftime("%B %d")

    return f"""
    <h2>☀️ Today's Sun Breaks ({today_date})</h2>
    <p>Total sunshine expected: <strong>{total_sunshine_hours:.1f} hours</strong></p>
    {legend}
    <div class="sunshine-grid">
        {"".join(grid_html)}
    </div>
    <p class="meta">Each block = 15 minutes. Hover for time and duration.</p>
    """


def build_sunshine_16day_html(sunshine_data: dict[str, Any]) -> str:
    """Build HTML for Module 2: 16-day daily sunshine."""
    daily = sunshine_data["daily_16day"].get("daily", {})
    dates = daily.get("time", [])
    sunshine_secs = daily.get("sunshine_duration", [])
    daylight_secs = daily.get("daylight_duration", [])

    if not dates:
        return "<p>No 16-day sunshine data available.</p>"

    rows = []
    for i, date_str in enumerate(dates):
        sunshine_hours = sunshine_secs[i] / 3600
        daylight_hours = daylight_secs[i] / 3600
        sunshine_pct = (sunshine_secs[i] / daylight_secs[i] * 100) if daylight_secs[i] > 0 else 0

        # Determine if good butterfly weather
        is_good = sunshine_hours > 3.0 or sunshine_pct > 40.0
        row_class = "good-day" if is_good else ""
        indicator = "☀️ Good" if is_good else ""

        # Sunshine bar visualization
        bar_width = int(sunshine_pct * 3)  # Scale to 300px max
        bar = f'<div class="sunshine-bar" style="width: {bar_width}px;"></div>'

        rows.append(
            f'<tr class="{row_class}">'
            f"<td>{date_str}</td>"
            f"<td>{sunshine_hours:.1f}h</td>"
            f"<td>{daylight_hours:.1f}h</td>"
            f"<td>{sunshine_pct:.0f}% {bar}</td>"
            f"<td>{indicator}</td>"
            f"</tr>"
        )

    return f"""
    <h2>📅 16-Day Sunshine Forecast</h2>
    <table>
        <tr>
            <th>Date</th>
            <th>Sunshine</th>
            <th>Daylight</th>
            <th>% Sunny</th>
            <th>Conditions</th>
        </tr>
        {"".join(rows)}
    </table>
    <p class="meta">Green rows indicate good butterfly weather (&gt;3h sun or &gt;40% sunny).</p>
    """


MONTH_NAMES = [
    "",
    "January",
    "February",
    "March",
    "April",
    "May",
    "June",
    "July",
    "August",
    "September",
    "October",
    "November",
    "December",
]


def build_butterfly_sightings_html(inat_data: dict[str, Any]) -> str:
    """Build HTML for butterfly species sightings from iNaturalist."""
    data = inat_data.get("data", {})
    species_list: list[dict[str, Any]] = data.get("species", [])
    month = data.get("month", 0)

    if not species_list:
        return "<p>No butterfly sightings data available.</p>"

    month_name = MONTH_NAMES[month] if 1 <= month <= 12 else "this month"

    # Show top 15 species
    top_species = sorted(species_list, key=lambda s: s["observation_count"], reverse=True)[:15]
    max_count = top_species[0]["observation_count"] if top_species else 1

    cards = []
    for sp in top_species:
        name = sp.get("common_name") or sp["scientific_name"]
        scientific = sp["scientific_name"]
        count = sp["observation_count"]
        photo_url = sp.get("photo_url")
        taxon_url = sp.get("taxon_url", "")

        # Observation bar (scaled to max)
        bar_width = int((count / max_count) * 200) if max_count > 0 else 0

        if photo_url:
            photo_html = f'<img class="species-photo" src="{photo_url}" alt="{name}">'
        else:
            photo_html = '<div class="species-photo-placeholder">&#x1f98b;</div>'

        name_html = f'<a href="{taxon_url}">{name}</a>' if taxon_url else name

        cards.append(
            f'<div class="species-card">'
            f"{photo_html}"
            f'<div class="species-info">'
            f'<div class="species-name">{name_html}</div>'
            f'<div class="species-scientific">{scientific}</div>'
            f'<div class="species-count">'
            f'<div class="obs-bar" style="width: {bar_width}px;"></div>'
            f"{count} research-grade observations</div>"
            f"</div></div>"
        )

    return f"""
    <h2>Butterfly Sightings - {month_name}</h2>
    <p>Butterfly species observed in NW Oregon / SW Washington during {month_name}
    (all years, research-grade observations from
    <a href="https://www.inaturalist.org">iNaturalist</a>).</p>
    {"".join(cards)}
    <p class="meta">Data from iNaturalist community observations.
    Observation counts reflect all years combined for {month_name}.</p>
    """


@task(name="build-html")
def build_html(
    weather_data: dict[str, Any],
    sunshine_data: dict[str, Any] | None,
    inat_data: dict[str, Any] | None = None,
) -> str:
    """Build HTML page from weather, sunshine, and iNaturalist data."""
    data = weather_data["data"]["daily"]

    # Convert timestamp to local time (PST)
    fetched_dt = datetime.fromisoformat(weather_data["fetched_at"])
    pst = ZoneInfo("America/Los_Angeles")
    local_dt = fetched_dt.astimezone(pst)
    updated = local_dt.strftime("%Y-%m-%d %H:%M")

    # Build weather table
    weather_rows = []
    for i, date in enumerate(data["time"]):
        high_c = data["temperature_2m_max"][i]
        low_c = data["temperature_2m_min"][i]
        high_f = c_to_f(high_c)
        low_f = c_to_f(low_c)
        precip = data["precipitation_sum"][i]
        weather_rows.append(
            f"<tr><td>{date}</td>"
            f'<td class="temp-high">{high_c:.1f}°C ({high_f:.0f}°F)</td>'
            f'<td class="temp-low">{low_c:.1f}°C ({low_f:.0f}°F)</td>'
            f"<td>{precip}mm</td></tr>"
        )

    # Build sunshine sections
    sunshine_today_html = ""
    sunshine_16day_html = ""
    if sunshine_data:
        sunshine_today_html = build_sunshine_today_html(sunshine_data)
        sunshine_16day_html = build_sunshine_16day_html(sunshine_data)

    # Build butterfly sightings section
    butterfly_sightings_html = ""
    if inat_data:
        butterfly_sightings_html = build_butterfly_sightings_html(inat_data)

    return HTML_TEMPLATE.format(
        updated=updated,
        sunshine_today=sunshine_today_html,
        sunshine_16day=sunshine_16day_html,
        butterfly_sightings=butterfly_sightings_html,
        weather_rows="\n        ".join(weather_rows),
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

    print("Building HTML...")
    html = build_html(weather, sunshine, inat)

    print("Writing site...")
    output_path = write_site(html)

    print(f"Site built: {output_path}")
    return {"pages": 1, "output": str(output_path)}


if __name__ == "__main__":
    result = build_all()
    print(f"Flow complete: {result}")
