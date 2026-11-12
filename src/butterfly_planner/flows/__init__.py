"""Prefect flows for data pipeline orchestration.

Thin orchestrators that wire together datasources, store, analysis, and renderers.

Flows:
  - fetch: Check store freshness → fetch stale sources → save via DataStore
  - build: Load from store → render HTML → write to derived/site/

Both flows run once per location in ``reference.geography.LOCATIONS``. Each
location reads and writes its own cache folder (see ``paths.py``) and gets
its own page: the default location at the site root and every other one in
its own subfolder.

Usage:
    python -m butterfly_planner.flows.fetch
    python -m butterfly_planner.flows.build
"""
