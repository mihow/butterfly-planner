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
        .hour-bar {{ display: inline-flex; gap: 1px; vertical-align: middle; }}
        .hour-seg {{ width: 16px; height: 18px; border-radius: 2px; }}
        .legend {{ display: flex; gap: 1rem; margin: 1rem 0; font-size: 0.85rem; }}
        .legend-item {{ display: flex; align-items: center; gap: 0.5rem; }}
        .legend-box {{ width: 20px; height: 20px; border-radius: 2px; }}
    </style>
</head>
<body>
    <h1>🦋 Butterfly Planner</h1>
    <p class="meta">Weather forecast for Portland, OR | Last updated: {updated}</p>

    {sunshine_today}

    {sunshine_16day}

    <h2>About</h2>
    <p>This page shows sunshine forecasts to help plan butterfly viewing trips. Butterflies are most active during sunny periods.</p>
    <p><strong>Good butterfly weather:</strong> &gt;3 hours of sunshine OR &gt;40% of daylight is sunny.</p>
    <ul>
        <li>Butterfly hotspots by week</li>
        <li>Species diversity maps</li>
        <li>Drive-time isochrones</li>
        <li>Nearby campgrounds</li>
    </ul>

    <p class="meta">Data from <a href="https://open-meteo.com">Open-Meteo</a></p>
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


def c_to_f(celsius: float) -> float:
    """Convert Celsius to Fahrenheit."""
    return celsius * 9 / 5 + 32


# WMO Weather Interpretation Codes (https://open-meteo.com/en/docs)
WMO_CONDITIONS: dict[int, str] = {
    0: "\u2600\ufe0f Clear",
    1: "\U0001f324\ufe0f Mostly Clear",
    2: "\u26c5 Partly Cloudy",
    3: "\u2601\ufe0f Overcast",
    45: "\U0001f32b\ufe0f Fog",
    48: "\U0001f32b\ufe0f Freezing Fog",
    51: "\U0001f326\ufe0f Light Drizzle",
    53: "\U0001f326\ufe0f Drizzle",
    55: "\U0001f326\ufe0f Heavy Drizzle",
    56: "\U0001f9ca Light Freezing Drizzle",
    57: "\U0001f9ca Freezing Drizzle",
    61: "\U0001f327\ufe0f Light Rain",
    63: "\U0001f327\ufe0f Rain",
    65: "\U0001f327\ufe0f Heavy Rain",
    66: "\U0001f9ca Light Freezing Rain",
    67: "\U0001f9ca Freezing Rain",
    71: "\U0001f328\ufe0f Light Snow",
    73: "\U0001f328\ufe0f Snow",
    75: "\U0001f328\ufe0f Heavy Snow",
    77: "\U0001f328\ufe0f Snow Grains",
    80: "\U0001f326\ufe0f Light Showers",
    81: "\U0001f327\ufe0f Showers",
    82: "\U0001f327\ufe0f Heavy Showers",
    85: "\U0001f328\ufe0f Light Snow Showers",
    86: "\U0001f328\ufe0f Snow Showers",
    95: "\u26c8\ufe0f Thunderstorm",
    96: "\u26c8\ufe0f Thunderstorm w/ Hail",
    99: "\u26c8\ufe0f Heavy Thunderstorm",
}


def wmo_code_to_conditions(code: int) -> str:
    """Convert a WMO weather code to a human-readable condition string."""
    return WMO_CONDITIONS.get(code, f"Unknown ({code})")


def build_sunshine_today_html(sunshine_data: dict[str, Any]) -> str:
    """Build HTML for Module 1: Today's 15-minute sunshine."""
    minutely = sunshine_data["today_15min"].get("minutely_15", {})
    times = minutely.get("time", [])
    durations = minutely.get("sunshine_duration", [])
    is_day = minutely.get("is_day", [])

    if not times:
        return "<p>No 15-minute sunshine data available.</p>"

    # Determine today's date (first date in the data)
    today_str = times[0][:10]  # "YYYY-MM-DD"

    # Filter to today's daylight hours only
    daylight_slots = [
        (times[i], durations[i])
        for i in range(len(times))
        if is_day[i] and times[i][:10] == today_str
    ]

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


