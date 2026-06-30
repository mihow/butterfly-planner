"""
Visualize the Hamilton DAG for the analysis layer.

Generates a textual representation showing the dependency flow.
"""

from __future__ import annotations

# Import the module to visualize
import prototype_basic_dag
from hamilton import base, driver


def main() -> None:
    """Generate DAG visualization."""

    # Create Hamilton driver
    config = {}
    dr = driver.Driver(
        config,
        prototype_basic_dag,
        adapter=base.SimplePythonGraphAdapter()
    )

    print("Hamilton Analysis DAG Visualization")
    print("=" * 70)

    # Get all nodes
    nodes = dr.list_available_variables()

    print(f"\nTotal nodes in DAG: {len(nodes)}")
    print("\nAll Nodes:")
    for node in sorted(nodes, key=lambda n: n.name):
        print(f"  - {node.name}")

    # Print dependency structure
    print("\n" + "=" * 70)
    print("Dependency Flow (source → transformation → output):")
    print("=" * 70)

    print("""
┌─────────────────────┐
│  SOURCE NODES       │  (No dependencies - data loaders)
├─────────────────────┤
│ observations_raw    │──┐
│ weather_data_raw    │──┼───┐
│ gdd_year_data       │──┼───┼───┐
└─────────────────────┘  │   │   │
                         │   │   │
┌─────────────────────┐  │   │   │
│  TRANSFORMATION     │  │   │   │
├─────────────────────┤  │   │   │
│ weather_by_date     │◄─┘   │   │
└─────────────────────┘      │   │
         │                   │   │
         │    ┌──────────────┘   │
         │    │                  │
         ▼    ▼                  ▼
┌──────────────────────┐ ┌─────────────────────┐
│  FINAL OUTPUTS       │ │  FINAL OUTPUTS      │
├──────────────────────┤ ├─────────────────────┤
│observations_with_    │ │ species_gdd_        │
│  weather             │ │   profiles          │
└──────────────────────┘ └─────────────────────┘

Dependencies explained:
  1. weather_by_date depends on weather_data_raw
  2. observations_with_weather depends on observations_raw AND weather_by_date
  3. species_gdd_profiles depends on observations_raw AND gdd_year_data
    """)

    print("=" * 70)
    print("\nKey Benefits of Hamilton DAG:")
    print("-" * 70)
    print("""
1. Automatic dependency resolution - Hamilton wires the graph from function signatures
2. Type safety - Function inputs/outputs are type-annotated
3. Testability - Each function is a pure transformation, easy to unit test
4. Visibility - Can visualize and understand data flow
5. Reusability - Functions can be composed into different execution paths
6. No manual ordering - Just declare what depends on what via parameters
    """)


if __name__ == "__main__":
    main()
