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

# Directories
DATA_DIR = Path("data")
RAW_DIR = DATA_DIR / "raw"
SITE_DIR = Path("site")

HTML_TEMPLATE = """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Butterfly Planner &mdash; Sunshine &amp; Weather Forecast</title>
    <link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css"
          integrity="sha256-p4NxAoJBhIIN+hmNHrzRCf9tD/miZyoHS5obTRR9BMY="
          crossorigin="" />
    <style>
        *, *::before, *::after {{ box-sizing: border-box; margin: 0; padding: 0; }}
        body {{
            font-family: Georgia, 'Times New Roman', Times, serif;
            line-height: 1.7;
            color: #222;
            max-width: 860px;
            margin: 0 auto;
            padding: 3rem 1.5rem;
        }}
        a {{ color: #222; text-decoration: none; border-bottom: 1px solid #ccc; transition: border-color 0.2s; }}
        a:hover {{ border-bottom-color: #222; }}

        /* --- Header --- */
        header {{
            text-align: center;
            padding-bottom: 1.5rem;
            margin-bottom: 2rem;
            border-bottom: 1px solid #ddd;
        }}
        header h1 {{
            font-size: 1.8rem;
            font-weight: normal;
            letter-spacing: 0.02em;
            color: #222;
        }}
        header .subtitle {{
            font-size: 1rem;
            font-style: italic;
            color: #555;
            margin-top: 0.25rem;
        }}
        header .updated {{
            font-size: 0.85rem;
            color: #888;
            margin-top: 0.5rem;
        }}

        /* --- Section headings --- */
        h2 {{
            font-size: 1.15rem;
            font-weight: normal;
            text-transform: uppercase;
            letter-spacing: 0.05em;
            color: #444;
            margin: 2.5rem 0 1rem;
            padding-bottom: 0.4rem;
            border-bottom: 1px solid #eee;
        }}

        /* --- Body text --- */
        p {{ margin: 0.8rem 0; font-size: 0.95rem; }}
        .meta {{ color: #666; font-size: 0.85rem; font-style: italic; }}
        strong {{ font-weight: 600; }}

        /* --- Data table --- */
        table {{
            border-collapse: collapse;
            width: 100%;
            font-size: 0.9rem;
            margin: 1rem 0;
        }}
        thead th {{
            background: #f8f9fa;
            border-bottom: 2px solid #ddd;
            font-size: 0.75rem;
            font-weight: 600;
            text-transform: uppercase;
            letter-spacing: 0.04em;
            color: #555;
            padding: 0.6rem 0.75rem;
            text-align: left;
        }}
        tbody td {{
            padding: 0.55rem 0.75rem;
            border-bottom: 1px solid #eee;
            vertical-align: middle;
        }}
        tbody tr:hover {{ background: #f8f9fa; }}
        tbody tr.good-day {{ background: #f2f7f0; }}
        tbody tr.good-day:hover {{ background: #e8f0e4; }}
        .temp-high {{ color: #9a3412; font-variant-numeric: tabular-nums; }}
        .temp-low {{ color: #1e40af; font-variant-numeric: tabular-nums; }}
        .numeric {{ font-family: 'SF Mono', 'Consolas', 'Liberation Mono', Menlo, monospace; font-size: 0.85rem; }}

        /* --- Sunshine timeline (today) --- */
        .timeline {{ margin: 1.25rem 0; }}
        .tl-labels {{ position: relative; height: 1.4em; font-size: 0.75rem; color: #888; letter-spacing: 0.02em; }}
        .tl-label {{ position: absolute; transform: translateX(-50%); }}
        .tl-bar {{ display: flex; gap: 1px; border-radius: 3px; overflow: hidden; height: 28px; border: 1px solid #e0e0e0; }}
        .tl-seg {{ flex: 1; min-width: 0; transition: opacity 0.15s; }}
        .tl-seg:hover {{ opacity: 0.65; }}

        /* --- Sunshine color scale (muted, scientific palette) --- */
        .sunshine-none {{ background: #e8e8e8; }}
        .sunshine-low  {{ background: #f5eec2; }}
        .sunshine-med  {{ background: #e8d44d; }}
        .sunshine-high {{ background: #d4a017; }}
        .sunshine-full {{ background: #b8860b; }}

        /* --- Inline hourly bar (16-day table) --- */
        .hour-bar {{ display: inline-flex; gap: 1px; vertical-align: middle; }}
        .hour-seg {{ width: 14px; height: 16px; border-radius: 1px; }}

        /* --- Legend --- */
        .legend {{
            display: flex;
            gap: 1.25rem;
            margin: 1rem 0;
            font-size: 0.8rem;
            color: #666;
            flex-wrap: wrap;
        }}
        .legend-item {{ display: flex; align-items: center; gap: 0.4rem; }}
        .legend-box {{ width: 16px; height: 16px; border-radius: 2px; border: 1px solid #ddd; }}

        /* --- Summary stats --- */
        .summary {{
            font-size: 0.95rem;
            margin: 0.75rem 0;
        }}
        .summary strong {{
            font-family: 'SF Mono', 'Consolas', 'Liberation Mono', Menlo, monospace;
            font-size: 0.9rem;
        }}

        /* --- Species sightings table --- */
        .species-photo {{ width: 48px; height: 48px; border-radius: 3px; object-fit: cover; vertical-align: middle; }}
        .species-photo-placeholder {{ display: inline-block; width: 48px; height: 48px; border-radius: 3px; background: #f0f0f0; text-align: center; line-height: 48px; color: #aaa; font-size: 1.2rem; vertical-align: middle; }}
        .species-scientific {{ font-style: italic; }}
        .obs-bar {{ display: inline-block; height: 12px; background: #8faa7b; border-radius: 2px; margin-right: 0.4rem; vertical-align: middle; }}
        td.obs-count {{ font-family: 'SF Mono', 'Consolas', 'Liberation Mono', Menlo, monospace; font-size: 0.85rem; white-space: nowrap; }}

        /* --- Sightings map --- */
        #sightings-map {{
            height: 420px;
            border-radius: 4px;
            border: 1px solid #ddd;
            margin: 1rem 0;
        }}

        /* --- About section --- */
        .about p {{ text-align: justify; font-size: 0.92rem; }}
        .about ul {{
            margin: 0.75rem 0 0.75rem 1.5rem;
            font-size: 0.92rem;
        }}
        .about li {{ margin: 0.3rem 0; }}
        .criteria {{
            font-size: 0.88rem;
            color: #444;
            background: #f8f9fa;
            padding: 0.75rem 1rem;
            border-left: 3px solid #ddd;
            margin: 1rem 0;
        }}

        /* --- Footer --- */
        footer {{
            margin-top: 3rem;
            padding-top: 1.25rem;
            border-top: 1px solid #ddd;
            text-align: center;
            font-size: 0.85rem;
            color: #888;
        }}

        /* --- Print --- */
        @media print {{
            body {{ max-width: none; padding: 1rem; }}
            header, footer {{ border: none; }}
        }}
    </style>
</head>
<body>
    <header>
        <h1>Butterfly Planner</h1>
        <div class="subtitle">Sunshine &amp; Weather Forecast &mdash; Portland, OR</div>
        <div class="updated">Last updated {updated} PST</div>
    </header>

    <main>
    {sunshine_today}

    {sunshine_16day}

    {butterfly_map}

    {butterfly_sightings}

    <h2>About</h2>
    <div class="about">
        <p>This page presents sunshine and weather forecasts to aid in planning
        butterfly observation outings. Lepidoptera are most active during periods
        of direct sunshine and warm temperatures.</p>
        <div class="criteria">
            <strong>Good butterfly weather</strong> is defined as &gt;3 hours of sunshine
            <em>or</em> &gt;40% of available daylight being sunny.
        </div>
        <p>Planned features:</p>
        <ul>
            <li>Butterfly abundance hotspots by week of year</li>
            <li>Species diversity maps for Oregon &amp; Washington</li>
            <li>Drive-time isochrone analysis</li>
            <li>Nearby campground locations</li>
        </ul>
    </div>
    </main>

    <footer>
        <p>Data provided by <a href="https://open-meteo.com">Open-Meteo</a>
        and <a href="https://www.inaturalist.org">iNaturalist</a>.
        Forecast models may not reflect actual conditions.</p>
    </footer>

    <script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"
            integrity="sha256-20nQCchB9co0qIjJZRGuk2/Z9VM+kNiyxNV1lvTlZBo="
            crossorigin=""></script>
    {map_script}
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


def _sunshine_color_class(pct: float) -> str:
    """Return CSS class name for a sunshine percentage (0-100)."""
    if pct == 0:
        return "sunshine-none"
    if pct < 25:
        return "sunshine-low"
    if pct < 50:
        return "sunshine-med"
    if pct < 75:
        return "sunshine-high"
    return "sunshine-full"


def build_sunshine_today_html(sunshine_data: dict[str, Any]) -> str:
    """Build HTML for today's sunshine as a horizontal timeline bar.

    Renders a full-width bar from sunrise to sunset where each 15-min
    segment is proportionally sized and colored by sunshine intensity.
    Hour labels are positioned above for time orientation.
    """
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

    n_slots = len(daylight_slots)

    # Calculate total sunshine
    total_sunshine_sec = sum(dur for _, dur in daylight_slots)
    total_sunshine_hours = total_sunshine_sec / 3600

    # Build timeline segments
    segments = []
    for time_str, duration in daylight_slots:
        dt = datetime.fromisoformat(time_str)
        pct = (duration / 900) * 100  # 900 sec = 15 min
        color_class = _sunshine_color_class(pct)
        title = f"{dt.strftime('%I:%M %p')}: {duration / 60:.0f} min sun"
        segments.append(f'<div class="tl-seg {color_class}" title="{title}"></div>')

    # Build hour labels positioned above the bar
    labels = []
    seen_hours: set[int] = set()
    for idx, (time_str, _) in enumerate(daylight_slots):
        dt = datetime.fromisoformat(time_str)
        if dt.hour not in seen_hours:
            seen_hours.add(dt.hour)
            left_pct = (idx / n_slots) * 100
            label_text = dt.strftime("%-I%p").lower()
            labels.append(
                f'<span class="tl-label" style="left:{left_pct:.1f}%">{label_text}</span>'
            )

    sunrise_dt = datetime.fromisoformat(daylight_slots[0][0])
    sunset_dt = datetime.fromisoformat(daylight_slots[-1][0])
    sunrise_str = sunrise_dt.strftime("%-I:%M %p")
    sunset_str = sunset_dt.strftime("%-I:%M %p")

    today_date = sunrise_dt.strftime("%B %d")

    legend = """
    <div class="legend">
        <div class="legend-item"><div class="legend-box sunshine-none"></div> No sun</div>
        <div class="legend-item"><div class="legend-box sunshine-low"></div> &lt;25%</div>
        <div class="legend-item"><div class="legend-box sunshine-med"></div> 25&ndash;50%</div>
        <div class="legend-item"><div class="legend-box sunshine-high"></div> 50&ndash;75%</div>
        <div class="legend-item"><div class="legend-box sunshine-full"></div> 75&ndash;100%</div>
    </div>
    """

    return f"""
    <h2>Today's Sun Breaks &mdash; {today_date}</h2>
    <p class="summary">Total sunshine expected: <strong>{total_sunshine_hours:.1f} hours</strong>
    &mdash; Sunrise {sunrise_str}, Sunset {sunset_str}</p>
    {legend}
    <div class="timeline">
        <div class="tl-labels">
            {"".join(labels)}
        </div>
        <div class="tl-bar">
            {"".join(segments)}
        </div>
    </div>
    <p class="meta">Each segment represents 15 minutes. Hover for exact time and duration.</p>
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
            color = "#e8e8e8"
        elif pct < 25:
            color = "#f5eec2"
        elif pct < 50:
            color = "#e8d44d"
        elif pct < 75:
            color = "#d4a017"
        else:
            color = "#b8860b"

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
        sun_sec = sunshine_secs[i] if sunshine_secs[i] is not None else 0
        day_sec = daylight_secs[i] if daylight_secs[i] is not None else 0
        sunshine_hours = sun_sec / 3600
        daylight_hours = day_sec / 3600
        sunshine_pct = (sun_sec / day_sec * 100) if day_sec > 0 else 0

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
    <h2>16-Day Sunshine Forecast</h2>
    <table>
        <thead>
        <tr>
            <th>Date</th>
            <th>Sunshine</th>
            <th>% Sunny</th>
            <th>High / Low</th>
            <th>Precip</th>
            <th>Conditions</th>
        </tr>
        </thead>
        <tbody>
        {"".join(rows)}
        </tbody>
    </table>
    <p class="meta">Highlighted rows indicate good butterfly weather
    (&gt;3 h sunshine or &gt;40% sunny). Hover hourly bars for detail.</p>
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


