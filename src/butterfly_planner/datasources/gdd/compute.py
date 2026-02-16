"""Pure GDD computation functions (no I/O).

Formula (modified average method with upper cutoff):

    T_max_adj = min(T_max, upper_cutoff)
    T_min_adj = max(T_min, base_temp)
    GDD_daily = max(0, (T_max_adj + T_min_adj) / 2 - base_temp)
"""

from __future__ import annotations

import statistics
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from datetime import date

from butterfly_planner.datasources.gdd.models import (
    DEFAULT_BASE_TEMP_F,
    DEFAULT_UPPER_CUTOFF_F,
    DailyGDD,
    DayOfYearStats,
    YearGDD,
)


def compute_daily_gdd(
    tmax_f: float,
    tmin_f: float,
    base_temp_f: float = DEFAULT_BASE_TEMP_F,
    upper_cutoff_f: float = DEFAULT_UPPER_CUTOFF_F,
) -> float:
    """Compute GDD for a single day using the modified average method.

    Applies horizontal cutoff: temperatures above the upper threshold are
    capped (not zeroed). Temperatures below the base are raised to the base.

    Args:
        tmax_f: Daily maximum temperature in Fahrenheit.
        tmin_f: Daily minimum temperature in Fahrenheit.
        base_temp_f: Base development temperature (default 50 F).
        upper_cutoff_f: Upper temperature cap (default 86 F).

    Returns:
        Growing degree days for the day (>= 0).
    """
    tmax_adj = min(tmax_f, upper_cutoff_f)
    tmin_adj = max(tmin_f, base_temp_f)
    avg = (tmax_adj + tmin_adj) / 2
    return max(0.0, avg - base_temp_f)


def compute_accumulated_gdd(
    daily_temps: list[tuple[date, float, float]],
    base_temp_f: float = DEFAULT_BASE_TEMP_F,
    upper_cutoff_f: float = DEFAULT_UPPER_CUTOFF_F,
) -> list[DailyGDD]:
    """Compute daily and accumulated GDD from a sequence of (date, tmax, tmin).

    Args:
        daily_temps: List of (date, tmax_f, tmin_f) tuples, ordered by date.
        base_temp_f: Base development temperature in Fahrenheit.
        upper_cutoff_f: Upper temperature cap in Fahrenheit.

    Returns:
        List of DailyGDD entries with running accumulation.
    """
    results: list[DailyGDD] = []
    accumulated = 0.0
    for dt, tmax, tmin in daily_temps:
        gdd = compute_daily_gdd(tmax, tmin, base_temp_f, upper_cutoff_f)
        accumulated += gdd
        results.append(
            DailyGDD(date=dt, tmax_f=tmax, tmin_f=tmin, gdd=gdd, accumulated=accumulated)
        )
    return results


def compute_normals(
    yearly_data: list[YearGDD],
) -> list[DayOfYearStats]:
    """Compute mean and stddev of accumulated GDD by day-of-year.

    Used to build the "30-year normal" band on the timeline chart.

    Args:
        yearly_data: List of YearGDD, one per historical year.

    Returns:
        List of DayOfYearStats for each day-of-year present in the data.
    """
    # Collect accumulated values by day-of-year across all years
    by_doy: dict[int, list[float]] = {}
    for year_gdd in yearly_data:
        for entry in year_gdd.daily:
            doy = entry.date.timetuple().tm_yday
            by_doy.setdefault(doy, []).append(entry.accumulated)

    stats: list[DayOfYearStats] = []
    for doy in sorted(by_doy):
        values = by_doy[doy]
        mean = statistics.mean(values)
        stddev = statistics.stdev(values) if len(values) >= 2 else 0.0
        stats.append(DayOfYearStats(doy=doy, mean_accumulated=mean, stddev=stddev))

    return stats


# Re-export from analysis layer for backward compatibility
from butterfly_planner.analysis.species_gdd import (  # noqa: E402, F401
    correlate_observations_with_gdd,
)
