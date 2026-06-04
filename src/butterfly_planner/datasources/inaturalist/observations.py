"""Butterfly observation fetching and parsing."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, timedelta
from typing import Any

from butterfly_planner.datasources.inaturalist import client

# ---------------------------------------------------------------------------
# Recency window
# ---------------------------------------------------------------------------
# Number of years to look back when fetching sightings for the map.
# The iNat paginator pages newest-first so that max_pages x per_page gives
# the most recent observations, not the oldest.  10 years captures a
# meaningful seasonal baseline while keeping queries recent.
# Change RECENT_YEARS to adjust the floor (product decision: see PR notes).
RECENT_YEARS: int = 10

# =============================================================================
# Data Model
# =============================================================================


@dataclass
class ButterflyObservation:
    """A single butterfly sighting from iNaturalist."""

    id: int
    species: str
    common_name: str | None
    observed_on: date
    latitude: float
    longitude: float
    quality_grade: str
    url: str
    photo_url: str | None = None

    @property
    def display_name(self) -> str:
        if self.common_name:
            return f"{self.common_name} ({self.species})"
        return self.species


# =============================================================================
# Parsing
# =============================================================================


def _parse_observation(obs: dict[str, Any]) -> ButterflyObservation | None:
    """Parse a single observation result. Returns None if location missing."""
    location = obs.get("location")
    if not location:
        return None

    parts = str(location).split(",")
    if len(parts) != 2:
        return None

    try:
        lat = float(parts[0])
        lon = float(parts[1])
    except ValueError:
        return None

    taxon = obs.get("taxon") or {}
    photos = obs.get("photos") or []
    observed_on_str = obs.get("observed_on")
    if not observed_on_str:
        return None

    return ButterflyObservation(
        id=obs["id"],
        species=taxon.get("name", "Unknown"),
        common_name=taxon.get("preferred_common_name"),
        observed_on=date.fromisoformat(observed_on_str),
        latitude=lat,
        longitude=lon,
        quality_grade=obs.get("quality_grade", "casual"),
        url=f"https://www.inaturalist.org/observations/{obs['id']}",
        photo_url=photos[0]["url"] if photos else None,
    )


# =============================================================================
# API Fetching
# =============================================================================


def fetch_observations_for_month(
    month: int | list[int],
    bbox: dict[str, float] | None = None,
    *,
    quality_grade: str = "research",
    max_pages: int = 3,
) -> list[ButterflyObservation]:
    """
    Fetch individual butterfly observations for a given month (recent years only).

    Observations are bounded to the last ``RECENT_YEARS`` years and fetched
    newest-first so that ``max_pages`` pages surface the most recent sightings,
    not the oldest.

    Args:
        month: Month number (1-12) or list of months.
        bbox: Bounding box. Defaults to NW Oregon / SW Washington.
        quality_grade: Filter by quality grade.
        max_pages: Maximum API pages to fetch (200 results each).

    Returns:
        List of ButterflyObservation objects.
    """
    bbox = bbox or client.NW_OREGON_SW_WASHINGTON

    month_str = ",".join(str(m) for m in month) if isinstance(month, list) else str(month)

    # Date floor: only include observations from roughly the last RECENT_YEARS
    # years. This is an approximate floor (365-day years, ignores leap days),
    # which is fine since it only gates a coarse recency window. Using a
    # timedelta avoids the ValueError that date(year - N, 2, 29) raises when
    # the target year is not a leap year.
    today = date.today()
    d1 = (today - timedelta(days=365 * RECENT_YEARS)).isoformat()

    params: dict[str, Any] = {
        "taxon_id": client.BUTTERFLIES,
        **bbox,
        "month": month_str,
        "quality_grade": quality_grade,
        "verifiable": "true",
        "d1": d1,
    }

    raw = client.get_observations_paginated(params, max_pages=max_pages, newest_first=True)
    observations: list[ButterflyObservation] = []
    for obs in raw:
        parsed = _parse_observation(obs)
        if parsed is not None:
            observations.append(parsed)
    return observations
