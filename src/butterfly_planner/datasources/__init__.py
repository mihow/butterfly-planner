"""External data source integrations.

Each subdirectory is one data source with a consistent structure:

    datasources/{name}/
    ├── __init__.py       # Public API re-exports
    ├── client.py         # API URLs, constants, rate limiting
    ├── models.py         # Dataclasses for API responses (optional)
    └── {feature}.py      # Fetch functions (one per endpoint/concept)

Adding a new datasource
-----------------------
1. Create ``datasources/{name}/`` with files above.
   See ``weather/`` for a minimal example, ``inaturalist/`` for a richer one.

2. Write fetch functions that return dicts or dataclasses::

       from butterfly_planner.services.http import session

       def fetch_something(lat, lon) -> dict[str, Any]:
           resp = session.get(API_URL, params={...})
           resp.raise_for_status()
           return resp.json()

3. Re-export public API in ``__init__.py`` with ``__all__``.

4. Wire into the pipeline (see ``flows/fetch.py``):
   - Add a ``@task`` that takes a ``Location`` and calls your fetch function
     with the location's point, bbox or timezone
   - Add the cache path to ``LocationPaths`` in ``flows/paths.py``, so each
     location gets its own file (e.g. ``live/<slug>/mydata.json``)
   - Call ``store.write(path, data, source="...", valid_until=...)``
   - Add the task call to ``_fetch_location()``

5. Add tests in ``tests/test_{name}.py``.
"""
