# Plan: Refactor App into Module Directories

## Problem

The app has outgrown its flat-file structure. Two modules carry most of the weight:

| Module | Lines | Concern count |
|---|---|---|
| `flows/build.py` | 753 | 7+ (rendering, templates, palettes, utils, orchestration) |
| `flows/fetch.py` | 309 | 4 (weather, sunshine, iNat, historical weather) |
| `inaturalist.py` | 474 | 3 (species, observations, weekly aggregation) |
| `sunshine.py` | 368 | 3 (15-min, daily, ensemble) |

Beyond code bloat, **documentation is also flat** — CLAUDE.md carries project instructions, learnings, and style rules all in one place. AI agents either load everything or nothing. We need tiered documentation so agents can fetch the right level of detail.

---

## Proposed Structure

```
src/butterfly_planner/
├── __init__.py                      # Package version, top-level exports
├── cli.py                           # CLI entry point (unchanged)
├── config.py                        # Settings (unchanged)
├── schemas.py                       # Pydantic models (unchanged)
│
├── flows/                           # Prefect orchestration only
│   ├── __init__.py                  # Overview: what flows exist, when to run them
│   ├── fetch.py                     # Slim: imports tasks, defines fetch_all() flow
│   └── build.py                     # Slim: imports renderers, defines build_all() flow
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
│   └── sunshine/
│       ├── __init__.py              # Public API: fetch_today, fetch_16day, fetch_ensemble
│       ├── README.md                # Open-Meteo sunshine endpoints, ensemble docs
│       ├── models.py                # SunshineSlot, DailySunshine, EnsembleSunshine
│       ├── today.py                 # fetch_today_15min_sunshine
│       ├── daily.py                 # fetch_16day_sunshine
│       └── ensemble.py              # fetch_ensemble_sunshine
│
├── renderers/                       # NEW — pure functions: data → HTML
│   ├── __init__.py                  # Overview: rendering pipeline, shared conventions
│   ├── sunshine.py                  # Today timeline + 16-day table renderers
│   ├── sightings_map.py             # Leaflet map generation
│   ├── sightings_table.py           # Species sightings HTML table
│   ├── species_palette.py           # SpeciesStyle, colors, initials
│   └── weather_utils.py             # c_to_f, wmo_code_to_conditions, WMO_CONDITIONS
│
├── templates/                       # Jinja2 templates (already exists, mostly unchanged)
│   ├── base.html.j2
│   ├── sunshine_today.html.j2
│   ├── sunshine_16day.html.j2
│   ├── sightings_table.html.j2
│   ├── sightings_map.html.j2
│   └── sightings_map_script.html.j2
│
└── core.py                          # Business logic placeholders (unchanged for now)
```

### What gets deleted

- `services/` directory — absorbed into `datasources/`
- `inaturalist.py` (top-level) — split into `datasources/inaturalist/`
- `sunshine.py` (top-level) — split into `datasources/sunshine/`

---

## Key Decisions

### Why `datasources/` instead of keeping `services/` + top-level modules

Currently the app has an awkward split: `services/inat.py` is the "low-level client" and `inaturalist.py` is the "high-level module." This forces you to understand two locations. Consolidating into `datasources/inaturalist/` groups everything about a data source together — client, parsing, aggregation, and docs.

### Why README.md per data source

Each data source has its own API quirks, rate limits, authentication, and pagination strategies. A README.md in each directory gives AI agents a focused reference without loading the entire project context. When adding a new data source (GBIF, Recreation.gov, OpenRouteService), you just copy the pattern.

### Why renderers stay flat (not per-directory)

The renderers are all ~80-180 lines and share a simple pattern (dict → HTML string). They don't warrant subdirectories. If any renderer grows beyond ~250 lines, it can be promoted to a directory then.

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
Data flows: datasources → flows/fetch → data/raw/*.json → flows/build → site/
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
  - Input: dict (loaded from data/raw/*.json)
  - Output: str (HTML fragment)
  - No side effects, no I/O, no Prefect decorators

Used by flows/build.py which orchestrates the rendering pipeline.
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
3. Slim `flows/build.py` to orchestration-only
4. Update test imports
5. `make ci` after each file

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

### Phase 5: Slim `flows/fetch.py`

After phases 2-4, `fetch.py` should only contain:
- Prefect `@task` wrappers that call into `datasources/`
- `save_*()` functions (JSON I/O)
- `fetch_all()` flow

This should be ~120 lines, down from 309.

### Phase 6: Clean up and documentation

1. Delete `services/` directory
2. Delete top-level `inaturalist.py` and `sunshine.py`
3. Update `CLAUDE.md` with new architecture overview
4. Write `__init__.py` docstrings (Layer 2)
5. Write `datasources/*/README.md` files (Layer 3)
6. Update `PLAN-refactor-build.md` to mark as done or remove
7. Final `make ci` + `make verify`

---

## File Size Targets (post-refactor)

| File | Target lines | Current |
|---|---|---|
| `flows/build.py` | ~80 | 753 |
| `flows/fetch.py` | ~120 | 309 |
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
| `renderers/sunshine.py` | ~180 | (from build.py) |
| `renderers/sightings_map.py` | ~100 | (from build.py) |
| `renderers/sightings_table.py` | ~100 | (from build.py) |
| `renderers/species_palette.py` | ~80 | (from build.py) |
| `renderers/weather_utils.py` | ~40 | (from build.py) |

**Total source lines:** ~2,650 (roughly the same — we're reorganizing, not rewriting)

---

## Risks and Mitigations

| Risk | Mitigation |
|---|---|
| Breaking imports across the codebase | Re-export public API from `__init__.py` during transition; `make ci` after each step |
| Test churn | Tests mostly mock at the function level; updating import paths is mechanical |
| Circular imports | Dependency direction is strict: `datasources` → nothing; `renderers` → `weather_utils`; `flows` → `datasources` + `renderers` |
| Losing track of what moved where | Each phase is one commit with a clear message |

---

## What This Enables (Future)

- **New data sources** (GBIF, Recreation.gov, OpenRouteService) just add a new `datasources/<name>/` directory
- **New renderers** (isochrone map, campground list) just add a new `renderers/<name>.py`
- **AI agents** can load exactly the context they need: directory README for debugging, `__init__.py` for navigation, `CLAUDE.md` for project rules
- **Parallel development** — different agents/people can work on different data sources without merge conflicts in a 750-line file
