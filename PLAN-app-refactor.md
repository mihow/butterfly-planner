# Plan: Refactor App into Module Directories

## Problem

The app has outgrown its flat-file structure. Several modules carry most of the weight:

| Module | Lines | Concern count |
|---|---|---|
| `flows/build.py` | 753 | 7+ (rendering, templates, palettes, utils, orchestration) |
| `gdd.py` | 737 | 5 (computation, HTTP fetch, serialization, rendering, cross-source correlation) |
| `inaturalist.py` | 474 | 3 (species, observations, weekly aggregation) |
| `sunshine.py` | 368 | 3 (15-min, daily, ensemble) |
| `flows/fetch.py` | 309 | 4 (weather, sunshine, iNat, historical weather) |

Beyond code bloat, there are two structural problems:

1. **Documentation is flat** — CLAUDE.md carries project instructions, learnings, and style rules all in one place. AI agents either load everything or nothing. We need tiered documentation so agents can fetch the right level of detail.

2. **No separation between data source logic, cross-source analysis, and presentation.** Cross-datasource joins (e.g., weather conditions on observation dates, GDD correlation with species emergence) are scattered across `build.py`, `fetch.py`, and `gdd.py`. As we add more datasources (flower phenology, US Pests, elevation, campgrounds) and build composite indexes, this will become unmanageable.

## What This Project Is Becoming

Categorically, this is a **geospatial decision-support system** — a multi-source environmental data fusion platform with a forecasting/planning UI. It mirrors:

- **Spatial Data Infrastructure (SDI) / Environmental Dashboard** — like what state natural resource agencies build (USGS, NOAA Climate.gov, USA-NPN). Ingest raster and point data from many sources, compute derived layers, present composite views.
- **ELT Data Pipeline** — the fetch→store→analyze→render flow is textbook Extract-Load-Transform. Prefect already handles orchestration. The "warehouse" is local files; the "transforms" are analysis modules.
- **Multi-Criteria Decision Analysis (MCDA)** — the planned "viewing score" and "best day to go" features weight multiple factors (GDD, weather, bloom stage, species likelihood, drive time) to produce ranked recommendations.

The closest analogy is a **personal-scale version of Google Earth Engine** — many raster/vector data sources, temporal alignment, composite analysis, map output — scoped to a specific domain and rendered as a static site.

---

## Proposed Structure

