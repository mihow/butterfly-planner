"""
iNaturalist butterfly occurrence module.

Fetches and processes butterfly observation data from the iNaturalist API.
Designed for querying "what butterflies are seen in this area during a given
week/month" across ALL years — useful for planning butterfly-viewing trips.

Three main features:
1. Species counts for a given month/week across all years
2. Recent individual observations in the target area
3. Weekly activity histogram across the full year

Geographic focus: NW Oregon / SW Washington (Portland metro + coast + valley).

API Documentation: https://api.inaturalist.org/v1/docs/
Rate limits: ~1 req/sec, 10k/day
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime, timedelta
from typing import Any

from butterfly_planner.services import inat

# ---------------------------------------------------------------------------
# Default geographic area: NW Oregon / SW Washington
# Covers Portland metro, northern Willamette Valley, Oregon coast (north),
# Clark County WA, and SW Washington lowlands.
# ---------------------------------------------------------------------------
NW_OREGON_SW_WASHINGTON = {
    "swlat": 44.5,
    "swlng": -124.2,
    "nelat": 46.5,
    "nelng": -121.5,
}


# =============================================================================
# Data Models
# =============================================================================


@dataclass
class SpeciesRecord:
    """A butterfly species with its observation count for a query."""

    taxon_id: int
    scientific_name: str
    common_name: str | None
    rank: str
    observation_count: int
    photo_url: str | None = None
    taxon_url: str = ""

    @property
    def display_name(self) -> str:
        """Human-friendly name: common name if available, else scientific."""
        if self.common_name:
            return f"{self.common_name} ({self.scientific_name})"
        return self.scientific_name


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


@dataclass
class WeeklyActivity:
    """Observation counts per week of year (1-53)."""

    week: int
    count: int


@dataclass
class OccurrenceSummary:
    """Top-level result combining species counts and observations."""

    month: int
    year: int | None  # None = all years
    bbox: dict[str, float]
    species: list[SpeciesRecord]
    observations: list[ButterflyObservation]
    total_species: int
    total_observations: int
    weeks: list[int] = field(default_factory=list)
    fetched_at: datetime = field(default_factory=datetime.now)

    @property
    def top_species(self) -> list[SpeciesRecord]:
        """Top 20 species by observation count."""
        return sorted(self.species, key=lambda s: s.observation_count, reverse=True)[:20]


# =============================================================================
# Parsing helpers
# =============================================================================


def _parse_species_record(result: dict[str, Any]) -> SpeciesRecord:
    """Parse a single species_counts result into a SpeciesRecord."""
    taxon = result.get("taxon", {})
    photos = taxon.get("default_photo", {})
    return SpeciesRecord(
        taxon_id=taxon.get("id", 0),
        scientific_name=taxon.get("name", "Unknown"),
        common_name=taxon.get("preferred_common_name"),
        rank=taxon.get("rank", "species"),
        observation_count=result.get("count", 0),
        photo_url=photos.get("medium_url") if photos else None,
        taxon_url=f"https://www.inaturalist.org/taxa/{taxon.get('id', '')}",
    )


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
# API Fetching Functions
# =============================================================================


def fetch_species_counts(
    month: int | list[int],
    bbox: dict[str, float] | None = None,
    *,
    quality_grade: str = "research",
    per_page: int = 100,
) -> list[SpeciesRecord]:
    """
    Fetch butterfly species and observation counts for a given month.

    Queries across ALL years — returns species historically observed during
    the specified month(s) within the bounding box.

    Args:
        month: Month number (1-12) or list of months.
        bbox: Bounding box dict with swlat/swlng/nelat/nelng.
              Defaults to NW Oregon / SW Washington.
        quality_grade: Filter by quality (research, needs_id, casual).
        per_page: Max species to return (API max 500).

    Returns:
        List of SpeciesRecord sorted by observation count (descending).
    """
    bbox = bbox or NW_OREGON_SW_WASHINGTON

    month_str = ",".join(str(m) for m in month) if isinstance(month, list) else str(month)

    params: dict[str, Any] = {
        "taxon_id": inat.BUTTERFLIES,
        **bbox,
        "month": month_str,
        "quality_grade": quality_grade,
        "verifiable": "true",
        "per_page": per_page,
    }

    data = inat.get_species_counts(params)
    results: list[dict[str, Any]] = data.get("results", [])
    return [_parse_species_record(r) for r in results]


def fetch_observations_for_month(
    month: int | list[int],
    bbox: dict[str, float] | None = None,
    *,
    quality_grade: str = "research",
    max_pages: int = 3,
) -> list[ButterflyObservation]:
    """
    Fetch individual butterfly observations for a given month across all years.

    Args:
        month: Month number (1-12) or list of months.
        bbox: Bounding box. Defaults to NW Oregon / SW Washington.
        quality_grade: Filter by quality grade.
        max_pages: Maximum API pages to fetch (200 results each).

    Returns:
        List of ButterflyObservation objects.
    """
    bbox = bbox or NW_OREGON_SW_WASHINGTON

    month_str = ",".join(str(m) for m in month) if isinstance(month, list) else str(month)

    params: dict[str, Any] = {
        "taxon_id": inat.BUTTERFLIES,
        **bbox,
        "month": month_str,
        "quality_grade": quality_grade,
        "verifiable": "true",
        "order": "desc",
        "order_by": "observed_on",
    }

    raw = inat.get_observations_paginated(params, max_pages=max_pages)
    observations: list[ButterflyObservation] = []
    for obs in raw:
        parsed = _parse_observation(obs)
        if parsed is not None:
            observations.append(parsed)
    return observations


def fetch_weekly_histogram(
    bbox: dict[str, float] | None = None,
) -> list[WeeklyActivity]:
    """
    Fetch butterfly observation counts bucketed by week of year.

    Covers all years. Useful for identifying peak butterfly activity periods.

    Args:
        bbox: Bounding box. Defaults to NW Oregon / SW Washington.

    Returns:
        List of WeeklyActivity (week 1-53) sorted by week number.
    """
    bbox = bbox or NW_OREGON_SW_WASHINGTON

    params: dict[str, Any] = {
        "taxon_id": inat.BUTTERFLIES,
        **bbox,
        "quality_grade": "research",
        "verifiable": "true",
        "date_field": "observed",
        "interval": "week_of_year",
    }

    data = inat.get_histogram(params)
    results: dict[str, int] = data.get("results", {}).get("week_of_year", {})

    weeks = []
    for week_str, count in results.items():
        weeks.append(WeeklyActivity(week=int(week_str), count=count))
    return sorted(weeks, key=lambda w: w.week)


# =============================================================================
# High-level convenience functions
# =============================================================================


def get_current_week_species(
    bbox: dict[str, float] | None = None,
) -> OccurrenceSummary:
    """
    Fetch butterfly occurrence data for the current week ± 1 week.

    Uses the current ISO week number and queries for the three-week window
    (current week - 1 through current week + 1), converting to months for
    the iNaturalist API. This answers: "What butterflies have historically
    been seen in this area around this time of year?"

    Args:
        bbox: Bounding box. Defaults to NW Oregon / SW Washington.

    Returns:
        OccurrenceSummary with species and observations.
    """
    today = date.today()
    current_week = today.isocalendar()[1]
    weeks = _week_range(current_week)
    months = _weeks_to_months(weeks)

    species = fetch_species_counts(months, bbox)
    observations = fetch_observations_for_month(months, bbox, max_pages=3)

    return OccurrenceSummary(
        month=months[0],
        year=None,
        bbox=bbox or NW_OREGON_SW_WASHINGTON,
        species=species,
        observations=observations,
        total_species=len(species),
        total_observations=len(observations),
        weeks=weeks,
    )


def get_species_for_week(
    week: int,
    bbox: dict[str, float] | None = None,
) -> OccurrenceSummary:
    """
    Fetch butterfly species for a specific ISO week of the year.

    Determines which month(s) the week falls in and queries iNaturalist.
    If the week spans two months, both are queried.

    Args:
        week: ISO week number (1-53).
        bbox: Bounding box. Defaults to NW Oregon / SW Washington.

    Returns:
        OccurrenceSummary with species and observations.
    """
    months = _week_to_months(week)
    species = fetch_species_counts(months, bbox)
    observations = fetch_observations_for_month(months, bbox, max_pages=2)

    return OccurrenceSummary(
        month=months[0],
        year=None,
        bbox=bbox or NW_OREGON_SW_WASHINGTON,
        species=species,
        observations=observations,
        total_species=len(species),
        total_observations=len(observations),
    )


# =============================================================================
# Analysis / Summary
# =============================================================================


def summarize_species(species: list[SpeciesRecord]) -> dict[str, Any]:
    """
    Create a summary of species data for reporting.

    Returns dict with top_species, total count, and family breakdown.
    """
    if not species:
        return {"total_species": 0, "top_species": [], "by_rank": {}}

    by_rank: dict[str, int] = {}
    for s in species:
        by_rank[s.rank] = by_rank.get(s.rank, 0) + 1

    top = sorted(species, key=lambda s: s.observation_count, reverse=True)[:10]

    return {
        "total_species": len(species),
        "total_observations": sum(s.observation_count for s in species),
        "top_species": [
            {
                "name": s.display_name,
                "count": s.observation_count,
                "taxon_id": s.taxon_id,
            }
            for s in top
        ],
        "by_rank": by_rank,
    }


def peak_weeks(histogram: list[WeeklyActivity], top_n: int = 5) -> list[WeeklyActivity]:
    """Return the top N weeks by observation count."""
    return sorted(histogram, key=lambda w: w.count, reverse=True)[:top_n]


# =============================================================================
# Internal helpers
# =============================================================================


def _week_range(center_week: int, *, radius: int = 1) -> list[int]:
    """
    Return a list of ISO week numbers centered on *center_week*.

    Wraps around year boundaries (week 1 ± 1 → [52, 1, 2]).

    Args:
        center_week: The center ISO week number (1-53).
        radius: Number of weeks on each side (default 1 → 3-week window).

    Returns:
        Sorted list of ISO week numbers.
    """
    weeks: list[int] = []
    for offset in range(-radius, radius + 1):
        w = center_week + offset
        if w < 1:
            w += 52
        elif w > 52:
            w -= 52
        weeks.append(w)
    return sorted(weeks)


def _weeks_to_months(weeks: list[int], year: int | None = None) -> list[int]:
    """
    Determine the unique month(s) that a list of ISO weeks span.

    Args:
        weeks: List of ISO week numbers (1-53).
        year: Reference year. Defaults to current year.

    Returns:
        Sorted list of unique month numbers (1-12).
    """
    months: set[int] = set()
    for w in weeks:
        months.update(_week_to_months(w, year))
    return sorted(months)


def _week_to_months(week: int, year: int | None = None) -> list[int]:
    """
    Determine which month(s) an ISO week falls in.

    Uses Jan 1 of the given (or current) year as reference. If the week
    spans two months, returns both.

    Args:
        week: ISO week number (1-53).
        year: Reference year. Defaults to current year.

    Returns:
        Sorted list of month numbers (1-12).
    """
    ref_year = year or date.today().year

    # Jan 4 is always in ISO week 1
    jan4 = date(ref_year, 1, 4)
    iso_year_start = jan4 - timedelta(days=jan4.weekday())

    monday = iso_year_start + timedelta(weeks=week - 1)
    sunday = monday + timedelta(days=6)

    return sorted({monday.month, sunday.month})
