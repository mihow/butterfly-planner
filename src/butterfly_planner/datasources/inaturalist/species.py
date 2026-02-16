"""Butterfly species data: counts, records, and weekly histograms."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from butterfly_planner.datasources.inaturalist import client

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
class WeeklyActivity:
    """Observation counts per week of year (1-53)."""

    week: int
    count: int


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
    bbox = bbox or client.NW_OREGON_SW_WASHINGTON

    month_str = ",".join(str(m) for m in month) if isinstance(month, list) else str(month)

    params: dict[str, Any] = {
        "taxon_id": client.BUTTERFLIES,
        **bbox,
        "month": month_str,
        "quality_grade": quality_grade,
        "verifiable": "true",
        "per_page": per_page,
    }

    data = client.get_species_counts(params)
    results: list[dict[str, Any]] = data.get("results", [])
    return [_parse_species_record(r) for r in results]


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
    bbox = bbox or client.NW_OREGON_SW_WASHINGTON

    params: dict[str, Any] = {
        "taxon_id": client.BUTTERFLIES,
        **bbox,
        "quality_grade": "research",
        "verifiable": "true",
        "date_field": "observed",
        "interval": "week_of_year",
    }

    data = client.get_histogram(params)
    results: dict[str, int] = data.get("results", {}).get("week_of_year", {})

    weeks = []
    for week_str, count in results.items():
        weeks.append(WeeklyActivity(week=int(week_str), count=count))
    return sorted(weeks, key=lambda w: w.week)


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
