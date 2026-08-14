"""
Prototype 1: Basic Hamilton DAG for Analysis Layer

This demonstrates how the existing analysis functions can be expressed as a
Hamilton DAG. Hamilton will automatically wire dependencies based on function
parameter names.
"""

from __future__ import annotations

import statistics
import sys
from datetime import date
from typing import Any

from hamilton import base, driver

# =============================================================================
# Hamilton Functions - Analysis Layer as DAG Nodes
# =============================================================================


def observations_raw() -> list[dict[str, Any]]:
    """Load raw observations (normally from store).

    In Hamilton, this is a "source" node with no inputs.
    """
    # Mock data for prototype
    return [
        {
            "species": "Papilio rutulus",
            "common_name": "Western Tiger Swallowtail",
            "observed_on": "2024-05-15",
            "latitude": 45.5,
            "longitude": -122.6,
        },
        {
            "species": "Papilio rutulus",
            "common_name": "Western Tiger Swallowtail",
            "observed_on": "2024-05-20",
            "latitude": 45.5,
            "longitude": -122.6,
        },
        {
            "species": "Vanessa cardui",
            "common_name": "Painted Lady",
            "observed_on": "2024-04-10",
            "latitude": 45.5,
            "longitude": -122.6,
        },
    ]


def weather_data_raw() -> dict[str, Any]:
    """Load raw weather data (normally from store).

    Another source node.
    """
    return {
        "data": {
            "daily": {
                "time": ["2024-04-10", "2024-05-15", "2024-05-20"],
                "temperature_2m_max": [18, 22, 24],
                "temperature_2m_min": [8, 12, 14],
                "precipitation_sum": [0, 0, 2],
                "weather_code": [1, 1, 61],
            }
        }
    }


def gdd_year_data() -> dict[int, dict[str, Any]]:
    """Load GDD year data (normally from store).

    Another source node.
    """
    # Mock GDD data - day of year -> accumulated GDD
    return {
        2024: {
            "year": 2024,
            "daily": [
                {"doy": i, "gdd_accumulated": i * 5.5}
                for i in range(1, 366)
            ],
        }
    }


def weather_by_date(weather_data_raw: dict[str, Any]) -> dict[str, dict[str, Any]]:
    """Transform weather data into date-keyed lookup.

    Hamilton sees this depends on weather_data_raw and will execute it after.
    This is from analysis/weekly_forecast.py:merge_sunshine_weather.
    """
    if not weather_data_raw:
        return {}

    w_daily = weather_data_raw.get("data", {}).get("daily", {})
    w_dates = w_daily.get("time", [])

    weather_lookup: dict[str, dict[str, Any]] = {}
    for j, w_date in enumerate(w_dates):
        weather_lookup[w_date] = {
            "high_c": w_daily.get("temperature_2m_max", [None])[j],
            "low_c": w_daily.get("temperature_2m_min", [None])[j],
            "precip_mm": w_daily.get("precipitation_sum", [None])[j],
            "weather_code": w_daily.get("weather_code", [None])[j],
        }

    return weather_lookup


def observations_with_weather(
    observations_raw: list[dict[str, Any]],
    weather_by_date: dict[str, dict[str, Any]],
) -> list[dict[str, Any]]:
    """Enrich observations with weather data.

    Hamilton sees this depends on both observations_raw AND weather_by_date.
    This is from analysis/species_weather.py:enrich_observations_with_weather.
    """
    enriched: list[dict[str, Any]] = []
    for obs in observations_raw:
        obs_date = obs.get("observed_on", "")
        weather = weather_by_date.get(obs_date) if obs_date else None
        enriched.append({**obs, "weather": weather})
    return enriched


