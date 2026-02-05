---
name: fetch-inat
description: Fetch butterfly occurrence data from iNaturalist for NW Oregon / SW Washington
---

# Fetch iNaturalist Butterfly Occurrence Data

Fetch butterfly sightings from the iNaturalist API for the NW Oregon / SW Washington
area. Returns species counts and individual observations for a given month or week
of the year, across ALL historical years.

## Quick Usage

```bash
# Test the module imports
python -c "from butterfly_planner.inaturalist import get_current_week_species; print('ok')"

# Fetch species for current week (interactive / live API)
python -c "
from butterfly_planner.inaturalist import get_current_week_species, summarize_species
summary = get_current_week_species()
print(f'Found {summary.total_species} species, {summary.total_observations} observations')
for s in summary.top_species[:10]:
    print(f'  {s.display_name}: {s.observation_count} obs')
"

# Fetch species for a specific ISO week
python -c "
from butterfly_planner.inaturalist import get_species_for_week
summary = get_species_for_week(25)  # ~mid-June
for s in summary.top_species[:10]:
    print(f'  {s.display_name}: {s.observation_count} obs')
"

# Weekly activity histogram (all year, all years)
python -c "
from butterfly_planner.inaturalist import fetch_weekly_histogram, peak_weeks
histogram = fetch_weekly_histogram()
for w in peak_weeks(histogram, top_n=10):
    print(f'  Week {w.week}: {w.count} observations')
"
```

## API Details

- **Endpoint**: `https://api.inaturalist.org/v1/observations/species_counts`
- **Taxon**: Papilionoidea (butterflies) — taxon_id 47224
- **Area**: NW Oregon / SW Washington bounding box (44.5°N–46.5°N, 124.2°W–121.5°W)
- **Rate limit**: ~1 request/second, 10k requests/day
- **Quality filter**: Research grade by default

## Key Files

| File | Purpose |
|------|---------|
| `src/butterfly_planner/inaturalist.py` | Main module: dataclasses, fetch functions, analysis |
| `src/butterfly_planner/services/inat.py` | Low-level API client: rate limiting, pagination |
| `tests/test_inaturalist.py` | Comprehensive tests with mocked API responses |

## Module API

### Data Models

- `SpeciesRecord` — species with observation count, photo, URL
- `ButterflyObservation` — individual sighting with location, date, photo
- `WeeklyActivity` — observation count per week of year
- `OccurrenceSummary` — top-level result combining species + observations

### Fetch Functions

| Function | API Calls | Description |
|----------|-----------|-------------|
| `fetch_species_counts(month, bbox)` | 1 | Species + counts for month(s), all years |
| `fetch_observations_for_month(month, bbox)` | 1–3 | Individual observations, paginated |
| `fetch_weekly_histogram(bbox)` | 1 | Observation counts by week of year |
| `get_current_week_species(bbox)` | 2–3 | Convenience: species + obs for current month |
| `get_species_for_week(week, bbox)` | 2–3 | Convenience: species + obs for specific ISO week |

### Analysis Functions

| Function | Description |
|----------|-------------|
| `summarize_species(species)` | Top species, totals, rank breakdown |
| `peak_weeks(histogram, top_n)` | Top N weeks by observation count |

## Bounding Box

Default covers NW Oregon / SW Washington:
```
NW_OREGON_SW_WASHINGTON = {
    "swlat": 44.5,   # South (roughly Corvallis, OR)
    "swlng": -124.2,  # West (Oregon coast)
    "nelat": 46.5,    # North (roughly Centralia, WA)
    "nelng": -121.5,  # East (Cascade foothills)
}
```

Override with any dict having `swlat/swlng/nelat/nelng` keys.

## Cost / Rate Limit Awareness

- The service client enforces ~1.1s between requests
- `species_counts` is the most efficient (1 call for all species)
- `observations` requires pagination (up to 200/page, default max 3 pages)
- `histogram` is 1 call for the full year
- A full `get_current_week_species()` call uses 3–4 API requests total

## Testing

```bash
# Run only iNaturalist tests (no API calls — fully mocked)
pytest tests/test_inaturalist.py -v

# Run full CI
make ci
```
