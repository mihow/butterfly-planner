"""Cross-datasource joins, correlations, and composite indexes.

Each module combines outputs from 2+ datasources into enriched structures
that renderers can consume directly. This is the domain logic layer.

Dependency rule: analysis/ imports from datasources/ models only.
It never fetches data or produces HTML.

Modules:
  - species_gdd: observations + GDD accumulation -> emergence profiles
  - species_weather: observations + historical weather -> enriched observations
  - weekly_forecast: sunshine + weather forecast -> date-keyed weather lookup

Adding an analysis module
-------------------------
1. Create ``analysis/{name}.py`` with a pure function::

       from butterfly_planner.datasources.gdd import YearGDD
       from butterfly_planner.datasources.inaturalist import ButterflyObservation

       def correlate_something(
           observations: list[ButterflyObservation],
           gdd_data: dict[int, YearGDD],
       ) -> dict[str, SomeProfile]:
           ...

2. Rules:
   - Import datasource *models* only (never call fetch functions here).
   - No I/O, no HTTP, no Prefect decorators.
   - Return dataclasses or dicts that renderers can consume.

3. Wire into the pipeline (see ``flows/build.py``):
   - Call your analysis function after loading data from the store.
   - Pass the result to a renderer.

4. Re-export in ``__init__.py`` and add tests in ``tests/test_{name}.py``.
"""
