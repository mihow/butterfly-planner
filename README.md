# Butterfly Planner

A combination of site-suitability analysis with **trip**-suitability analysis. Depending on the availability and interest of the participants on a given day. One part exploratory dashboard, two parts executive decision-making tool.

GIS layers for butterfly abundance and species diversity forecasting. The site covers two areas: Portland, OR (NW Oregon and SW Washington) and Bisbee, AZ (Bisbee, Leslie Canyon and SE Arizona).

Uses butterfly observation data, environmental data, and flower phenology to predict optimal butterfly viewing locations by week of the year. Includes isochrone mapping for driving time analysis.

## Setup

```bash
# Create virtual environment with Python 3.12
uv venv --python 3.12
source .venv/bin/activate

# Install with dev dependencies
make install-dev
```

## CLI Usage

```bash
butterfly-planner info                          # Show app info
butterfly-planner run --name test               # Run example process
butterfly-planner refresh                       # Fetch data and build every location's page
butterfly-planner refresh --location bisbee     # Fetch and build one location
butterfly-planner --help                        # Show all commands
```

## Locations

Each location is published as its own static page. The default location (Portland) is the site root, `index.html`. Every other location has its own folder, such as `bisbee/index.html`. The pages link to each other with plain relative links.

A location defines its observation search box, its weather point, its timezone, its map view and any points of interest to mark on the map. Each location's cached data lives in its own folder, for example `data/live/bisbee/`, and its daily JSON is written to `data/derived/daily/<slug>/today.json`.

To add a location:

1. Add a `Location` entry in `src/butterfly_planner/reference/geography.py` and add it to `LOCATIONS`. Give it a unique `slug` and `site_subdir`.
2. Use an IANA timezone name, such as `America/Phoenix`. Weather, sunshine and the "this week" window all use the location's local time.
3. Make sure the bounding box contains the weather point, the map center and every point of interest. The tests in `tests/test_geography.py` check this for every registered location.
4. Run `butterfly-planner refresh --location <slug>` to fetch and build the new page.

The fetch and build flows, the page links and the CLI choices all read the registry, so no other code changes are needed.

## Development

```bash
# Run tests
make test

# Run full CI (lint, format, typecheck, tests)
make ci

# Run verification suite
make verify

# See all commands
make help
```

## Project Structure

```
src/butterfly_planner/
├── cli.py          # Command-line interface
├── config.py       # Settings (env vars, paths)
├── core.py         # Business logic
└── models.py       # Data models

tests/              # Test suite
```
