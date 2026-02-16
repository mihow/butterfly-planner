"""Correlate butterfly observations with Growing Degree Days.

Cross-references iNaturalist observation dates with accumulated GDD
to build species emergence profiles — answering "at what GDD range
does each species appear?"
"""

from __future__ import annotations

import statistics
from datetime import date
from typing import Any

from butterfly_planner.datasources.gdd.models import SpeciesGDDProfile, YearGDD


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
        deciles = statistics.quantiles(sorted_vals, n=10, method="inclusive")
        profiles[sci_name] = SpeciesGDDProfile(
            scientific_name=sci_name,
            common_name=species_names.get(sci_name, sci_name),
            observation_count=n,
            gdd_min=sorted_vals[0],
            gdd_p10=deciles[0],
            gdd_median=statistics.median(sorted_vals),
            gdd_p90=deciles[8],
            gdd_max=sorted_vals[-1],
        )

    return profiles
