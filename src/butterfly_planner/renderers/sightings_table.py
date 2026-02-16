"""Species sightings HTML table renderer.

Builds a ranked table of butterfly species with observation counts,
photos, and links to iNaturalist.
"""

from __future__ import annotations

from typing import Any

from butterfly_planner.renderers import render_template
from butterfly_planner.renderers.sightings_map import _week_label, _year_range
from butterfly_planner.renderers.species_palette import (
    MONTH_NAMES,
    SpeciesStyle,
    build_species_palette,
)


def _inat_obs_url(taxon_id: int, month: int) -> str:
    """Build an iNaturalist observation search URL for a taxon in the target region."""
    return (
        f"https://www.inaturalist.org/observations"
        f"?taxon_id={taxon_id}&month={month}"
        f"&quality_grade=research&verifiable=true"
        f"&swlat=44.5&swlng=-124.2&nelat=46.5&nelng=-121.5"
    )


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
        palette = build_species_palette(species_list)

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

    return render_template(
        "sightings_table.html.j2",
        period_label=period_label,
        month_name=month_name,
        all_obs_url=all_obs_url,
        species=species_rows,
    )
