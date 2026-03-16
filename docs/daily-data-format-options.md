# Structured Daily Data Format — Options

**Date**: 2026-03-16
**Status**: Option A implemented; others documented for future consideration

## Problem

The build pipeline transforms raw API data directly into HTML. There is no
intermediate structured format that other consumers (iPhone widget, API,
notifications) can use. We need a JSON representation of each day's data that
is independent of both the upstream API shapes and the downstream HTML rendering.

## Options

### Option A: Daily Data Snapshot in Build Flow (Implemented)

**Where**: New module `src/butterfly_planner/renderers/daily_data.py`
**When**: Runs as a task in `flows/build.py`, alongside HTML generation
**Output**: `data/derived/daily/<date>.json` + `data/derived/daily/today.json` (symlink/copy)

The build flow already loads and transforms all the data. This option adds a
pure function that extracts a structured `DailyData` dict from the same inputs
the HTML renderers use, then writes it to the derived/ tier.

**Schema** (see `daily_data.py` for the canonical definition):

```json
{
  "version": "1.0",
  "date": "2026-03-16",
  "location": {"name": "Portland, OR", "lat": 45.5, "lon": -122.6},
  "generated_at": "2026-03-16T10:30:00-07:00",
  "sunshine": {
    "today_hours": 4.2,
    "daylight_hours": 11.8,
    "sunshine_pct": 35.6,
    "is_good_day": true,
    "sunrise": "07:15",
    "sunset": "19:05",
    "hourly": [{"hour": 7, "sun_minutes": 8}, ...]
  },
  "weather": {
    "high_c": 14.2,
    "low_c": 6.1,
    "precip_mm": 0.0,
    "weather_code": 1,
    "conditions": "Mostly Clear"
  },
  "gdd": {
    "accumulated": 142.5,
    "daily": 8.3,
    "base_temp_f": 50,
    "year_comparison": "+28 GDD ahead of last year"
  },
  "butterflies": {
    "observation_window": {"start": "2026-03-02", "end": "2026-03-23"},
    "species_count": 12,
    "top_species": [
      {"common_name": "Painted Lady", "scientific_name": "Vanessa cardui", "observation_count": 45}
    ],
    "recent_observations_count": 87
  },
  "forecast": [
    {"date": "2026-03-17", "sunshine_hours": 5.1, "high_c": 15.0, "low_c": 7.2, ...},
    ...
  ]
}
```

**Pros**:
- Minimal new code — reuses existing data loading
- Naturally fits the existing Prefect task graph
- File-based output works for static hosting (widget can fetch `today.json`)
- Schema versioned for forward compatibility

**Cons**:
- Coupled to the build flow schedule
- File-based, so no dynamic queries

---

### Option B: Standalone CLI Command

**Where**: New CLI command `butterfly-planner daily-json [--date DATE] [--output PATH]`
**When**: Run on-demand or via cron, independent of the build flow

Would add a new entry point that loads data from the store and produces a
daily JSON file. Could target a specific date or default to today.

```bash
butterfly-planner daily-json                    # today → stdout
butterfly-planner daily-json --date 2026-03-15  # specific date
butterfly-planner daily-json --output daily.json
```

**Pros**:
- Independent of the build flow — can run for historical dates
- Good for scripting and piping to other tools
- Can generate data for date ranges (e.g., backfill a week)

**Cons**:
- Duplicates data loading logic from build.py (or needs shared extraction)
- Requires store to have data for the target date (no on-demand fetching)
- More code to maintain

**Implementation notes**: Would share the extraction function from Option A
but wrap it in a CLI entry point using the existing Click CLI infrastructure.

---

### Option C: REST API Endpoint

**Where**: New `src/butterfly_planner/services/api.py` using FastAPI/Litestar
**When**: Always-on server, responds to HTTP requests

```
GET /api/v1/daily          → today's data
GET /api/v1/daily/2026-03-15  → specific date
GET /api/v1/forecast       → 16-day array
```

**Pros**:
- Dynamic queries with filtering (species, date range, location)
- Natural fit for mobile apps and widgets
- Can compute data on-the-fly from the store
- Supports authentication, rate limiting, CORS

**Cons**:
- Requires running a server (deployment complexity)
- Overkill for the current static-site architecture
- Need to manage uptime, scaling, caching

**Implementation notes**: FastAPI is a natural choice. The daily data
extraction function from Option A becomes the core of each endpoint handler.
The store provides the data layer. Could be deployed as a single Fly.io or
Railway container alongside the static site.

---

### Option D: Event-Driven with Webhooks

**Where**: Extension to the fetch flow
**When**: After each data fetch completes

Each successful fetch would emit a webhook/notification with the updated
daily data payload. Consumers register URLs to receive updates.

```python
# In flows/fetch.py, after saving data:
daily = build_daily_data(weather, sunshine, inat, gdd)
for url in settings.webhook_urls:
    httpx.post(url, json=daily)
```

**Pros**:
- Push-based — consumers get updates immediately
- Good for real-time widgets and notifications
- No polling needed

**Cons**:
- Requires webhook infrastructure (retries, delivery guarantees)
- Consumers must run HTTP servers to receive
- Complex error handling (what if a webhook is down?)
- Premature for current scale

---

## Recommendation

**Start with Option A** (implemented in this PR). It provides the structured
data format with minimal complexity. The extraction function is pure and
reusable, so Options B and C can build on it later:

1. **Now**: Option A — daily JSON files in derived/
2. **Soon**: Option B — CLI command for ad-hoc generation
3. **Later**: Option C — REST API when we need dynamic queries
4. **Eventually**: Option D — Webhooks for real-time consumers

The `build_daily_data()` function is the shared foundation for all options.
