"""
Prefect flows for data pipeline.

Flows:
- fetch: Download data from iNat, GBIF, weather APIs
- build: Transform raw data into GeoJSON layers for static site

Usage (local):
    python -m butterfly_planner.flows.fetch
    python -m butterfly_planner.flows.build

Usage (Prefect):
    prefect server start  # Optional, for dashboard
    prefect deployment run 'fetch-data/default'

In GitHub Actions:
    pip install prefect
    python -m butterfly_planner.flows.fetch
    python -m butterfly_planner.flows.build
"""
