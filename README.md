# Butterfly Planner

GIS layers for butterfly abundance and species diversity forecasting in Oregon and Washington.

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
butterfly-planner info              # Show app info
butterfly-planner run --name test   # Run example process
butterfly-planner --help            # Show all commands
```

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

## License

MIT
