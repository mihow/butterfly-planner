"""Pure GDD computation functions (no I/O).

Formula (modified average method with upper cutoff):

    T_max_adj = min(T_max, upper_cutoff)
    T_min_adj = max(T_min, base_temp)
    GDD_daily = max(0, (T_max_adj + T_min_adj) / 2 - base_temp)
"""

from __future__ import annotations

import statistics
from datetime import date
from typing import Any

from butterfly_planner.datasources.gdd.models import (
    DEFAULT_BASE_TEMP_F,
    DEFAULT_UPPER_CUTOFF_F,
    DailyGDD,
    DayOfYearStats,
    SpeciesGDDProfile,
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


def correlate_observations_with_gdd(
    observations: list[dict[str, Any]],
    year_gdd_lookup: dict[int, YearGDD],
) -> dict[str, SpeciesGDDProfile]:
    """Cross-reference butterfly observations with GDD to build species profiles.

    For each observation, looks up the accumulated GDD on that date (using the
    configured location's GDD — a reasonable approximation since observations are
    already filtered to a bounding box).

    Args:
        observations: List of observation dicts with 'species', 'common_name',
            and 'observed_on' (ISO date string) keys.
        year_gdd_lookup: Mapping of year -> YearGDD for GDD lookups.

    Returns:
        Dict mapping scientific_name -> SpeciesGDDProfile.
    """
    # Collect GDD values per species
    species_gdd: dict[str, list[float]] = {}
    species_names: dict[str, str] = {}

    for obs in observations:
        observed_on = obs.get("observed_on", "")
        species = obs.get("species", "")
        if not observed_on or not species:
            continue

        try:
            obs_date = date.fromisoformat(observed_on[:10])
        except ValueError:
            continue

        year_data = year_gdd_lookup.get(obs_date.year)
        if not year_data:
            continue

        doy = obs_date.timetuple().tm_yday
        acc_gdd = year_data.accumulated_through_doy(doy)
        if acc_gdd > 0:
            species_gdd.setdefault(species, []).append(acc_gdd)
            if species not in species_names:
                species_names[species] = obs.get("common_name") or species

    # Build profiles with percentile statistics
    profiles: dict[str, SpeciesGDDProfile] = {}
    for sci_name, gdd_values in species_gdd.items():
        if len(gdd_values) < 3:
            continue  # Need enough observations for meaningful stats

        sorted_vals = sorted(gdd_values)
        n = len(sorted_vals)
        profiles[sci_name] = SpeciesGDDProfile(
            scientific_name=sci_name,
            common_name=species_names.get(sci_name, sci_name),
            observation_count=n,
            gdd_min=sorted_vals[0],
            gdd_p10=sorted_vals[max(0, int(n * 0.1))],
            gdd_median=statistics.median(sorted_vals),
            gdd_p90=sorted_vals[min(n - 1, int(n * 0.9))],
            gdd_max=sorted_vals[-1],
        )

    return profiles
