"""JSON serialization helpers for GDD data structures."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from butterfly_planner.datasources.gdd.models import (
        DayOfYearStats,
        SpeciesGDDProfile,
        YearGDD,
    )


def year_gdd_to_dict(year_gdd: YearGDD) -> dict[str, Any]:
    """Serialize a YearGDD to a JSON-compatible dict.

    Args:
        year_gdd: The YearGDD to serialize.

    Returns:
        Dict with year, total, and daily entries.
    """
    return {
        "year": year_gdd.year,
        "total_gdd": round(year_gdd.total, 1),
        "daily": [
            {
                "date": entry.date.isoformat(),
                "tmax": round(entry.tmax_f, 1),
                "tmin": round(entry.tmin_f, 1),
                "gdd": round(entry.gdd, 1),
                "accumulated": round(entry.accumulated, 1),
            }
            for entry in year_gdd.daily
        ],
    }


def normals_to_dict(stats: list[DayOfYearStats], year_range: str) -> dict[str, Any]:
    """Serialize GDD normals to a JSON-compatible dict.

    Args:
        stats: List of per-day-of-year statistics.
        year_range: Human-readable year range string (e.g. "1996-2025").

    Returns:
        Dict with year_range and by_doy entries.
    """
    return {
        "year_range": year_range,
        "by_doy": [
            {
                "doy": s.doy,
                "mean_accumulated": round(s.mean_accumulated, 1),
                "stddev": round(s.stddev, 1),
            }
            for s in stats
        ],
    }


def species_profiles_to_dict(
    profiles: dict[str, SpeciesGDDProfile],
) -> list[dict[str, Any]]:
    """Serialize species GDD profiles to a JSON-compatible list.

    Args:
        profiles: Dict mapping scientific name to profile.

    Returns:
        List of profile dicts, sorted by median GDD.
    """
    sorted_profiles = sorted(profiles.values(), key=lambda p: p.gdd_median)
    return [
        {
            "scientific_name": p.scientific_name,
            "common_name": p.common_name,
            "observation_count": p.observation_count,
            "gdd_min": round(p.gdd_min, 0),
            "gdd_p10": round(p.gdd_p10, 0),
            "gdd_median": round(p.gdd_median, 0),
            "gdd_p90": round(p.gdd_p90, 0),
            "gdd_max": round(p.gdd_max, 0),
        }
        for p in sorted_profiles
    ]