```
src/butterfly_planner/
├── __init__.py                      # Package version, top-level exports
├── cli.py                           # CLI entry point (unchanged)
├── config.py                        # Settings (unchanged)
├── schemas.py                       # Pydantic models (unchanged)
├── store.py                         # NEW — DataStore: read/write/is_fresh for cached data
│
├── flows/                           # Prefect orchestration only
│   ├── __init__.py                  # Overview: what flows exist, when to run them
│   ├── fetch.py                     # Slim: check freshness → fetch stale → save
│   └── build.py                     # Slim: load → analyze → render → write HTML
│
├── datasources/                     # NEW — one module per external data source
│   ├── __init__.py                  # Overview: available data sources, shared patterns
│   ├── inaturalist/
│   │   ├── __init__.py              # Public API: get_current_week_species, etc.
│   │   ├── README.md                # Data source docs: API, rate limits, auth, gotchas
│   │   ├── client.py                # Low-level API (from services/inat.py)
│   │   ├── species.py               # SpeciesRecord, fetch_species_counts, histograms
│   │   ├── observations.py          # ButterflyObservation, fetch_observations_for_month
│   │   └── weekly.py                # get_current_week_species, get_species_for_week
│   │
│   ├── weather/
│   │   ├── __init__.py              # Public API: fetch_forecast, fetch_historical
│   │   ├── README.md                # Open-Meteo API docs, endpoints, limits
│   │   ├── client.py                # Low-level HTTP (from services/weather.py)
│   │   ├── forecast.py              # 16-day forecast fetch + parse
│   │   └── historical.py            # Archive API, date batching logic
│   │
│   ├── sunshine/
│   │   ├── __init__.py              # Public API: fetch_today, fetch_16day, fetch_ensemble
│   │   ├── README.md                # Open-Meteo sunshine endpoints, ensemble docs
│   │   ├── models.py                # SunshineSlot, DailySunshine, EnsembleSunshine
│   │   ├── today.py                 # fetch_today_15min_sunshine
│   │   ├── daily.py                 # fetch_16day_sunshine
│   │   └── ensemble.py              # fetch_ensemble_sunshine
│   │
│   └── gdd/
│       ├── __init__.py              # Public API: fetch_year_gdd, compute_accumulated_gdd
│       ├── README.md                # Open-Meteo archive API, GDD formula, base temps
│       ├── client.py                # HTTP fetch from Open-Meteo archive (from gdd.py)
│       ├── compute.py               # Pure GDD computation: daily, accumulated, normals
│       ├── models.py                # DailyGDD, YearGDD, NormalGDD, DayOfYearStats
│       └── serialization.py         # year_gdd_to_dict, year_gdd_from_dict
│
├── analysis/                        # NEW — cross-datasource joins and composite logic
│   ├── __init__.py                  # Overview: what analyses exist, data flow
│   ├── species_weather.py           # Join observations + historical weather by date
│   ├── species_gdd.py               # Correlate observations with GDD → SpeciesGDDProfile
│   ├── weekly_forecast.py           # Merge sunshine + weather into unified forecast view
│   └── viewing_index.py             # (future) Composite score: GDD + flowers + weather
│
├── renderers/                       # NEW — pure functions: data → HTML
│   ├── __init__.py                  # Overview: rendering pipeline, shared conventions
│   ├── sunshine.py                  # Today timeline + 16-day table renderers
│   ├── sightings_map.py             # Leaflet map generation
│   ├── sightings_table.py           # Species sightings HTML table
│   ├── species_palette.py           # SpeciesStyle, colors, initials
│   ├── gdd.py                       # GDD today card + timeline SVG renderers
│   └── weather_utils.py             # c_to_f, wmo_code_to_conditions, WMO_CONDITIONS
│
├── templates/                       # Jinja2 templates (already exists, mostly unchanged)
│   ├── base.html.j2
│   ├── sunshine_today.html.j2
│   ├── sunshine_16day.html.j2
│   ├── sightings_table.html.j2
│   ├── sightings_map.html.j2
│   ├── sightings_map_script.html.j2
│   ├── gdd_today.html.j2
│   └── gdd_timeline.html.j2
│
└── core.py                          # Minimal shared utilities (if any remain)
```

### Data flow

```
datasources/  →  store (save)  →  analysis/  →  renderers/  →  site/
  (fetch)         (cache)          (combine)      (present)
```

Each layer only imports from the layers to its left. `flows/` orchestrates the pipeline but contains no domain logic.

### What gets deleted

- `services/` directory — absorbed into `datasources/`
- `inaturalist.py` (top-level) — split into `datasources/inaturalist/`
- `sunshine.py` (top-level) — split into `datasources/sunshine/`
- `gdd.py` (top-level, 737 lines) — split into `datasources/gdd/`, `analysis/species_gdd.py`, `renderers/gdd.py`

---

## Key Decisions

### Why `datasources/` instead of keeping `services/` + top-level modules

Currently the app has an awkward split: `services/inat.py` is the "low-level client" and `inaturalist.py` is the "high-level module." This forces you to understand two locations. Consolidating into `datasources/inaturalist/` groups everything about a data source together — client, parsing, aggregation, and docs.

### Why README.md per data source

Each data source has its own API quirks, rate limits, authentication, and pagination strategies. A README.md in each directory gives AI agents a focused reference without loading the entire project context. When adding a new data source (GBIF, Recreation.gov, OpenRouteService), you just copy the pattern.

### Why renderers stay flat (not per-directory)

The renderers are all ~80-180 lines and share a simple pattern (dict → HTML string). They don't warrant subdirectories. If any renderer grows beyond ~250 lines, it can be promoted to a directory then.

### Why `analysis/` exists (cross-datasource logic)

Several pieces of logic don't belong in any single datasource or renderer:

| Logic | Inputs | Current location |
|---|---|---|
| Attach weather to observation markers | iNat observations × historical weather | `build.py:498` |
| Merge sunshine + weather into 16-day view | sunshine daily × weather forecast | `build.py:288` |
| Correlate species emergence with GDD | iNat observations × GDD accumulation | `gdd.py:206` |

Without a dedicated home, this logic leaks into `flows/` (defeating "slim orchestrator"), piles up in `renderers/` (breaking "pure data→HTML"), or creates a new monolith. The `analysis/` package gives cross-datasource joins, correlations, and composite indexes their own layer.

