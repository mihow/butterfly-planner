"""
Prefect flow for building static site from raw data.

Transforms raw data into HTML pages for GitHub Pages.

Run locally:
    python -m butterfly_planner.flows.build
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo

import jinja2
from prefect import flow, task

from butterfly_planner import gdd

# Directories
DATA_DIR = Path("data")
RAW_DIR = DATA_DIR / "raw"
SITE_DIR = Path("site")

# Jinja2 environment — loads .html.j2 templates from the templates/ directory
_TEMPLATE_DIR = Path(__file__).resolve().parent.parent / "templates"
_jinja_env = jinja2.Environment(
    loader=jinja2.FileSystemLoader(str(_TEMPLATE_DIR)),
    autoescape=False,  # We produce trusted HTML fragments
)


def _render(template_name: str, **kwargs: Any) -> str:
    """Render a Jinja2 template by name."""
    return _jinja_env.get_template(template_name).render(**kwargs)


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
# Utility functions
# =============================================================================


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


# =============================================================================
# Sunshine renderers
# =============================================================================


def build_sunshine_today_html(sunshine_data: dict[str, Any]) -> str:
    """Build HTML for today's sunshine as a horizontal timeline bar."""
    minutely = sunshine_data["today_15min"].get("minutely_15", {})
    times = minutely.get("time", [])
    durations = minutely.get("sunshine_duration", [])
    is_day = minutely.get("is_day", [])

    if not times:
        return "<p>No 15-minute sunshine data available.</p>"

    today_str = times[0][:10]

    daylight_slots = [
        (times[i], durations[i])
        for i in range(len(times))
        if is_day[i] and times[i][:10] == today_str
    ]

    if not daylight_slots:
        return "<p>No daylight hours in forecast.</p>"

    n_slots = len(daylight_slots)
    total_sunshine_sec = sum(dur for _, dur in daylight_slots)
    total_sunshine_hours = total_sunshine_sec / 3600

    segments = []
    for time_str, duration in daylight_slots:
        dt = datetime.fromisoformat(time_str)
        pct = (duration / 900) * 100
        segments.append(
            {
                "color_class": _sunshine_color_class(pct),
                "title": f"{dt.strftime('%I:%M %p')}: {duration / 60:.0f} min sun",
            }
        )

    labels = []
    seen_hours: set[int] = set()
    for idx, (time_str, _) in enumerate(daylight_slots):
        dt = datetime.fromisoformat(time_str)
        if dt.hour not in seen_hours:
            seen_hours.add(dt.hour)
            labels.append(
                {
                    "left_pct": f"{(idx / n_slots) * 100:.1f}",
                    "text": dt.strftime("%-I%p").lower(),
                }
            )

    sunrise_dt = datetime.fromisoformat(daylight_slots[0][0])
    sunset_dt = datetime.fromisoformat(daylight_slots[-1][0])

    return _render(
        "sunshine_today.html.j2",
        today_date=sunrise_dt.strftime("%B %d"),
        total_sunshine_hours=f"{total_sunshine_hours:.1f} hours",
        sunrise=sunrise_dt.strftime("%-I:%M %p"),
        sunset=sunset_dt.strftime("%-I:%M %p"),
        labels=labels,
        segments=segments,
    )


def _group_15min_by_date(
    sunshine_data: dict[str, Any],
) -> dict[str, list[tuple[str, int, bool]]]:
    """Group 15-minute sunshine slots by date."""
    minutely = sunshine_data.get("today_15min", {}).get("minutely_15", {})
    times = minutely.get("time", [])
    durations = minutely.get("sunshine_duration", [])
    is_day = minutely.get("is_day", [])

    by_date: dict[str, list[tuple[str, int, bool]]] = {}
    for i, time_str in enumerate(times):
        date_str = time_str[:10]
        by_date.setdefault(date_str, []).append((time_str, durations[i], bool(is_day[i])))
    return by_date


def _build_hourly_bar(slots: list[tuple[str, int, bool]]) -> str:
    """Build an inline hourly sunshine bar from 15-min slot data."""
    daylight = [(t, d) for t, d, is_day in slots if is_day]
    if not daylight:
        return ""

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

    slots_by_date = _group_15min_by_date(sunshine_data)

    rows = []
    for i, date_str in enumerate(dates):
        sun_sec = sunshine_secs[i] if sunshine_secs[i] is not None else 0
        day_sec = daylight_secs[i] if daylight_secs[i] is not None else 0
        sunshine_hours = sun_sec / 3600
        daylight_hours = day_sec / 3600
        sunshine_pct = (sun_sec / day_sec * 100) if day_sec > 0 else 0

        is_good = sunshine_hours > 3.0 or sunshine_pct > 40.0

        day_slots = slots_by_date.get(date_str)
        if day_slots:
            bar = _build_hourly_bar(day_slots)
        else:
            bar_width = int(sunshine_pct * 3)
            bar = f'<div class="sunshine-bar" style="width: {bar_width}px;"></div>'

        w = weather_by_date.get(date_str)
        if w and w["high_c"] is not None:
            temp_cell = (
                f'<span class="temp-high">{w["high_c"]:.0f}\u00b0C</span> / '
                f'<span class="temp-low">{w["low_c"]:.0f}\u00b0C</span>'
            )
            precip_mm = w["precip_mm"] if w["precip_mm"] is not None else 0
            precip_cell = f"{precip_mm:.1f}mm"
        else:
            temp_cell = "\u2014"
            precip_cell = "\u2014"

        if w and w["weather_code"] is not None:
            conditions = wmo_code_to_conditions(w["weather_code"])
        else:
            conditions = "\u2014"

        rows.append(
            {
                "row_class": "good-day" if is_good else "",
                "date": date_str,
                "sunshine_hours": f"{sunshine_hours:.1f}",
                "daylight_hours": f"{daylight_hours:.1f}",
                "sunshine_pct": f"{sunshine_pct:.0f}",
                "bar": bar,
                "temp_cell": temp_cell,
                "precip_cell": precip_cell,
                "conditions": conditions,
            }
        )

    return _render("sunshine_16day.html.j2", rows=rows)


