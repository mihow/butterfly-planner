"""Backward-compatibility shim for renderers.daily_data.

The daily data contract has moved to
``butterfly_planner.serialization.daily_data``.  Import from there.

This module re-exports the public API so existing code continues to work,
but new code should import directly from the serialization package.
"""

from butterfly_planner.serialization.daily_data import (
    SCHEMA_VERSION,
    WMO_DESCRIPTIONS,
    DailyButterflies,
    DailyData,
    DailyGDD,
    DailySunshine,
    DailyWeather,
    SpeciesRecord,
    build_daily_data,
)

__all__ = [
    "SCHEMA_VERSION",
    "WMO_DESCRIPTIONS",
    "DailyButterflies",
    "DailyData",
    "DailyGDD",
    "DailySunshine",
    "DailyWeather",
    "SpeciesRecord",
    "build_daily_data",
]