The name "analysis" over "queries" — these aren't read-only lookups, they're computations (statistical profiles, composite indexes, predictions).

### Why `store.py` and structured data tiers

Current state: all data lives in `data/raw/*.json` with a single `fetched_at` timestamp. With 10+ datasources and historical depth, this causes unnecessary refetches (30-year GDD normals recomputed every run), no cache invalidation, and a flat namespace.

Data falls into three temporal categories that need different storage and refresh strategies — see **Data Storage Architecture** below.

---

## Data Storage Architecture

### The problem with flat `data/raw/`

Currently every fetch writes to `data/raw/<source>.json` and every build reads from there. All files are treated identically — no distinction between data that changes hourly (weather forecast) and data that's stable for months (30-year GDD normals). This means:

- **Wasted API calls**: 30 years of GDD history refetched every run
- **No staleness awareness**: Can't tell if a file needs refreshing without re-fetching
- **No temporal queries**: Can't ask "what did the forecast look like yesterday?"
- **Flat namespace**: 20+ files with no organization

### Data tiers by update frequency

| Tier | Examples | TTL | Size trend |
|---|---|---|---|
| **Reference** (static) | DEMs, species range polygons, campground locations, trail networks | 90 days | Large but fetch-once |
| **Historical** (slow-changing) | GDD normals (30-yr), past observations, flower phenology baselines, completed-year weather | 24h for current period; indefinite for past | Grows over time, cacheable for months |
| **Live** (ephemeral) | Weather forecast, today's sunshine, current campground availability, this week's iNat sightings | 1–6 hours | Small, always overwritten |
| **Derived** (computed) | Species GDD profiles, viewing indexes, enriched markers | 0 (recompute from cached inputs) | Output of `analysis/` |

### Proposed data directory

```
data/
├── reference/                       # Static / fetch-once
│   ├── dem/                         # Digital elevation model tiles
│   ├── species_ranges/              # Range polygons
│   └── campgrounds/                 # Campground locations
│
├── historical/                      # Slow-changing, append-only
│   ├── gdd/
│   │   ├── portland_normals_30yr.json
│   │   ├── portland_2025.json       # Full year, immutable
│   │   └── portland_2026.json       # Current year, updated daily
│   ├── observations/
│   │   └── inat_2026_w06-w08.json   # Current window, refreshed
│   └── weather/
│       └── portland_2026-01.json    # Monthly archive chunks
│
├── live/                            # Ephemeral, overwritten each run
│   ├── weather_forecast.json
│   ├── sunshine_15min.json
│   ├── sunshine_16day.json
│   └── inat_current_week.json
│
└── derived/                         # Analysis outputs (recomputed)
    ├── species_gdd_profiles.json
    ├── weekly_viewing_index.json
    └── site/                        # Final HTML output
        └── index.html
```

### Metadata envelope

Every stored file carries a self-describing header so the fetch flow can skip sources that are still fresh:

```json
{
    "meta": {
        "source": "open-meteo-archive",
        "fetched_at": "2026-02-14T21:33:58Z",
        "valid_until": "2026-02-15T06:00:00Z",
        "location": {"lat": 45.5, "lon": -122.6},
        "params": {"years": "1996-2025"}
    },
    "data": { ... }
}
```

The `valid_until` field is key. Default TTLs by tier:

| Tier | Default TTL |
|---|---|
| `reference/` | 90 days |
| `historical/` (completed periods) | Indefinite |
| `historical/` (current period) | 24 hours |
| `live/` | 1–6 hours (source-dependent) |
| `derived/` | 0 — always recompute |

### `store.py` — implementation sketch

~40-60 lines. No database, no Redis. Structured files with expiry metadata:

```python
class DataStore:
    """Manages read/write of cached data files with TTL."""

    def __init__(self, base_dir: Path):
        self.reference = base_dir / "reference"
        self.historical = base_dir / "historical"
        self.live = base_dir / "live"
        self.derived = base_dir / "derived"

    def read(self, path: Path) -> dict | None:
        """Read data file, return None if missing."""

    def write(self, path: Path, data: dict, source: str,
              valid_until: datetime | None = None, **params) -> Path:
        """Write data with metadata envelope."""

    def is_fresh(self, path: Path) -> bool:
        """Check if file exists and hasn't expired."""
```

