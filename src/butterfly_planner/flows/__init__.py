"""Prefect flows for data pipeline orchestration.

Thin orchestrators that wire together datasources, store, analysis, and renderers.

Flows:
  - fetch: Check store freshness → fetch stale sources → save via DataStore
  - build: Load from store → render HTML → write to derived/site/

Usage:
    python -m butterfly_planner.flows.fetch
    python -m butterfly_planner.flows.build
"""
