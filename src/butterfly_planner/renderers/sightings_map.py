"""Leaflet map renderer for butterfly observations.

Generates an interactive map with markers carrying structured data
for rich popups with thumbnail images and weather info.
"""

from __future__ import annotations

from typing import Any

from butterfly_planner.renderers import render_template
from butterfly_planner.renderers.species_palette import (
    SpeciesStyle,
    build_species_palette,
)
from butterfly_planner.renderers.weather_utils import wmo_code_to_conditions


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


def build_butterfly_map_html(
    inat_data: dict[str, Any],
    palette: dict[str, SpeciesStyle] | None = None,
) -> tuple[str, str]:
    """Build an interactive Leaflet map of butterfly observations.

    Each marker carries structured data so the JS template can build rich
    popups with thumbnail images and weather info.

    Observations should be pre-enriched with a ``"weather"`` key (see
    ``analysis.species_weather.enrich_observations_with_weather``).

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
        palette = build_species_palette(species_list)

    # Build JS array of marker objects for the template.
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

        # Weather from pre-enriched observation
        w = obs.get("weather")
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

    map_div = render_template(
        "sightings_map.html.j2",
        label=label.title(),
        years=years,
        obs_count=len(observations),
    )

    map_script = render_template(
        "sightings_map_script.html.j2",
        markers_json=markers_js,
    )

    return (map_div, map_script)