# =============================================================================
# Species palette
# =============================================================================

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

_SPECIES_COLORS = [
    "#e6194b",  # red
    "#3cb44b",  # green
    "#4363d8",  # blue
    "#f58231",  # orange
    "#911eb4",  # purple
    "#42d4f4",  # cyan
    "#f032e6",  # magenta
    "#bfef45",  # lime
    "#fabed4",  # pink
    "#469990",  # teal
    "#dcbeff",  # lavender
    "#9a6324",  # brown
    "#ffe119",  # yellow
    "#aaffc3",  # mint
    "#808000",  # olive
]


@dataclass
class SpeciesStyle:
    """Visual style for a species on the map and table."""

    color: str
    initials: str
    common_name: str
    scientific_name: str


def _build_species_palette(species_list: list[dict[str, Any]]) -> dict[str, SpeciesStyle]:
    """Assign a color and 2-letter abbreviation to each species."""
    palette: dict[str, SpeciesStyle] = {}
    ranked = sorted(species_list, key=lambda s: s.get("observation_count", 0), reverse=True)
    for i, sp in enumerate(ranked):
        scientific = sp.get("scientific_name", "Unknown")
        common = sp.get("common_name") or scientific
        color = _SPECIES_COLORS[i % len(_SPECIES_COLORS)]
        initials = _species_initials(common)
        palette[scientific] = SpeciesStyle(
            color=color,
            initials=initials,
            common_name=common,
            scientific_name=scientific,
        )
    return palette


def _species_initials(name: str) -> str:
    """Derive a 2-letter abbreviation from a common name."""
    words = name.split()
    if len(words) >= 2:
        return (words[0][0] + words[-1][0]).upper()
    if len(name) >= 2:
        return name[:2].upper()
    return name.upper()


def _year_range(observations: list[dict[str, Any]]) -> str:
    """Derive year range string from observation dates, e.g. '2014-2026'."""
    years: set[int] = set()
    for obs in observations:
        observed_on = obs.get("observed_on", "")
        if observed_on and len(observed_on) >= 4 and observed_on[:4].isdigit():
            years.add(int(observed_on[:4]))
    if not years:
        return "all years"
    min_year, max_year = min(years), max(years)
    if min_year == max_year:
        return str(min_year)
    return f"{min_year}\u2013{max_year}"


def _week_label(weeks: list[int]) -> str:
    """Human-readable label for a list of ISO weeks."""
    if not weeks:
        return "this week"
    if len(weeks) == 1:
        return f"week {weeks[0]}"
    return f"weeks {weeks[0]}\u2013{weeks[-1]}"


def _inat_obs_url(taxon_id: int, month: int) -> str:
    """Build an iNaturalist observation search URL for a taxon in the target region."""
    return (
        f"https://www.inaturalist.org/observations"
        f"?taxon_id={taxon_id}&month={month}"
        f"&quality_grade=research&verifiable=true"
        f"&swlat=44.5&swlng=-124.2&nelat=46.5&nelng=-121.5"
    )


# =============================================================================
# Butterfly sightings renderers
# =============================================================================


def _escape_js(text: str) -> str:
    """Escape a string for safe embedding inside a JS double-quoted string."""
    return text.replace("\\", "\\\\").replace('"', '\\"').replace("'", "\\'")


def _build_weather_html(w: dict[str, Any]) -> str:
    """Build a compact weather summary string for a popup."""
    parts: list[str] = []
    if w.get("weather_code") is not None:
        parts.append(wmo_code_to_conditions(w["weather_code"]))
    if w.get("high_c") is not None and w.get("low_c") is not None:
        parts.append(f"{w['high_c']:.0f}/{w['low_c']:.0f}\u00b0C")
    if w.get("precip_mm") is not None and w["precip_mm"] > 0:
        parts.append(f"{w['precip_mm']:.1f}mm")
    return " &middot; ".join(parts)


