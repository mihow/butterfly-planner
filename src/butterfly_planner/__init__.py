"""Butterfly Planner - butterfly abundance and species diversity forecasting.

Architecture::

    datasources/   External APIs (iNaturalist, Open-Meteo weather/sunshine, GDD)
    store.py       Tiered cache with TTL (reference → historical → live → derived)
    analysis/      Cross-datasource logic (species-GDD correlation)
    renderers/     Pure data → HTML (sunshine, sightings, GDD charts)
    flows/         Prefect orchestration (fetch checks freshness, build renders site)
    services/      Shared utilities (HTTP client with retry, future API stubs)

Data flow: datasources → store (cache) → analysis → renderers → derived/site/

Extension points — see each package's docstring for step-by-step guides:
  - New data source:   datasources/__init__.py
  - New analysis:      analysis/__init__.py
  - New UI module:     renderers/__init__.py
"""

__version__ = "0.1.0"
__author__ = "Michael Howden"

from butterfly_planner.config import Settings
from butterfly_planner.schemas import Example

__all__ = ["Example", "Settings", "__version__"]
