"""Weekly butterfly occurrence queries and calendar utilities.

High-level functions that combine species counts and observations
for a given ISO week, plus week-to-month conversion helpers.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime, timedelta
from typing import TYPE_CHECKING

from butterfly_planner.datasources.inaturalist import client
from butterfly_planner.datasources.inaturalist.observations import (
    fetch_observations_for_month,
)
from butterfly_planner.datasources.inaturalist.species import fetch_species_counts

if TYPE_CHECKING:
    from butterfly_planner.datasources.inaturalist.observations import ButterflyObservation
    from butterfly_planner.datasources.inaturalist.species import SpeciesRecord

# Re-export for convenience
NW_OREGON_SW_WASHINGTON = client.NW_OREGON_SW_WASHINGTON


# =============================================================================
# Data Model
# =============================================================================


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
# High-level convenience functions
# =============================================================================


def get_current_week_species(
    bbox: dict[str, float] | None = None,
) -> OccurrenceSummary:
    """
    Fetch butterfly occurrence data for the current week +/- 1 week.

    Uses the current ISO week number and queries for the three-week window,
    converting to months for the iNaturalist API.

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
        bbox=bbox or client.NW_OREGON_SW_WASHINGTON,
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
        bbox=bbox or client.NW_OREGON_SW_WASHINGTON,
        species=species,
        observations=observations,
        total_species=len(species),
        total_observations=len(observations),
    )


# =============================================================================
# Internal helpers
# =============================================================================


def _week_range(center_week: int, *, radius: int = 1) -> list[int]:
    """
    Return a list of ISO week numbers centered on *center_week*.

    Wraps around year boundaries (week 1 +/- 1 -> [52, 1, 2]).

    Args:
        center_week: The center ISO week number (1-53).
        radius: Number of weeks on each side (default 1 -> 3-week window).

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

    Uses Jan 4 of the given (or current) year as reference. If the week
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
