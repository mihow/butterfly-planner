"""Backward-compatibility re-exports from datasources.gdd.

All code has moved to butterfly_planner.datasources.gdd/.
This module re-exports the public API so existing imports keep working
until all callers are updated.
"""

from butterfly_planner.datasources.gdd import (  # noqa: F401
    ARCHIVE_API,
    DEFAULT_BASE_TEMP_F,
    DEFAULT_UPPER_CUTOFF_F,
    DailyGDD,
    DayOfYearStats,
    NormalGDD,
    SpeciesGDDProfile,
    YearGDD,
    compute_accumulated_gdd,
    compute_daily_gdd,
    compute_normals,
    correlate_observations_with_gdd,
    fetch_temperature_data,
    fetch_year_gdd,
    normals_to_dict,
    species_profiles_to_dict,
    year_gdd_to_dict,
)
