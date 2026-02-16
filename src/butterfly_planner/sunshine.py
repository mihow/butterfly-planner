"""Backward-compatibility re-exports from datasources.sunshine.

All code has moved to butterfly_planner.datasources.sunshine/.
This module re-exports the public API so existing imports keep working
until all callers are updated.
"""

from butterfly_planner.datasources.sunshine import (  # noqa: F401
    ENSEMBLE_API,
    FORECAST_API,
    DailySunshine,
    EnsembleSunshine,
    SunshineSlot,
    fetch_16day_sunshine,
    fetch_ensemble_sunshine,
    fetch_today_15min_sunshine,
    get_daylight_slots,
    get_peak_sunshine_window,
    get_total_sunshine_minutes,
    summarize_weekly_sunshine,
)
