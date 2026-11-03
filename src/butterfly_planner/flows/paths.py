"""Per-location file paths shared by the fetch and build flows.

The fetch flow writes each location's cache files and the build flow reads
them back. Both take their paths from ``location_paths`` so the two sides
cannot drift apart, and so two locations never read or overwrite each
other's data.

Cache paths are relative to the ``DataStore`` base directory. ``daily_dir``
is relative to ``store.derived``, and ``site_file`` is relative to the
built site's root directory.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from butterfly_planner.reference.geography import Location


@dataclass(frozen=True)
class LocationPaths:
    """Where one location's cached inputs and built outputs live."""

    weather: Path
    sunshine_15min: Path
    sunshine_16day: Path
    inaturalist: Path
    historical_weather: Path
    gdd: Path
    daily_dir: Path
    site_file: Path


def location_paths(loc: Location) -> LocationPaths:
    """Return the cache and output paths for ``loc``, keyed by its slug."""
    live = Path("live") / loc.slug
    historical = Path("historical") / loc.slug
    return LocationPaths(
        weather=live / "weather.json",
        sunshine_15min=live / "sunshine_15min.json",
        sunshine_16day=live / "sunshine_16day.json",
        inaturalist=live / "inaturalist.json",
        historical_weather=historical / "weather" / "historical_weather.json",
        gdd=historical / "gdd" / "gdd.json",
        daily_dir=Path("daily") / loc.slug,
        site_file=Path(loc.site_subdir) / "index.html",
    )