def species_gdd_profiles(
    observations_raw: list[dict[str, Any]],
    gdd_year_data: dict[int, dict[str, Any]],
) -> dict[str, dict[str, Any]]:
    """Correlate observations with GDD to build species profiles.

    Hamilton sees this depends on observations_raw AND gdd_year_data.
    This is from analysis/species_gdd.py:correlate_observations_with_gdd (simplified).
    """
    # Collect GDD values per species
    species_gdd: dict[str, list[float]] = {}
    species_names: dict[str, str] = {}

    for obs in observations_raw:
        observed_on = obs.get("observed_on", "")
        species = obs.get("species", "")
        if not observed_on or not species:
            continue

        try:
            obs_date = date.fromisoformat(observed_on[:10])
        except ValueError:
            continue

        year_data = gdd_year_data.get(obs_date.year)
        if not year_data:
            continue

        doy = obs_date.timetuple().tm_yday
        # Simplified GDD lookup
        daily = year_data.get("daily", [])
        if doy <= len(daily):
            acc_gdd = daily[doy - 1]["gdd_accumulated"]
            if acc_gdd > 0:
                species_gdd.setdefault(species, []).append(acc_gdd)
                if species not in species_names:
                    species_names[species] = obs.get("common_name") or species

    # Build profiles with statistics
    profiles: dict[str, dict[str, Any]] = {}
    for sci_name, gdd_values in species_gdd.items():
        if len(gdd_values) < 2:
            continue

        sorted_vals = sorted(gdd_values)
        profiles[sci_name] = {
            "scientific_name": sci_name,
            "common_name": species_names.get(sci_name, sci_name),
            "observation_count": len(sorted_vals),
            "gdd_min": sorted_vals[0],
            "gdd_median": statistics.median(sorted_vals),
            "gdd_max": sorted_vals[-1],
        }

    return profiles


# =============================================================================
# Driver Execution
# =============================================================================


def main() -> None:
    """Execute the Hamilton DAG."""

    # Create Hamilton driver - it discovers all functions in this module
    # Use DictResult for non-pandas outputs
    config = {}
    dr = driver.Driver(config, sys.modules[__name__], adapter=base.SimplePythonGraphAdapter())

    print("Hamilton DAG Structure")
    print("=" * 60)

    # Visualize the DAG
    print("\nDAG Nodes (Functions):")
    for node in dr.list_available_variables():
        print(f"  - {node}")

    print("\n" + "=" * 60)
    print("Executing DAG to compute 'species_gdd_profiles' and 'observations_with_weather'")
    print("=" * 60 + "\n")

    # Execute the DAG - Hamilton will figure out what needs to run
    results = dr.execute(
        final_vars=["species_gdd_profiles", "observations_with_weather"],
    )

    print("Results:")
    print("-" * 60)

    print("\nSpecies GDD Profiles:")
    for species, profile in results["species_gdd_profiles"].items():
        print(f"  {species}:")
        print(f"    Common: {profile['common_name']}")
        print(f"    Observations: {profile['observation_count']}")
        print(f"    GDD Range: {profile['gdd_min']:.1f} - {profile['gdd_max']:.1f}")
        print(f"    GDD Median: {profile['gdd_median']:.1f}")

    print("\nObservations with Weather:")
    for obs in results["observations_with_weather"]:
        print(f"  {obs['common_name']} on {obs['observed_on']}:")
        weather = obs.get("weather")
        if weather:
            print(f"    Temp: {weather['low_c']}°C - {weather['high_c']}°C")
            print(f"    Precip: {weather['precip_mm']}mm")
        else:
            print("    No weather data")

    print("\n" + "=" * 60)
    print("Key Observations:")
    print("=" * 60)
    print("""
1. Hamilton automatically wired the dependencies:
   - observations_with_weather depends on: observations_raw, weather_by_date
   - weather_by_date depends on: weather_data_raw
   - species_gdd_profiles depends on: observations_raw, gdd_year_data

2. Functions are pure transformations with explicit inputs/outputs

3. No manual dependency management or ordering required

4. The DAG can be visualized and debugged independently
""")


if __name__ == "__main__":
    main()
