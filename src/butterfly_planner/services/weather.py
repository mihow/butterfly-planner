"""Backward-compatibility re-exports from datasources.weather.

All code has moved to butterfly_planner.datasources.weather/.
This module re-exports the public API so existing imports keep working
until all callers are updated.
"""

from butterfly_planner.datasources.weather.client import (  # noqa: F401
    OPEN_METEO_API,
    OPEN_METEO_HISTORICAL,
)
from butterfly_planner.datasources.weather.historical import (  # noqa: F401
    fetch_historical_daily,
)
