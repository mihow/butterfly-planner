"""iNaturalist butterfly occurrence data source.

Fetches and processes butterfly observation data from the iNaturalist API.
Designed for querying "what butterflies are seen in this area during a given
week/month" across ALL years.

Public API:
  - client: Low-level HTTP (rate-limited, paginated)
  - species: SpeciesRecord, fetch_species_counts, WeeklyActivity, fetch_weekly_histogram
  - observations: ButterflyObservation, fetch_observations_for_month
  - weekly: OccurrenceSummary, get_current_week_species, get_species_for_week

Geographic focus: NW Oregon / SW Washington (Portland metro + coast + valley).
"""

from butterfly_planner.datasources.inaturalist.client import NW_OREGON_SW_WASHINGTON
from butterfly_planner.datasources.inaturalist.observations import (
    ButterflyObservation,
    fetch_observations_for_month,
)
from butterfly_planner.datasources.inaturalist.species import (
    SpeciesRecord,
    WeeklyActivity,
    fetch_species_counts,
    fetch_weekly_histogram,
    peak_weeks,
    summarize_species,
)
from butterfly_planner.datasources.inaturalist.weekly import (
    OccurrenceSummary,
    get_current_week_species,
    get_species_for_week,
)

__all__ = [
    "NW_OREGON_SW_WASHINGTON",
    "ButterflyObservation",
    "OccurrenceSummary",
    "SpeciesRecord",
    "WeeklyActivity",
    "fetch_observations_for_month",
    "fetch_species_counts",
    "fetch_weekly_histogram",
    "get_current_week_species",
    "get_species_for_week",
    "peak_weeks",
    "summarize_species",
]