### How flows use the store

```
1. Flow asks store.is_fresh() for each data file
2. Flow calls datasources/ to fetch only what's stale
3. Flow calls analysis/ to recompute derived outputs
4. Flow calls renderers/ to build HTML
5. Everything goes to derived/site/
```

---

## Documentation Strategy: Multi-Fidelity

### Layer 1: Project Overview (always in context)

**File: `CLAUDE.md`** — Stays lean. Contains:
- One-paragraph project purpose
- `make` commands
- Python style rules
- Verification rules
- Learnings (short, with file:line references)

**File: `src/butterfly_planner/__init__.py`** — Module docstring with architectural overview:
```
Data flows: datasources → store (cache) → analysis (combine) → renderers (present) → site/
Orchestration: flows/ checks freshness, fetches stale data, triggers analysis + render
```

### Layer 2: Directory Overviews (loaded on demand)

Every `__init__.py` gets a docstring explaining:
- What this directory contains
- When you'd look here
- Key public functions/classes

Examples:

```python
# datasources/__init__.py
"""External data source integrations.

Each subdirectory is one data source (iNaturalist, Open-Meteo weather,
Open-Meteo sunshine). Each has:
  - client.py: Low-level HTTP calls
  - Domain modules: Parsing, aggregation, dataclasses
  - README.md: API docs, rate limits, gotchas

To add a new data source, copy an existing directory and adapt.
"""
```

```python
# renderers/__init__.py
"""Pure rendering functions: structured data → HTML strings.

All renderers follow the same pattern:
  - Input: dict or dataclass (from analysis/ or store)
  - Output: str (HTML fragment)
  - No side effects, no I/O, no Prefect decorators

Used by flows/build.py which orchestrates the rendering pipeline.
"""
```

```python
# analysis/__init__.py
"""Cross-datasource joins, correlations, and composite indexes.

Each module combines outputs from 2+ datasources into enriched structures
that renderers can consume directly. This is the domain logic layer —
the interesting part of the application.

Dependency rule: analysis/ imports from datasources/ models only.
It never fetches data or produces HTML.

Modules:
  - species_weather: observations + historical weather → enriched markers
  - species_gdd: observations + GDD accumulation → emergence profiles
  - weekly_forecast: sunshine + weather → unified daily forecast
  - viewing_index: (future) composite 0-100 viewing score
"""
```

### Layer 3: Deep Documentation (per data source)

Each `datasources/<source>/README.md` contains:
- API base URL and authentication
- Rate limits and retry strategy
- Key endpoints used
- Data model mapping (API response → our dataclasses)
- Known gotchas and workarounds
- Example API responses (truncated)

This is the documentation an agent reads when debugging a specific data source or adding a new feature to it.

### Layer 4: Inline Documentation

- Docstrings on public functions (what, not how)
- Comments only where the "why" isn't obvious
- Type annotations as documentation

### Summary: What agents load when

| Task | Loads |
|---|---|
| "What does this project do?" | `CLAUDE.md` (Layer 1) |
| "How is the code organized?" | `__init__.py` docstrings (Layer 2) |
| "Fix a bug in iNat fetching" | `datasources/inaturalist/README.md` (Layer 3) + source files |
| "Add a new data source" | `datasources/__init__.py` (Layer 2) + any existing source as template |
| "Why does this function do X?" | Inline docs (Layer 4) |

---

## Migration Plan

### Phase 1: Create `renderers/` (from build.py)

This is already planned in `PLAN-refactor-build.md` and is the safest starting point — pure functions with no external dependencies.

1. Create `renderers/__init__.py`, `weather_utils.py`, `species_palette.py`
2. Create `renderers/sunshine.py`, `sightings_map.py`, `sightings_table.py`
3. Create `renderers/gdd.py` (from `gdd.py` rendering functions)
4. Slim `flows/build.py` to orchestration-only
5. Update test imports
6. `make ci` after each file

### Phase 2: Create `datasources/inaturalist/`

1. Create directory with `__init__.py`, `README.md`
2. Move `services/inat.py` → `datasources/inaturalist/client.py`
3. Split `inaturalist.py` into `species.py`, `observations.py`, `weekly.py`
4. Update `__init__.py` to re-export public API (backward compat)
5. Update `flows/fetch.py` imports
6. Update test imports
7. `make ci`

