# Plan: Break apart `flows/build.py`

## Problem

`flows/build.py` has grown to ~1,045 lines and mixes several concerns:
- HTML template (250 lines of raw CSS/HTML)
- Weather/sunshine rendering logic
- iNaturalist/butterfly rendering logic (map + table)
- Species symbology (palette, initials, colors)
- Prefect tasks/flow orchestration
- Data loading helpers
- Utility functions (temperature conversion, WMO codes)

## Proposed structure

```
src/butterfly_planner/
├── flows/
│   └── build.py              # Prefect flow + tasks only (~80 lines)
│                              #   load_weather(), load_sunshine(), load_inaturalist()
│                              #   build_html() task, write_site() task, build_all() flow
├── templates/
│   ├── __init__.py
│   ├── base.py               # HTML_TEMPLATE string, MONTH_NAMES constant
│   └── styles.py             # CSS (if we want to separate further, optional)
├── renderers/
│   ├── __init__.py
│   ├── sunshine.py            # build_sunshine_today_html()
│   │                          #   build_sunshine_16day_html()
│   │                          #   _build_hourly_bar(), _group_15min_by_date()
│   │                          #   _sunshine_color_class()
│   ├── sightings_map.py       # build_butterfly_map_html()
│   │                          #   _week_label(), _year_range()
│   ├── sightings_table.py     # build_butterfly_sightings_html()
│   │                          #   _inat_obs_url()
│   └── species_palette.py     # _SPECIES_COLORS, SpeciesStyle dataclass
│                              #   _build_species_palette(), _species_initials()
└── weather_utils.py           # c_to_f(), wmo_code_to_conditions()
```

## Module responsibilities

### `flows/build.py` (~80 lines)
Keep only Prefect orchestration: `@task` and `@flow` decorated functions.
Imports rendering functions from `renderers/`. Stays the entry point.

### `templates/base.py` (~260 lines)
The `HTML_TEMPLATE` string and `MONTH_NAMES` list.
No logic, just the skeleton. This is the largest single piece but it's
a static string literal — moving it out dramatically unclutters `build.py`.

### `renderers/sunshine.py` (~180 lines)
All sunshine visualization: today's timeline, 16-day table, hourly bars.
Depends on `weather_utils` for `c_to_f()` and `wmo_code_to_conditions()`.
Depends on `templates.base` for `MONTH_NAMES`.

### `renderers/sightings_map.py` (~100 lines)
Leaflet map generation. Depends on `species_palette` for colors.

### `renderers/sightings_table.py` (~100 lines)
Species sightings HTML table. Depends on `species_palette` for colors.

### `renderers/species_palette.py` (~80 lines)
`SpeciesStyle` dataclass, color palette constant, `_build_species_palette()`,
`_species_initials()`. Shared by both map and table renderers.

### `weather_utils.py` (~30 lines)
Pure functions: `c_to_f()`, `wmo_code_to_conditions()`. No dependencies.

## Migration strategy

1. **Create modules bottom-up** (no dependencies first):
   - `weather_utils.py`
   - `renderers/species_palette.py`
   - `templates/base.py`

2. **Move renderers** (depend on above):
   - `renderers/sunshine.py`
   - `renderers/sightings_map.py`
   - `renderers/sightings_table.py`

3. **Slim down `flows/build.py`**: Replace moved code with imports.

4. **Update tests**: Adjust import paths. Test modules can mirror the
   new structure or stay as `test_flows_build.py` importing from new locations.

5. **Verify**: `make ci` must pass after each step.

## Principles

- Each file should be < 200 lines where practical
- No circular imports — renderers depend on palette/utils, not on each other
- Prefect concerns (`@task`, `@flow`) stay in `flows/build.py`
- Rendering functions are pure (dict in → str out), easy to test independently
- The HTML template is the one exception to the line limit — it's a single
  string literal and splitting it further would hurt readability