def _group_15min_by_date(
    sunshine_data: dict[str, Any],
) -> dict[str, list[tuple[str, int, bool]]]:
    """Group 15-minute sunshine slots by date.

    Returns a dict mapping date strings (YYYY-MM-DD) to lists of
    (time_iso, duration_seconds, is_day) tuples.
    """
    minutely = sunshine_data.get("today_15min", {}).get("minutely_15", {})
    times = minutely.get("time", [])
    durations = minutely.get("sunshine_duration", [])
    is_day = minutely.get("is_day", [])

    by_date: dict[str, list[tuple[str, int, bool]]] = {}
    for i, time_str in enumerate(times):
        date_str = time_str[:10]  # "YYYY-MM-DD"
        by_date.setdefault(date_str, []).append((time_str, durations[i], bool(is_day[i])))
    return by_date


def _build_hourly_bar(slots: list[tuple[str, int, bool]]) -> str:
    """Build an inline hourly sunshine bar from 15-min slot data.

    Groups daylight 15-min slots into hours and renders a compact
    colored bar showing sunshine intensity throughout the day.
    """
    # Filter to daylight only
    daylight = [(t, d) for t, d, is_day in slots if is_day]
    if not daylight:
        return ""

    # Group into hours: sum sunshine seconds per hour
    hours: dict[int, int] = {}
    for time_str, dur in daylight:
        dt = datetime.fromisoformat(time_str)
        hours.setdefault(dt.hour, 0)
        hours[dt.hour] += dur

    if not hours:
        return ""

    first_hour = min(hours)
    last_hour = max(hours)

    segments = []
    for h in range(first_hour, last_hour + 1):
        sun_secs = hours.get(h, 0)
        # Max possible per hour = 3600 sec (4 slots x 900 sec)
        pct = (sun_secs / 3600) * 100 if sun_secs else 0
        if pct == 0:
            color = "#e0e0e0"
        elif pct < 25:
            color = "#fff9c4"
        elif pct < 50:
            color = "#ffeb3b"
        elif pct < 75:
            color = "#ffc107"
        else:
            color = "#ff9800"

        dt_hour = datetime.fromisoformat(daylight[0][0]).replace(hour=h, minute=0)
        title = f"{dt_hour.strftime('%I %p')}: {sun_secs / 60:.0f}min sun"
        segments.append(f'<div class="hour-seg" style="background:{color};" title="{title}"></div>')

    return f'<div class="hour-bar">{"".join(segments)}</div>'


