"""
Growing Degree Days (GDD) computation and data fetching.

GDD measures accumulated heat units over a growing season. It is the standard
phenological metric for predicting insect development — answering "how much
warmth has accumulated?" rather than relying on calendar dates.

Formula (modified average method with upper cutoff):

    T_max_adj = min(T_max, upper_cutoff)
    T_min_adj = max(T_min, base_temp)
    GDD_daily = max(0, (T_max_adj + T_min_adj) / 2 - base_temp)

Default parameters for butterflies:
    base_temp  = 50 deg F (10 deg C) — standard for Lepidoptera
    upper_cutoff = 86 deg F (30 deg C) — insects stop developing faster above this

References:
    - UMass Extension: Growing Degree Days for Insect Pests
    - USA National Phenology Network: AGDD products
    - Open-Meteo Historical Weather API (data source)
"""

from __future__ import annotations

import statistics
from dataclasses import dataclass, field
from datetime import date, timedelta
from typing import Any

import requests

# Open-Meteo archive endpoint for historical daily temperatures
ARCHIVE_API = "https://archive-api.open-meteo.com/v1/archive"

# Default GDD parameters for butterflies / general insects
DEFAULT_BASE_TEMP_F = 50.0
DEFAULT_UPPER_CUTOFF_F = 86.0


# ---------------------------------------------------------------------------
# Data structures
# ---------------------------------------------------------------------------


@dataclass
class DailyGDD:
    """GDD computation result for a single day."""

    date: date
    tmax_f: float
    tmin_f: float
    gdd: float
    accumulated: float


@dataclass
class YearGDD:
    """Full-year (or partial-year) GDD accumulation."""

    year: int
    daily: list[DailyGDD] = field(default_factory=list)

    @property
    def total(self) -> float:
        """Total accumulated GDD for the year so far."""
        return self.daily[-1].accumulated if self.daily else 0.0

    def accumulated_through_doy(self, day_of_year: int) -> float:
        """Return accumulated GDD through a given day-of-year (1-based).

        Args:
            day_of_year: Day of year, 1 = Jan 1.

        Returns:
            Accumulated GDD, or 0.0 if no data for that day.
        """
        for entry in self.daily:
            if entry.date.timetuple().tm_yday == day_of_year:
                return entry.accumulated
        return 0.0


@dataclass
class NormalGDD:
    """Multi-year GDD normals: mean and standard deviation by day-of-year."""

    year_range: str
    by_doy: list[DayOfYearStats] = field(default_factory=list)


@dataclass
class DayOfYearStats:
    """GDD statistics for a single day-of-year across multiple years."""

    doy: int
    mean_accumulated: float
    stddev: float


@dataclass
class SpeciesGDDProfile:
    """GDD range statistics for a butterfly species.

    Built by cross-referencing observation dates with accumulated GDD
    at the configured location.
    """

    scientific_name: str
    common_name: str
    observation_count: int
    gdd_min: float
    gdd_p10: float
    gdd_median: float
    gdd_p90: float
    gdd_max: float


# ---------------------------------------------------------------------------
# Core computation (pure functions, no I/O)
# ---------------------------------------------------------------------------


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


# ---------------------------------------------------------------------------
# Data fetching (Open-Meteo archive API)
# ---------------------------------------------------------------------------


def fetch_temperature_data(
    lat: float,
    lon: float,
    start: date,
    end: date,
) -> list[tuple[date, float, float]]:
    """Fetch daily min/max temperatures from the Open-Meteo archive API.

    Args:
        lat: Latitude of the location.
        lon: Longitude of the location.
        start: Start date (inclusive).
        end: End date (inclusive).

    Returns:
        List of (date, tmax_f, tmin_f) tuples.

    Raises:
        requests.HTTPError: If the API request fails.
    """
    params: dict[str, str | float] = {
        "latitude": lat,
        "longitude": lon,
        "start_date": start.isoformat(),
        "end_date": end.isoformat(),
        "daily": "temperature_2m_max,temperature_2m_min",
        "temperature_unit": "fahrenheit",
        "timezone": "America/Los_Angeles",
    }

    resp = requests.get(ARCHIVE_API, params=params, timeout=30)
    resp.raise_for_status()
    data = resp.json()

    daily = data.get("daily", {})
    dates = daily.get("time", [])
    tmax_values = daily.get("temperature_2m_max", [])
    tmin_values = daily.get("temperature_2m_min", [])

    results: list[tuple[date, float, float]] = []
    for i, date_str in enumerate(dates):
        dt = date.fromisoformat(date_str)
        tmax = tmax_values[i] if tmax_values[i] is not None else 0.0
        tmin = tmin_values[i] if tmin_values[i] is not None else 0.0
        results.append((dt, tmax, tmin))

    return results


def fetch_year_gdd(
    lat: float,
    lon: float,
    year: int,
    through: date | None = None,
    base_temp_f: float = DEFAULT_BASE_TEMP_F,
    upper_cutoff_f: float = DEFAULT_UPPER_CUTOFF_F,
) -> YearGDD:
    """Fetch temperatures and compute GDD for a full year (or year-to-date).

    Args:
        lat: Latitude.
        lon: Longitude.
        year: Calendar year to fetch.
        through: End date (defaults to Dec 31 or yesterday if current year).
        base_temp_f: Base temperature for GDD computation.
        upper_cutoff_f: Upper cutoff temperature.

    Returns:
        YearGDD with daily GDD entries.
    """
    start = date(year, 1, 1)
    if through is None:
        today = date.today()
        through = today - timedelta(days=1) if year == today.year else date(year, 12, 31)

    temps = fetch_temperature_data(lat, lon, start, through)
    daily = compute_accumulated_gdd(temps, base_temp_f, upper_cutoff_f)
    return YearGDD(year=year, daily=daily)


# ---------------------------------------------------------------------------
# JSON serialization helpers
# ---------------------------------------------------------------------------


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
