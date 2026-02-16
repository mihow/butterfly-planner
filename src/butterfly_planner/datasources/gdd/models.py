"""GDD data models and constants."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from datetime import date

# Default GDD parameters for butterflies / general insects
DEFAULT_BASE_TEMP_F = 50.0
DEFAULT_UPPER_CUTOFF_F = 86.0


@dataclass
class DailyGDD:
    """GDD computation result for a single day."""

    date: date
    tmax_f: float
    tmin_f: float
    gdd: float
    accumulated: float


@dataclass
class YearGDD:
    """Full-year (or partial-year) GDD accumulation."""

    year: int
    daily: list[DailyGDD] = field(default_factory=list)

    @property
    def total(self) -> float:
        """Total accumulated GDD for the year so far."""
        return self.daily[-1].accumulated if self.daily else 0.0

    def accumulated_through_doy(self, day_of_year: int) -> float:
        """Return accumulated GDD through a given day-of-year (1-based).

        Args:
            day_of_year: Day of year, 1 = Jan 1.

        Returns:
            Accumulated GDD, or 0.0 if no data for that day.
        """
        for entry in self.daily:
            if entry.date.timetuple().tm_yday == day_of_year:
                return entry.accumulated
        return 0.0


@dataclass
class DayOfYearStats:
    """GDD statistics for a single day-of-year across multiple years."""

    doy: int
    mean_accumulated: float
    stddev: float


@dataclass
class NormalGDD:
    """Multi-year GDD normals: mean and standard deviation by day-of-year."""

    year_range: str
    by_doy: list[DayOfYearStats] = field(default_factory=list)


@dataclass
class SpeciesGDDProfile:
    """GDD range statistics for a butterfly species.

    Built by cross-referencing observation dates with accumulated GDD
    at the configured location.
    """

    scientific_name: str
    common_name: str
    observation_count: int
    gdd_min: float
    gdd_p10: float
    gdd_median: float
    gdd_p90: float
    gdd_max: float
