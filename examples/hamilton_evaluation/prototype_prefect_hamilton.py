"""
Prototype 3: Prefect + Hamilton Integration

This demonstrates how Prefect (macro-orchestration) and Hamilton
(micro-orchestration) work together. Prefect handles scheduling, retries,
and flow-level coordination. Hamilton handles function-level DAG within
the analysis step.
"""

from __future__ import annotations

# Import the actual store from the project
import os
import sys
from pathlib import Path
from typing import Any

from hamilton import base, driver
from prefect import flow, task

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../src'))
from butterfly_planner.store import DataStore

# =============================================================================
# Hamilton Analysis Functions
# =============================================================================


def observations_data(raw_observations: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Process raw observations.

    In Hamilton, we can declare dependencies via function parameters.
    """
    return [obs for obs in raw_observations if obs.get("species")]


def weather_lookup(raw_weather: dict[str, Any]) -> dict[str, dict[str, Any]]:
    """Transform weather into date-keyed lookup."""
    if not raw_weather:
        return {}

    w_daily = raw_weather.get("daily", {})
    w_dates = w_daily.get("time", [])

    weather_by_date: dict[str, dict[str, Any]] = {}
    for j, w_date in enumerate(w_dates):
        weather_by_date[w_date] = {
            "high_c": w_daily.get("temperature_2m_max", [None])[j],
            "low_c": w_daily.get("temperature_2m_min", [None])[j],
        }

    return weather_by_date


def enriched_observations(
    observations_data: list[dict[str, Any]],
    weather_lookup: dict[str, dict[str, Any]],
) -> list[dict[str, Any]]:
    """Enrich observations with weather data."""
    enriched: list[dict[str, Any]] = []
    for obs in observations_data:
        obs_date = obs.get("observed_on", "")
        weather = weather_lookup.get(obs_date)
        enriched.append({**obs, "weather": weather})
    return enriched


def analysis_summary(enriched_observations: list[dict[str, Any]]) -> dict[str, Any]:
    """Compute summary statistics."""
    return {
        "total_observations": len(enriched_observations),
        "with_weather": sum(1 for obs in enriched_observations if obs.get("weather")),
        "species_count": len({obs.get("species") for obs in enriched_observations}),
    }


# =============================================================================
# Prefect Tasks & Flow
# =============================================================================


@task(name="load-from-store")
def load_from_store(store: DataStore, path: str) -> dict[str, Any]:
    """Prefect task: Load data from store.

    Prefect handles:
    - Retry logic if store read fails
    - Logging and observability
    - Task-level caching (if configured)
    """
    data = store.read(Path(path))
    if data is None:
        return {}
    print(f"📦 Loaded from {path}")
    return data


@task(name="run-hamilton-analysis")
def run_hamilton_analysis(
    observations: dict[str, Any],
    weather: dict[str, Any],
) -> dict[str, Any]:
    """Prefect task: Run Hamilton DAG for analysis.

    This is where Hamilton shines - it orchestrates the function-level
    dependencies within this single task.

    Prefect sees this as one task. Hamilton sees it as a multi-node DAG.
    """
    print("🔄 Running Hamilton analysis DAG...")

    # Create Hamilton driver with our analysis functions
    config = {}
    dr = driver.Driver(config, sys.modules[__name__], adapter=base.SimplePythonGraphAdapter())

    # Execute the DAG with provided inputs
    results = dr.execute(
        final_vars=["enriched_observations", "analysis_summary"],
        inputs={
            "raw_observations": observations.get("observations", []),
            "raw_weather": weather,
        },
    )

    print(f"✓ Analysis complete: {results['analysis_summary']}")
    return results


@task(name="save-results")
def save_results(store: DataStore, results: dict[str, Any]) -> Path:
    """Prefect task: Save analysis results to store."""
    from datetime import UTC, datetime, timedelta

    path = Path("derived/analysis_results.json")
    store.write(
        path,
        results,
        source="hamilton-analysis",
        valid_until=datetime.now(UTC) + timedelta(hours=1),
    )

    full = store.derived / "analysis_results.json"
    print(f"💾 Saved results to {full}")
    return full


@flow(name="analyze-butterflies")
def analyze_butterflies_flow(store_path: Path) -> dict[str, Any]:
    """Prefect flow: Macro-orchestration of the analysis pipeline.

    Prefect handles:
    - Flow-level scheduling (run daily at 6am)
    - Cross-task coordination
    - Retry policies
    - Notifications on failure

    Hamilton (within run_hamilton_analysis) handles:
    - Function-level DAG
    - Automatic dependency resolution
    - Data transformations
    """
    print("🚀 Starting butterfly analysis flow (Prefect)")
    print("=" * 70)

    store = DataStore(store_path)

    # Prefect orchestrates these tasks in order
    observations = load_from_store(store, "live/inaturalist.json")
    weather = load_from_store(store, "live/weather.json")

    # Hamilton orchestrates the analysis DAG within this task
    results = run_hamilton_analysis(observations, weather)

    # Save the results
    output_path = save_results(store, results)

    print("=" * 70)
    print(f"✓ Flow complete. Results: {output_path}")

    return results


# =============================================================================
# Main
# =============================================================================


def main() -> None:
    """Demonstrate Prefect + Hamilton integration."""

    print("Prefect + Hamilton Integration Prototype")
    print("=" * 70)
    print()

    # Setup mock data
    print("Setup: Creating mock data store...")
    from datetime import UTC, datetime, timedelta
    temp_store = DataStore(Path("/tmp/prefect_hamilton_test"))

    temp_store.write(
        Path("live/inaturalist.json"),
        {
            "observations": [
                {"species": "Papilio rutulus", "observed_on": "2024-05-15"},
                {"species": "Vanessa cardui", "observed_on": "2024-04-10"},
                {"species": "Papilio rutulus", "observed_on": "2024-05-20"},
            ]
        },
        source="mock-inat",
        valid_until=datetime.now(UTC) + timedelta(hours=1),
    )

    temp_store.write(
        Path("live/weather.json"),
        {
            "daily": {
                "time": ["2024-04-10", "2024-05-15", "2024-05-20"],
                "temperature_2m_max": [18, 22, 24],
                "temperature_2m_min": [8, 12, 14],
            }
        },
        source="mock-weather",
        valid_until=datetime.now(UTC) + timedelta(hours=1),
    )
    print("✓ Mock data ready\n")

    # Run the Prefect flow
    analyze_butterflies_flow(Path("/tmp/prefect_hamilton_test"))

    print()
    print("=" * 70)
    print("Architecture Summary:")
    print("=" * 70)
    print("""
┌─────────────────────────────────────────────────────────────────┐
│                      PREFECT FLOW                               │
│                (Macro-Orchestration)                            │
│                                                                 │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐        │
│  │ Load Task 1  │→ │ Load Task 2  │→ │ Analysis     │→ Save  │
│  │ (iNat data)  │  │ (Weather)    │  │ Task         │        │
│  └──────────────┘  └──────────────┘  └──────┬───────┘        │
│                                              │                 │
│  Prefect handles:                            ▼                 │
│  • Scheduling                    ┌───────────────────────┐    │
│  • Retries                       │   HAMILTON DAG        │    │
│  • Task coordination             │ (Micro-Orchestration) │    │
│  • Observability                 │                       │    │
│                                  │  observations_data    │    │
│                                  │          ↓            │    │
│                                  │    weather_lookup     │    │
│                                  │          ↓            │    │
│                                  │  enriched_observations│    │
│                                  │          ↓            │    │
│                                  │   analysis_summary    │    │
│                                  │                       │    │
│                                  │ Hamilton handles:     │    │
│                                  │ • Function deps       │    │
│                                  │ • Auto-wiring         │    │
│                                  │ • Type safety         │    │
│                                  └───────────────────────┘    │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘

Key Insights:

1. PREFECT = Macro-orchestration
   - Schedules when the pipeline runs
   - Manages task-level retries and failure handling
   - Provides observability across the entire workflow
   - Coordinates data loading, processing, and saving

2. HAMILTON = Micro-orchestration
   - Manages function-level dependencies WITHIN the analysis task
   - Automatically wires data transformations
   - Makes the analysis logic testable and composable
   - No need to manually order analysis functions

3. THEY COMPOSE PERFECTLY:
   - Prefect flow → Hamilton task → Pure functions
   - Different levels of abstraction
   - No overlap in responsibility
   - Clean separation of concerns

4. When to use what:
   - Use Prefect for: "Run this pipeline daily", "Retry on failure"
   - Use Hamilton for: "This analysis depends on these inputs"
   - Use store.py for: "Cache this data for 6 hours"

5. Scale consideration:
   - For 3-5 analysis functions: Hamilton might be overkill
   - For 10+ analysis functions with complex dependencies: Hamilton shines
   - Current butterfly-planner has ~5 analysis modules → marginal benefit
   - BUT: If adding more datasources/analyses, Hamilton prevents spaghetti
    """)


if __name__ == "__main__":
    main()