def build_butterfly_map_html(
    inat_data: dict[str, Any],
    palette: dict[str, SpeciesStyle] | None = None,
    historical_weather: dict[str, dict[str, Any]] | None = None,
) -> tuple[str, str]:
    """Build an interactive Leaflet map of butterfly observations.

    Each marker carries structured data so the JS template can build rich
    popups with thumbnail images and weather info.

    Returns a (map_div_html, map_script_js) tuple.
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

    if palette is None:
        species_list: list[dict[str, Any]] = data.get("species", [])
        palette = _build_species_palette(species_list)

    hw = historical_weather or {}

    # Build JS array of marker objects for the template.
    # Using objects (not positional arrays) so future fields are easy to add.
    markers_js_parts: list[str] = []
    for obs in observations:
        lat = obs.get("latitude")
        lon = obs.get("longitude")
        if lat is None or lon is None:
            continue

        name = obs.get("common_name") or obs.get("species", "Unknown")
        species = obs.get("species", "")
        obs_date = obs.get("observed_on", "")
        url = obs.get("url", "")
        photo_url = obs.get("photo_url") or ""

        style = palette.get(species)
        color = style.color if style else "#888"
        initials = style.initials if style else "?"

        # Weather string for this observation's date
        w = hw.get(obs_date)
        weather_html = _escape_js(_build_weather_html(w)) if w else ""

        marker = (
            "{"
            f"lat:{lat},lon:{lon},"
            f'name:"{_escape_js(name)}",'
            f'species:"{_escape_js(species)}",'
            f'date:"{_escape_js(obs_date)}",'
            f'url:"{_escape_js(url)}",'
            f'photo:"{_escape_js(photo_url)}",'
            f'color:"{color}",'
            f'initials:"{_escape_js(initials)}",'
            f'weather:"{weather_html}"'
            "}"
        )
        markers_js_parts.append(marker)

    markers_js = "[" + ",".join(markers_js_parts) + "]"
    years = _year_range(observations)

    map_div = _render(
        "sightings_map.html.j2",
        label=label.title(),
        years=years,
        obs_count=len(observations),
    )

    map_script = _render(
        "sightings_map_script.html.j2",
        markers_json=markers_js,
    )

    return (map_div, map_script)


def build_butterfly_sightings_html(
    inat_data: dict[str, Any],
    palette: dict[str, SpeciesStyle] | None = None,
) -> str:
    """Build HTML table for butterfly species sightings from iNaturalist."""
    data = inat_data.get("data", {})
    species_list: list[dict[str, Any]] = data.get("species", [])
    observations_list: list[dict[str, Any]] = data.get("observations", [])
    month = data.get("month", 0)
    weeks: list[int] = data.get("weeks", [])

    if not species_list:
        return "<p>No butterfly sightings data available.</p>"

    if palette is None:
        palette = _build_species_palette(species_list)

    years = _year_range(observations_list)
    if weeks:
        period_label = f"{_week_label(weeks).title()} ({years})"
    elif 1 <= month <= 12:
        period_label = MONTH_NAMES[month]
    else:
        period_label = "This Month"
    month_name = MONTH_NAMES[month] if 1 <= month <= 12 else "this month"

    top_species = sorted(species_list, key=lambda s: s["observation_count"], reverse=True)[:15]
    max_count = top_species[0]["observation_count"] if top_species else 1

    species_rows = []
    for sp in top_species:
        name = sp.get("common_name") or sp["scientific_name"]
        scientific = sp["scientific_name"]
        count = sp["observation_count"]
        photo_url = sp.get("photo_url")
        taxon_id = sp.get("taxon_id", 0)
        taxon_url = sp.get("taxon_url", "")

        style = palette.get(scientific)
        color = style.color if style else "#888"
        initials = style.initials if style else "?"

        bar_width = int((count / max_count) * 200) if max_count > 0 else 0

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

        name_link = f'<a href="{taxon_url}">{name}</a>' if taxon_url else name

        obs_url = _inat_obs_url(taxon_id, month) if taxon_id and month else ""
        count_html = f'<a href="{obs_url}">{count}</a>' if obs_url else str(count)

        species_rows.append(
            {
                "photo_html": photo_html,
                "color": color,
                "initials": initials,
                "name_html": name_link,
                "scientific_name": scientific,
                "bar_width": bar_width,
                "count_html": count_html,
            }
        )

    all_obs_url = (
        f"https://www.inaturalist.org/observations"
        f"?taxon_id=47224&month={month}"
        f"&quality_grade=research&verifiable=true"
        f"&swlat=44.5&swlng=-124.2&nelat=46.5&nelng=-121.5"
    )

    return _render(
        "sightings_table.html.j2",
        period_label=period_label,
        month_name=month_name,
        all_obs_url=all_obs_url,
        species=species_rows,
    )


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
        palette = _build_species_palette(species_list)
        butterfly_sightings_html = build_butterfly_sightings_html(inat_data, palette)

        hist_weather = load_historical_weather()
        butterfly_map_html, map_script_html = build_butterfly_map_html(
            inat_data, palette, hist_weather
        )

    gdd_today_html = ""
    gdd_timeline_html = ""
    if gdd_data:
        gdd_today_html = gdd.build_gdd_today_html(gdd_data, _render)
        gdd_timeline_html = gdd.build_gdd_timeline_html(gdd_data, _render)

    return _render(
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
