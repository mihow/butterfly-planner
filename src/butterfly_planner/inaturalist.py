"""Backward-compatibility re-exports from datasources.inaturalist.

All code has moved to butterfly_planner.datasources.inaturalist/.
This module re-exports the public API so existing imports keep working
until all callers are updated.
"""

from butterfly_planner.datasources.inaturalist.client import (  # noqa: F401
    NW_OREGON_SW_WASHINGTON,
)
from butterfly_planner.datasources.inaturalist.observations import (  # noqa: F401
    ButterflyObservation,
    _parse_observation,
    fetch_observations_for_month,
)
from butterfly_planner.datasources.inaturalist.species import (  # noqa: F401
    SpeciesRecord,
    WeeklyActivity,
    _parse_species_record,
    fetch_species_counts,
    fetch_weekly_histogram,
    peak_weeks,
    summarize_species,
)
from butterfly_planner.datasources.inaturalist.weekly import (  # noqa: F401
    OccurrenceSummary,
    _week_range,
    _week_to_months,
    _weeks_to_months,
    get_current_week_species,
    get_species_for_week,
)
