"""Species visual styling: colors, initials, and palette assignment.

Shared by both map and table renderers.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

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


def build_species_palette(species_list: list[dict[str, Any]]) -> dict[str, SpeciesStyle]:
    """Assign a color and 2-letter abbreviation to each species."""
    palette: dict[str, SpeciesStyle] = {}
    ranked = sorted(species_list, key=lambda s: s.get("observation_count", 0), reverse=True)
    for i, sp in enumerate(ranked):
        scientific = sp.get("scientific_name", "Unknown")
        common = sp.get("common_name") or scientific
        color = _SPECIES_COLORS[i % len(_SPECIES_COLORS)]
        initials = species_initials(common)
        palette[scientific] = SpeciesStyle(
            color=color,
            initials=initials,
            common_name=common,
            scientific_name=scientific,
        )
    return palette


def species_initials(name: str) -> str:
    """Derive a 2-letter abbreviation from a common name."""
    words = name.split()
    if len(words) >= 2:
        return (words[0][0] + words[-1][0]).upper()
    if len(name) >= 2:
        return name[:2].upper()
    return name.upper()
