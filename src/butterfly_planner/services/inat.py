"""Backward-compatibility re-exports from datasources.inaturalist.client.

All code has moved to butterfly_planner.datasources.inaturalist.client.
This module re-exports the public API so existing imports keep working
until all callers are updated.
"""

from butterfly_planner.datasources.inaturalist.client import (  # noqa: F401
    API_BASE,
    BUTTERFLIES,
    LEPIDOPTERA,
    MAX_PER_PAGE,
    MAX_RESULTS,
    MIN_REQUEST_INTERVAL,
    OREGON,
    WASHINGTON,
    get_histogram,
    get_observations,
    get_observations_paginated,
    get_species_counts,
)
