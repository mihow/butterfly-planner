"""
Prototype 2: Hamilton with store.py Integration

This demonstrates how Hamilton can integrate with the existing store.py
caching layer. Hamilton handles function-level DAG orchestration while
store.py handles data persistence and freshness checks.
"""

from __future__ import annotations

# Import the actual store from the project
import os
import sys
from pathlib import Path
from typing import Any

from hamilton import base, driver

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../src'))
from butterfly_planner.store import DataStore

# =============================================================================
# Hamilton Functions with Store Integration
# =============================================================================


def store() -> DataStore:
    """Provide the data store instance.

    In Hamilton, this is a configuration input that can be provided
    at execution time or defaulted here.
    """
    # For prototype, use a temp directory
    import tempfile
    temp_dir = Path(tempfile.mkdtemp())
    return DataStore(temp_dir)


def observations_from_store(store: DataStore) -> list[dict[str, Any]]:
    """Load observations from store with freshness awareness.

    Hamilton function that reads from store.py. If the data is stale,
    this would normally trigger a fetch (via Prefect flow).
    """
    path = Path("live/inaturalist.json")
    data = store.read(path)

    if data is None:
        # In real scenario, would trigger fetch flow
        print("⚠️  No observations in store - would trigger fetch")
        return []

    # Check freshness
    raw = store.read_raw(path)
    if raw:
        valid_until = raw.get("meta", {}).get("valid_until")
        print(f"📦 Loaded observations from store (valid until: {valid_until})")

    return data.get("observations", [])


def weather_from_store(store: DataStore) -> dict[str, Any]:
    """Load weather data from store with freshness awareness."""
    path = Path("live/weather.json")
    data = store.read(path)

    if data is None:
        print("⚠️  No weather data in store - would trigger fetch")
        return {}

    raw = store.read_raw(path)
    if raw:
        valid_until = raw.get("meta", {}).get("valid_until")
        print(f"📦 Loaded weather from store (valid until: {valid_until})")

    return data


def weather_by_date(weather_from_store: dict[str, Any]) -> dict[str, dict[str, Any]]:
    """Transform weather into date-keyed lookup (analysis function)."""
    if not weather_from_store:
        return {}

    w_daily = weather_from_store.get("daily", {})
    w_dates = w_daily.get("time", [])

    weather_lookup: dict[str, dict[str, Any]] = {}
    for j, w_date in enumerate(w_dates):
        weather_lookup[w_date] = {
            "high_c": w_daily.get("temperature_2m_max", [None])[j],
            "low_c": w_daily.get("temperature_2m_min", [None])[j],
            "precip_mm": w_daily.get("precipitation_sum", [None])[j],
            "weather_code": w_daily.get("weather_code", [None])[j],
        }

    print(f"🔄 Transformed weather data into {len(weather_lookup)} daily records")
    return weather_lookup


def enriched_observations(
    observations_from_store: list[dict[str, Any]],
    weather_by_date: dict[str, dict[str, Any]],
) -> list[dict[str, Any]]:
    """Enrich observations with weather (analysis function)."""
    enriched: list[dict[str, Any]] = []
    for obs in observations_from_store:
        obs_date = obs.get("observed_on", "")
        weather = weather_by_date.get(obs_date) if obs_date else None
        enriched.append({**obs, "weather": weather})

    print(f"🔄 Enriched {len(enriched)} observations with weather data")
    return enriched


def save_enriched_to_store(
    store: DataStore,
    enriched_observations: list[dict[str, Any]],
) -> Path:
    """Save enriched observations back to store (derived data).

    Hamilton can also handle writing outputs. This demonstrates
    how derived data flows back into the store.
    """
    from datetime import UTC, datetime, timedelta

    path = Path("derived/enriched_observations.json")
    store.write(
        path,
        {"observations": enriched_observations},
        source="hamilton-analysis",
        valid_until=datetime.now(UTC) + timedelta(hours=1),
    )

    full_path = store.derived / "enriched_observations.json"
    print(f"💾 Saved {len(enriched_observations)} enriched observations to {full_path}")
    return full_path


# =============================================================================
# Driver Execution
# =============================================================================


def main() -> None:
    """Execute the Hamilton DAG with store integration."""

    print("Hamilton + store.py Integration Prototype")
    print("=" * 70)
    print()

    # Create Hamilton driver
    config = {}
    dr = driver.Driver(config, sys.modules[__name__], adapter=base.SimplePythonGraphAdapter())

    # First, populate the store with mock data for the prototype
    print("Setup: Populating store with mock data...")
    print("-" * 70)
    temp_store = DataStore(Path("/tmp/hamilton_store_test"))
    from datetime import UTC, datetime, timedelta

    temp_store.write(
        Path("live/inaturalist.json"),
        {
            "observations": [
                {"species": "Papilio rutulus", "observed_on": "2024-05-15"},
                {"species": "Vanessa cardui", "observed_on": "2024-04-10"},
            ]
        },
        source="mock-inat",
        valid_until=datetime.now(UTC) + timedelta(hours=1),
    )
    temp_store.write(
        Path("live/weather.json"),
        {
            "daily": {
                "time": ["2024-04-10", "2024-05-15"],
                "temperature_2m_max": [18, 22],
                "temperature_2m_min": [8, 12],
                "precipitation_sum": [0, 0],
                "weather_code": [1, 1],
            }
        },
        source="mock-weather",
        valid_until=datetime.now(UTC) + timedelta(hours=1),
    )
    print("✓ Mock data written to store\n")

    # Execute the DAG with the populated store
    print("Executing Hamilton DAG...")
    print("-" * 70)

    # Override the store function with our populated store
    results = dr.execute(
        final_vars=["save_enriched_to_store"],
        overrides={"store": temp_store},
    )

    print()
    print("=" * 70)
    print("Results:")
    print("-" * 70)
    print(f"Output saved to: {results['save_enriched_to_store']}")

    # Verify the output
    saved_data = temp_store.read(Path("derived/enriched_observations.json"))
    if saved_data:
        print(f"\nVerification: Successfully read back {len(saved_data['observations'])} observations")
        for obs in saved_data["observations"]:
            print(f"  - {obs['species']} on {obs['observed_on']}: weather={bool(obs.get('weather'))}")

    print()
    print("=" * 70)
    print("Key Insights:")
    print("=" * 70)
    print("""
1. Hamilton orchestrates the analysis functions (transformations)
2. store.py handles data persistence, freshness, and TTL
3. They are COMPLEMENTARY, not overlapping:
   - Hamilton: Function-level DAG, automatic dependency wiring
   - store.py: File-based caching, freshness checks, metadata

4. Prefect can sit above both:
   - Prefect flow: "If stale, fetch → store → run Hamilton analysis → save"
   - Hamilton: "Given these inputs, compute these outputs"
   - store.py: "Read/write with TTL awareness"

5. Benefits of this architecture:
   - Pure functions in Hamilton make testing easy
   - store.py handles all I/O concerns
   - Prefect handles scheduling and orchestration
   - Each layer has a single responsibility
    """)


if __name__ == "__main__":
    main()