def build_sunshine_16day_html(
    sunshine_data: dict[str, Any], weather_data: dict[str, Any] | None = None
) -> str:
    """Build HTML for the merged 16-day forecast (sunshine + weather)."""
    daily = sunshine_data["daily_16day"].get("daily", {})
    dates = daily.get("time", [])
    sunshine_secs = daily.get("sunshine_duration", [])
    daylight_secs = daily.get("daylight_duration", [])

    if not dates:
        return "<p>No 16-day sunshine data available.</p>"

    # Build a lookup from weather data keyed by date string
    weather_by_date: dict[str, dict[str, Any]] = {}
    if weather_data:
        w_daily = weather_data.get("data", {}).get("daily", {})
        w_dates = w_daily.get("time", [])
        for j, w_date in enumerate(w_dates):
            weather_by_date[w_date] = {
                "high_c": w_daily.get("temperature_2m_max", [None])[j],
                "low_c": w_daily.get("temperature_2m_min", [None])[j],
                "precip_mm": w_daily.get("precipitation_sum", [None])[j],
                "weather_code": w_daily.get("weather_code", [None])[j],
            }

    # Group 15-min slots by date for granular bar charts
    slots_by_date = _group_15min_by_date(sunshine_data)

    rows = []
    for i, date_str in enumerate(dates):
        sunshine_hours = sunshine_secs[i] / 3600
        daylight_hours = daylight_secs[i] / 3600
        sunshine_pct = (sunshine_secs[i] / daylight_secs[i] * 100) if daylight_secs[i] > 0 else 0

        # Determine if good butterfly weather
        is_good = sunshine_hours > 3.0 or sunshine_pct > 40.0
        row_class = "good-day" if is_good else ""

        # Sunshine bar: hourly detail if 15-min data available, else simple bar
        day_slots = slots_by_date.get(date_str)
        if day_slots:
            bar = _build_hourly_bar(day_slots)
        else:
            bar_width = int(sunshine_pct * 3)  # Scale to 300px max
            bar = f'<div class="sunshine-bar" style="width: {bar_width}px;"></div>'

        # Weather columns (from merged data)
        w = weather_by_date.get(date_str)
        if w and w["high_c"] is not None:
            high_c = w["high_c"]
            low_c = w["low_c"]
            temp_cell = (
                f'<td><span class="temp-high">{high_c:.0f}\u00b0C</span> / '
                f'<span class="temp-low">{low_c:.0f}\u00b0C</span></td>'
            )
            precip_mm = w["precip_mm"] if w["precip_mm"] is not None else 0
            precip_cell = f"<td>{precip_mm:.1f}mm</td>"
        else:
            temp_cell = "<td>\u2014</td>"
            precip_cell = "<td>\u2014</td>"

        # Conditions from WMO weather code
        if w and w["weather_code"] is not None:
            conditions = wmo_code_to_conditions(w["weather_code"])
        else:
            conditions = "\u2014"

        rows.append(
            f'<tr class="{row_class}">'
            f"<td>{date_str}</td>"
            f"<td>{sunshine_hours:.1f}h of {daylight_hours:.1f}h</td>"
            f"<td>{sunshine_pct:.0f}% {bar}</td>"
            f"{temp_cell}"
            f"{precip_cell}"
            f"<td>{conditions}</td>"
            f"</tr>"
        )

    return f"""
    <h2>\U0001f4c5 16-Day Sunshine Forecast</h2>
    <table>
        <tr>
            <th>Date</th>
            <th>Sun</th>
            <th>% Sunny</th>
            <th>High / Low</th>
            <th>Precip</th>
            <th>Conditions</th>
        </tr>
        {"".join(rows)}
    </table>
    <p class="meta">Green rows indicate good butterfly weather (&gt;3h sun or &gt;40% sunny).
    Hover over hourly bars for detail.</p>
    """


@task(name="build-html")
def build_html(weather_data: dict[str, Any], sunshine_data: dict[str, Any] | None) -> str:
    """Build HTML page from weather and sunshine data."""
    # Convert timestamp to local time (PST)
    fetched_dt = datetime.fromisoformat(weather_data["fetched_at"])
    pst = ZoneInfo("America/Los_Angeles")
    local_dt = fetched_dt.astimezone(pst)
    updated = local_dt.strftime("%Y-%m-%d %H:%M")

    # Build sunshine sections (16-day now includes merged weather data)
    sunshine_today_html = ""
    sunshine_16day_html = ""
    if sunshine_data:
        sunshine_today_html = build_sunshine_today_html(sunshine_data)
        sunshine_16day_html = build_sunshine_16day_html(sunshine_data, weather_data)

    return HTML_TEMPLATE.format(
        updated=updated,
        sunshine_today=sunshine_today_html,
        sunshine_16day=sunshine_16day_html,
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

    print("Building HTML...")
    html = build_html(weather, sunshine)

    print("Writing site...")
    output_path = write_site(html)

    print(f"Site built: {output_path}")
    return {"pages": 1, "output": str(output_path)}


if __name__ == "__main__":
    result = build_all()
    print(f"Flow complete: {result}")