### Phase 3: Create `datasources/weather/`

1. Create directory with `__init__.py`, `README.md`
2. Move `services/weather.py` → `datasources/weather/client.py`
3. Extract forecast fetch logic from `flows/fetch.py` → `datasources/weather/forecast.py`
4. Move historical weather logic → `datasources/weather/historical.py`
5. Update imports, `make ci`

### Phase 4: Create `datasources/sunshine/`

1. Create directory with `__init__.py`, `README.md`
2. Split `sunshine.py` into `models.py`, `today.py`, `daily.py`, `ensemble.py`
3. Update `flows/fetch.py` imports
4. Update test imports
5. `make ci`

### Phase 5: Create `datasources/gdd/`

1. Create directory with `__init__.py`, `README.md`
2. Extract `gdd.py` computation → `datasources/gdd/compute.py`
3. Extract `gdd.py` HTTP fetch → `datasources/gdd/client.py`
4. Extract `gdd.py` dataclasses → `datasources/gdd/models.py`
5. Extract `gdd.py` serialization → `datasources/gdd/serialization.py`
6. Update `flows/fetch.py` imports
7. `make ci`

### Phase 6: Create `analysis/` (cross-datasource logic)

Depends on phases 2-5 (datasource models must exist to import from).

1. Create `analysis/__init__.py` with overview docstring
2. Extract `gdd.py:correlate_observations_with_gdd` → `analysis/species_gdd.py`
3. Extract observation-weather join from `build.py` → `analysis/species_weather.py`
4. Extract sunshine+weather merge from `build.py` → `analysis/weekly_forecast.py`
5. Update `flows/build.py` to call `analysis.*`, pass results to `renderers.*`
6. `make ci`

### Phase 7: Create `store.py` and restructure `data/`

1. Implement `DataStore` class (~40-60 lines) with `read()`, `write()`, `is_fresh()`
2. Restructure `data/` into `reference/`, `historical/`, `live/`, `derived/`
3. Add `meta` envelope (including `valid_until`) to all data writes
4. Update `flows/fetch.py` to check `store.is_fresh()` before fetching
5. Update `flows/build.py` to read from store and write to `derived/`
6. Migrate existing `data/raw/*.json` files to new locations
7. `make ci` + `make verify`

### Phase 8: Slim flows and clean up

After phases 1-7, flows should be thin orchestrators only:
- `fetch.py`: check freshness → fetch stale → save via store (~120 lines)
- `build.py`: load → analyze → render → write HTML (~80 lines)

1. Delete `services/` directory
2. Delete top-level `inaturalist.py`, `sunshine.py`, and `gdd.py`
3. Delete `data/raw/` (replaced by tiered storage)
4. Update `CLAUDE.md` with new architecture overview
5. Write `__init__.py` docstrings (Layer 2)
6. Write `datasources/*/README.md` files (Layer 3)
7. Final `make ci` + `make verify`

---

## File Size Targets (post-refactor)

| File | Target lines | Current |
|---|---|---|
| `flows/build.py` | ~80 | 753 |
| `flows/fetch.py` | ~120 | 309 |
| `store.py` | ~60 | (new) |
| `datasources/inaturalist/client.py` | ~120 | (from services/inat.py) |
| `datasources/inaturalist/species.py` | ~150 | (from inaturalist.py) |
| `datasources/inaturalist/observations.py` | ~150 | (from inaturalist.py) |
| `datasources/inaturalist/weekly.py` | ~100 | (from inaturalist.py) |
| `datasources/weather/client.py` | ~60 | (from services/weather.py) |
| `datasources/weather/forecast.py` | ~50 | (from fetch.py) |
| `datasources/weather/historical.py` | ~80 | (from fetch.py) |
| `datasources/sunshine/models.py` | ~60 | (from sunshine.py) |
| `datasources/sunshine/today.py` | ~100 | (from sunshine.py) |
| `datasources/sunshine/daily.py` | ~100 | (from sunshine.py) |
| `datasources/sunshine/ensemble.py` | ~100 | (from sunshine.py) |
| `datasources/gdd/compute.py` | ~80 | (from gdd.py) |
| `datasources/gdd/client.py` | ~80 | (from gdd.py) |
| `datasources/gdd/models.py` | ~60 | (from gdd.py) |
| `datasources/gdd/serialization.py` | ~50 | (from gdd.py) |
| `analysis/species_gdd.py` | ~80 | (from gdd.py) |
| `analysis/species_weather.py` | ~60 | (from build.py) |
| `analysis/weekly_forecast.py` | ~50 | (from build.py) |
| `renderers/sunshine.py` | ~180 | (from build.py) |
| `renderers/sightings_map.py` | ~100 | (from build.py) |
| `renderers/sightings_table.py` | ~100 | (from build.py) |
| `renderers/species_palette.py` | ~80 | (from build.py) |
| `renderers/gdd.py` | ~180 | (from gdd.py) |
| `renderers/weather_utils.py` | ~40 | (from build.py) |

