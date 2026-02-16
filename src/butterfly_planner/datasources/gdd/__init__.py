"""Growing Degree Days (GDD) computation and data source.

GDD measures accumulated heat units over a growing season — the standard
phenological metric for predicting insect development.

Public API:
  - models: DailyGDD, YearGDD, NormalGDD, DayOfYearStats, SpeciesGDDProfile
  - compute: compute_daily_gdd, compute_accumulated_gdd, compute_normals,
             correlate_observations_with_gdd
  - client: fetch_temperature_data, fetch_year_gdd
  - serialization: year_gdd_to_dict, normals_to_dict, species_profiles_to_dict
"""

from butterfly_planner.datasources.gdd.client import (
    ARCHIVE_API,
    fetch_temperature_data,
    fetch_year_gdd,
)
from butterfly_planner.datasources.gdd.compute import (
    compute_accumulated_gdd,
    compute_daily_gdd,
    compute_normals,
    correlate_observations_with_gdd,
)
from butterfly_planner.datasources.gdd.models import (
    DEFAULT_BASE_TEMP_F,
    DEFAULT_UPPER_CUTOFF_F,
    DailyGDD,
    DayOfYearStats,
    NormalGDD,
    SpeciesGDDProfile,
    YearGDD,
)
from butterfly_planner.datasources.gdd.serialization import (
    normals_to_dict,
    species_profiles_to_dict,
    year_gdd_to_dict,
)

__all__ = [
    "ARCHIVE_API",
    "DEFAULT_BASE_TEMP_F",
    "DEFAULT_UPPER_CUTOFF_F",
    "DailyGDD",
    "DayOfYearStats",
    "NormalGDD",
    "SpeciesGDDProfile",
    "YearGDD",
    "compute_accumulated_gdd",
    "compute_daily_gdd",
    "compute_normals",
    "correlate_observations_with_gdd",
    "fetch_temperature_data",
    "fetch_year_gdd",
    "normals_to_dict",
    "species_profiles_to_dict",
    "year_gdd_to_dict",
]
