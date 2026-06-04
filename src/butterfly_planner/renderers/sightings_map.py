"""Leaflet map renderer for butterfly observations.

Generates an interactive map with markers carrying structured data
for rich popups with thumbnail images and weather info.
"""

from __future__ import annotations

import json
from typing import Any

from pydantic import BaseModel

from butterfly_planner.renderers import render_template
from butterfly_planner.renderers.date_utils import date_range_label, year_range
from butterfly_planner.renderers.species_palette import (
    SpeciesStyle,
    build_species_palette,
)
from butterfly_planner.renderers.weather_utils import wmo_code_to_conditions


class _MarkerData(BaseModel):
    """Structured marker data serialized as JSON into the map script."""

    lat: float
    lon: float
    name: str
    species: str
    date: str
    url: str
    photo: str
    color: str
    initials: str
    weather: str


def _safe_json(obj: Any) -> str:
    """Serialize *obj* to a JSON string safe for embedding in a <script> block.

    json.dumps escapes ``"`` and ``\\`` by default.  Three additional sequences
    are unsafe inside a ``<script>`` block even inside a string literal:

    * ``</`` — closes the enclosing ``<script>`` element when the browser
      HTML-parses the document before executing JS.
    * U+2028 (LINE SEPARATOR) and U+2029 (PARAGRAPH SEPARATOR) — treated as
      line terminators by JS engines; they break string literals when
      unescaped.  Python's json.dumps does NOT escape them by default.

    ``ensure_ascii=False`` is intentional: non-ASCII characters in names are
    preserved as UTF-8 rather than being mangled into ``\\uXXXX`` sequences,
    which keeps popup text readable.  The three dangerous sequences above are
    the only ones that need explicit post-processing.
    """
    serialized = json.dumps(obj, ensure_ascii=False)
    # Escape </script> injection: replace </ with <\/
    # (the backslash is legal in a JSON string and ignored by JS)
    serialized = serialized.replace("</", "<\\/")
    # Escape U+2028 / U+2029 — illegal unescaped in JS string literals
    serialized = serialized.replace(chr(0x2028), "\\u2028")
    serialized = serialized.replace(chr(0x2029), "\\u2029")
    return serialized


def _build_weather_html(w: dict[str, Any]) -> str:
    """Build a compact weather summary string for a popup."""
    parts: list[str] = []
    if w.get("weather_code") is not None:
        parts.append(wmo_code_to_conditions(w["weather_code"]))
    if w.get("high_c") is not None and w.get("low_c") is not None:
        parts.append(f"{w['high_c']:.0f}/{w['low_c']:.0f}°C")
    if w.get("precip_mm") is not None and w["precip_mm"] > 0:
        parts.append(f"{w['precip_mm']:.1f}mm")
    return " &middot; ".join(parts)


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

    label = date_range_label(data.get("date_start", ""), data.get("date_end", ""))

    if not observations:
        return (
            f"<h2>Butterfly Sightings Map &mdash; {label.title()}</h2>"
            "<p>No observation data available for the map.</p>",
            "",
        )

    if palette is None:
        species_list: list[dict[str, Any]] = data.get("species", [])
        palette = build_species_palette(species_list)

    # Build list of typed marker objects; serialize once with _safe_json.
    markers: list[_MarkerData] = []
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
        weather_html = _build_weather_html(w) if w else ""

        markers.append(
            _MarkerData(
                lat=lat,
                lon=lon,
                name=name,
                species=species,
                date=obs_date,
                url=url,
                photo=photo_url,
                color=color,
                initials=initials,
                weather=weather_html,
            )
        )

    markers_json = _safe_json([m.model_dump() for m in markers])
    years = year_range(observations)

    map_div = render_template(
        "sightings_map.html.j2",
        label=label.title(),
        years=years,
        obs_count=len(observations),
    )

    map_script = render_template(
        "sightings_map_script.html.j2",
        markers_json=markers_json,
    )

    return (map_div, map_script)