**Total source lines:** ~3,400 (up from ~2,650 due to GDD module; reorganizing, not rewriting)

---

## Risks and Mitigations

| Risk | Mitigation |
|---|---|
| Breaking imports across the codebase | Re-export public API from `__init__.py` during transition; `make ci` after each step |
| Test churn | Tests mostly mock at the function level; updating import paths is mechanical |
| Circular imports | Dependency direction is strict: `datasources` → nothing; `analysis` → `datasources` models; `renderers` → `weather_utils`; `flows` → all via `store` |
| Losing track of what moved where | Each phase is one commit with a clear message |
| Data migration (`data/raw/` → tiered) | Phase 7 is explicitly separate; old flat files work until then |
| Over-engineering `store.py` | Start with ~40 lines (read/write/is_fresh). No database until file count exceeds ~50 or concurrent access is needed |

---

## What This Enables (Future)

- **New data sources** (flower phenology, US Pests, elevation DEMs, GBIF, Recreation.gov, OpenRouteService) just add a new `datasources/<name>/` directory
- **Composite indexes** (viewing score, emergence prediction) go in `analysis/` — the domain logic has a proper home
- **Smart caching** — only fetch what's stale; historical data fetched once and kept
- **New renderers** (isochrone map, campground list, GDD overlay) just add a new `renderers/<name>.py`
- **AI agents** can load exactly the context they need: directory README for debugging, `__init__.py` for navigation, `CLAUDE.md` for project rules
- **Parallel development** — different agents/people can work on different data sources without merge conflicts in a 750-line file
- **Future migration path** — when flat JSON files outgrow the filesystem (100+ MB, concurrent writes, complex temporal queries), the `DataStore` interface can be backed by DuckDB or GeoParquet without changing any callers

---

## Open Questions and Areas for Further Research

The architecture above is well-grounded for the current codebase and the next 3-5 datasources. However, several areas would benefit from validation before or during implementation:

**`store.py` TTL granularity.** The proposed TTLs (90 days for reference, 24h for current historical, 1-6h for live) are reasonable defaults, but we haven't profiled actual API costs or latency to know if they're optimal. For example, Open-Meteo archive responses for 30-year GDD normals are ~60KB — cheap enough to refetch weekly, or worth caching for months? The right answer depends on how often we run the pipeline and whether we deploy on a schedule vs. on-demand. We should instrument the first implementation with timing/size logging and tune TTLs from real data rather than guessing.

**`analysis/` module boundaries.** The three initial modules (species_weather, species_gdd, weekly_forecast) are clearly extractable from existing code. But as we add composite indexes that combine 3+ datasources (e.g., a viewing score that uses GDD + weather + flower bloom + elevation), the question becomes whether each index gets its own module or whether there's a shared scoring framework. We should wait until we have at least two composite indexes before designing an abstraction — build concrete things first, then factor out patterns.

**Data format for reference/raster data.** The plan assumes JSON for everything, which works for point data and time series. But DEMs and species range polygons are inherently spatial — GeoTIFF, GeoJSON, or GeoParquet may be more appropriate. The `DataStore` interface should be format-agnostic (read/write paths, not JSON specifically), but we haven't validated that the metadata envelope pattern works for binary raster formats. This needs a spike when we add the first raster datasource (likely elevation DEMs).

**Prefect task granularity after refactor.** Currently each `@task` does fetch+save as one unit. With `store.is_fresh()` checks, the flow might skip individual fetches. We should verify that Prefect handles conditional task skipping cleanly (via `return` or Prefect's native skip/caching) rather than building our own orchestration on top of Prefect's.