def _inat_obs_url(taxon_id: int, month: int) -> str:
    """Build an iNaturalist observation search URL for a taxon in the target region."""
    return (
        f"https://www.inaturalist.org/observations"
        f"?taxon_id={taxon_id}&month={month}"
        f"&quality_grade=research&verifiable=true"
        f"&swlat=44.5&swlng=-124.2&nelat=46.5&nelng=-121.5"
    )


def _week_label(weeks: list[int]) -> str:
    """Human-readable label for a list of ISO weeks, e.g. 'weeks 5\u20137'."""
    if not weeks:
        return "this week"
    if len(weeks) == 1:
        return f"week {weeks[0]}"
    return f"weeks {weeks[0]}\u2013{weeks[-1]}"


def build_butterfly_map_html(inat_data: dict[str, Any]) -> tuple[str, str]:
    """Build an interactive Leaflet map of butterfly observations.

    Returns a (map_div_html, map_script_js) tuple. The script must be placed
    after the Leaflet library is loaded.
    """
    data = inat_data.get("data", {})
    observations: list[dict[str, Any]] = data.get("observations", [])
    weeks: list[int] = data.get("weeks", [])

    label = _week_label(weeks)

    if not observations:
        return (
            f"<h2>Butterfly Sightings Map &mdash; {label.title()}</h2>"
            "<p>No observation data available for the map.</p>",
            "",
        )

    # Build JS array of observation markers
    markers_js_parts: list[str] = []
    for obs in observations:
        lat = obs.get("latitude")
        lon = obs.get("longitude")
        name = obs.get("common_name") or obs.get("species", "Unknown")
        species = obs.get("species", "")
        obs_date = obs.get("observed_on", "")
        url = obs.get("url", "")
        if lat is not None and lon is not None:
            # Escape for JS string
            safe_name = name.replace("'", "\\'").replace('"', '\\"')
            safe_species = species.replace("'", "\\'").replace('"', '\\"')
            popup = (
                f"<b>{safe_name}</b><br><i>{safe_species}</i><br>"
                f'{obs_date}<br><a href=\\"{url}\\" target=\\"_blank\\">View on iNaturalist</a>'
            )
            markers_js_parts.append(f'[{lat},{lon},"{popup}"]')

    markers_js = ",".join(markers_js_parts)

    map_div = f"""
    <h2>Butterfly Sightings Map &mdash; {label.title()}</h2>
    <p>Research-grade butterfly observations in NW Oregon / SW Washington
    during {label}, all years combined. {len(observations)} observations shown.</p>
    <div id="sightings-map"></div>
    """

    map_script = (
        "<script>\n"
        "(function() {\n"
        '  var map = L.map("sightings-map").setView([45.5, -122.8], 8);\n'
        '  L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png", {\n'
        "    maxZoom: 16,\n"
        '    attribution: \'&copy; <a href="https://www.openstreetmap.org/copyright">'
        'OpenStreetMap</a> contributors"\n'
        "  }).addTo(map);\n"
        f"  var obs = [{markers_js}];\n"
        "  var markers = L.markerClusterGroup ? L.markerClusterGroup() : L.layerGroup();\n"
        "  for (var i = 0; i < obs.length; i++) {\n"
        "    var m = L.circleMarker([obs[i][0], obs[i][1]], {\n"
        "      radius: 5, fillColor: '#8faa7b', color: '#5a7a4a',\n"
        "      weight: 1, opacity: 0.8, fillOpacity: 0.6\n"
        "    });\n"
        "    m.bindPopup(obs[i][2]);\n"
        "    markers.addLayer(m);\n"
        "  }\n"
        "  markers.addTo(map);\n"
        "  if (obs.length > 0) {\n"
        "    var bounds = L.latLngBounds(obs.map(function(o) { return [o[0], o[1]]; }));\n"
        "    map.fitBounds(bounds, {padding: [30, 30]});\n"
        "  }\n"
        "})();\n"
        "</script>"
    )

    return (map_div, map_script)


def build_butterfly_sightings_html(inat_data: dict[str, Any]) -> str:
    """Build HTML table for butterfly species sightings from iNaturalist."""
    data = inat_data.get("data", {})
    species_list: list[dict[str, Any]] = data.get("species", [])
    month = data.get("month", 0)
    weeks: list[int] = data.get("weeks", [])

    if not species_list:
        return "<p>No butterfly sightings data available.</p>"

    if weeks:
        period_label = _week_label(weeks).title()
    elif 1 <= month <= 12:
        period_label = MONTH_NAMES[month]
    else:
        period_label = "This Month"
    month_name = MONTH_NAMES[month] if 1 <= month <= 12 else "this month"

    # Show top 15 species
    top_species = sorted(species_list, key=lambda s: s["observation_count"], reverse=True)[:15]
    max_count = top_species[0]["observation_count"] if top_species else 1

    rows = []
    for _rank, sp in enumerate(top_species, 1):
        name = sp.get("common_name") or sp["scientific_name"]
        scientific = sp["scientific_name"]
        count = sp["observation_count"]
        photo_url = sp.get("photo_url")
        taxon_id = sp.get("taxon_id", 0)
        taxon_url = sp.get("taxon_url", "")

        # Observation bar (scaled to max)
        bar_width = int((count / max_count) * 200) if max_count > 0 else 0

        # Photo thumbnail linked to taxon page
        if photo_url:
            photo_html = (
                f'<a href="{taxon_url}">'
                f'<img class="species-photo" src="{photo_url}" alt="{name}">'
                f"</a>"
                if taxon_url
                else f'<img class="species-photo" src="{photo_url}" alt="{name}">'
            )
        else:
            photo_html = '<div class="species-photo-placeholder">&#x1f98b;</div>'

        # Species name linked to taxon page
        name_html = f'<a href="{taxon_url}">{name}</a>' if taxon_url else name

        # Observation count linked to search results
        obs_url = _inat_obs_url(taxon_id, month) if taxon_id and month else ""
        count_html = f'<a href="{obs_url}">{count}</a>' if obs_url else str(count)

        rows.append(
            f"<tr>"
            f"<td>{photo_html}</td>"
            f"<td>{name_html}<br>"
            f'<span class="species-scientific">{scientific}</span></td>'
            f'<td class="obs-count">'
            f'<div class="obs-bar" style="width: {bar_width}px;"></div>'
            f"{count_html}</td>"
            f"</tr>"
        )

    # Link to browse all butterfly observations in the region for this month
    all_obs_url = (
        f"https://www.inaturalist.org/observations"
        f"?taxon_id=47224&month={month}"
        f"&quality_grade=research&verifiable=true"
        f"&swlat=44.5&swlng=-124.2&nelat=46.5&nelng=-121.5"
    )

    return f"""
    <h2>Butterfly Sightings &mdash; {period_label}</h2>
    <p>Research-grade butterfly observations in NW Oregon / SW Washington
    during {period_label} ({month_name}), all years combined
    (<a href="{all_obs_url}">browse on iNaturalist</a>).</p>
    <table>
        <thead>
        <tr>
            <th></th>
            <th>Species</th>
            <th>Observations</th>
        </tr>
        </thead>
        <tbody>
        {"".join(rows)}
        </tbody>
    </table>
    <p class="meta">Observation counts are cumulative across all years for {month_name}.
    Species ranked by research-grade observation frequency.</p>
    """


@task(name="build-html")
def build_html(
    weather_data: dict[str, Any],
    sunshine_data: dict[str, Any] | None,
    inat_data: dict[str, Any] | None = None,
) -> str:
    """Build HTML page from weather, sunshine, and iNaturalist data."""
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

    # Build butterfly sightings section
    butterfly_sightings_html = ""
    butterfly_map_html = ""
    map_script_html = ""
    if inat_data:
        butterfly_sightings_html = build_butterfly_sightings_html(inat_data)
        butterfly_map_html, map_script_html = build_butterfly_map_html(inat_data)

    return HTML_TEMPLATE.format(
        updated=updated,
        sunshine_today=sunshine_today_html,
        sunshine_16day=sunshine_16day_html,
        butterfly_sightings=butterfly_sightings_html,
        butterfly_map=butterfly_map_html,
        map_script=map_script_html,
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
