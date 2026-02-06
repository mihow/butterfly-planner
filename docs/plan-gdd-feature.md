# Growing Degree Days (GDD) Feature Plan

## Overview

Integrate Growing Degree Days into the butterfly planner to correlate butterfly
emergence and activity with accumulated heat units. GDD is the standard
phenological metric for predicting insect development — it answers "how much
warmth has accumulated this season?" rather than "what's the calendar date?"

Two butterflies spotted on March 15 in a warm year and April 10 in a cool year
may both correspond to ~350 accumulated GDD. By tracking GDD we can predict
activity windows independent of calendar quirks.

---

## What Is GDD?

```
GDD_daily = max(0, (T_max + T_min) / 2 - T_base)
```

- **T_base** = 50°F (10°C) — standard for butterflies and most insects
- **Upper cutoff** = 86°F (30°C) — cap T_max to avoid overestimating
- **Accumulation** = sum of daily GDD from Jan 1 (or biofix date) through target date

Example: a day with high 72°F and low 48°F → `max(0, (72+48)/2 - 50)` = **10 GDD**.

---

## Data Sources (Ranked)

### Primary: Open-Meteo Historical Weather API

Already used in the project for forecasts. The archive endpoint provides daily
min/max temps back to **1940** with no API key.

```
GET https://archive-api.open-meteo.com/v1/archive
  ?latitude=45.5&longitude=-122.6
  &start_date=2025-01-01&end_date=2025-12-31
  &daily=temperature_2m_max,temperature_2m_min
  &temperature_unit=fahrenheit
```

- Free, no auth, JSON response
- ~10km grid resolution
- Compute GDD ourselves (simple formula above)
- Can fetch multiple years in one call (date range up to a year)

### Secondary: USA National Phenology Network (USA-NPN)

Pre-computed Accumulated GDD grids (base 50°F) going back to **1981**. Available
as WMS map tiles — useful for the Leaflet map overlay.

```
# WMS tile layer for accumulated GDD
http://geoserver.usanpn.org/geoserver/gdd/wms
  ?service=WMS&request=GetMap
  &layers=gdd:agdd_50f
  &time=2025-06-15
  &bbox=-124.2,44.5,-121.5,46.5
  &width=512&height=512
  &format=image/png
```

- ~4km resolution gridded raster
- No API key (just self-identify via HTTP header)
- Good for map visualization; not ideal for point queries

### Stretch: PRISM 800m Grids

Oregon State's PRISM dataset offers **800m resolution** daily temperature grids
(free since March 2025). Higher spatial fidelity for mountainous terrain where
GDD varies significantly by elevation. Worth considering if we need per-location
accuracy beyond what Open-Meteo provides.

---

## Feature Design

### 1. "Today's GDD" Card

A new section on the site showing current-year GDD accumulation for the
configured location.

**Display:**
```
Growing Degree Days (base 50°F)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Today: 847 GDD    (Feb 6, 2026)
Normal: 795 GDD   (30-yr avg for this date)
Last year: 812 GDD

▎ early ──── on track ──── late ▎
              ▲
```

**Data needed:**
- Daily min/max temps from Jan 1 through today (Open-Meteo archive API)
- Same data for previous years (for "normal" and "last year" comparisons)

**Implementation:**
- New function `compute_accumulated_gdd(daily_temps, base=50, upper=86) -> list[float]`
- New fetch task `fetch_historical_temps(lat, lon, years)` in `flows/fetch.py`
- Save to `data/raw/gdd.json`
- New template section `gdd_today.html.j2`

### 2. GDD Timeline / Year Curve

A timeline visualization showing GDD accumulation across the full year, with
multiple years overlaid for comparison.

**Display concept:**
```
Accumulated GDD
1600 ┤
     │                                          ╱── 2024
1200 ┤                                    ╱───╱
     │                              ╱───╱╱── 2025 (actual)
 800 ┤                        ╱───╱╱
     │                  ╱───╱╱........... 2026 (forecast →)
 400 ┤            ╱───╱╱
     │      ╱───╱╱── 30-yr normal (shaded band ±1σ)
   0 ┤─────╱
     └──┬──┬──┬──┬──┬──┬──┬──┬──┬──┬──┬──┬──
       Jan Feb Mar Apr May Jun Jul Aug Sep Oct Nov Dec
                         ▲ today
```

**Layers:**
- **30-year normal** (1996-2025): shaded band showing mean ± 1 standard deviation
- **Current year** (bold line): actual through today, forecast extension using
  16-day Open-Meteo data
- **Previous 1-2 years** (thin lines): for quick comparison
- **Butterfly activity markers**: horizontal bands or icons showing when key
  species historically appear, placed at their typical GDD thresholds

**Implementation options:**
- **Option A (simple):** SVG generated server-side via Jinja2 template, inline
  in the HTML. No JS dependency. Consistent with the project's static-site
  approach.
- **Option B (interactive):** Lightweight JS charting (Chart.js or inline
  `<canvas>`). Allows hover tooltips showing "Week 23: 650 GDD — expect Painted
  Lady emergence." More complex but better UX.

**Recommendation:** Start with Option A (SVG). The curve is essentially a
monotonically increasing line — straightforward to render as an SVG `<polyline>`.
Can upgrade to interactive later if needed.

### 3. GDD-Indexed Species Table

Enhance the existing butterfly species table with a GDD column showing the
typical GDD range when each species is active.

| Species | GDD Range | Observations | Peak |
|---------|-----------|--------------|------|
| Painted Lady | 300–900 | ████████ 542 | 550 |
| Western Tiger Swallowtail | 400–1100 | ██████ 387 | 700 |
| Monarch | 600–1400 | ████ 201 | 900 |

**Data source:** Cross-reference each iNaturalist observation date with the
GDD accumulated through that date (from historical temps). Build a per-species
GDD distribution from observations.

**Implementation:**
- For each observation, look up accumulated GDD for (lat, lon, date)
- Aggregate per species: min/p10/median/p90/max GDD
- Display as a range bar in the species table

### 4. GDD Map Layer (Optional / Phase 2)

Overlay the Leaflet map with a USA-NPN WMS tile layer showing current
accumulated GDD as a color ramp. Butterfly observation markers sit on top.

```javascript
L.tileLayer.wms("http://geoserver.usanpn.org/geoserver/gdd/wms", {
    layers: "gdd:agdd_50f",
    format: "image/png",
    transparent: true,
    time: "2026-02-06",
    opacity: 0.5
}).addTo(map);
```

This gives immediate spatial context — you can see that higher-elevation areas
have lower GDD and expect later butterfly emergence.

---

## Historical GDD for Any Day

**Yes, we can get historical GDD for any given day of previous years.**

**Approach:**
1. Fetch daily min/max temps for Jan 1 through target date for the desired year
2. Compute daily GDD using the modified method
3. Sum to get accumulated GDD

**Open-Meteo supports this back to 1940.** A single API call per year:

```
GET https://archive-api.open-meteo.com/v1/archive
  ?latitude=45.5&longitude=-122.6
  &start_date=2020-01-01&end_date=2020-12-31
  &daily=temperature_2m_max,temperature_2m_min
  &temperature_unit=fahrenheit
```

For the 30-year normal, we'd fetch 30 years of data. This is a one-time
computation that can be cached and only updated annually.

---

## Implementation Phases

### Phase 1: Core GDD Computation + Today's Card

**New files:**
- `src/butterfly_planner/gdd.py` — GDD computation logic
- `src/butterfly_planner/templates/gdd_today.html.j2` — today's GDD display

**Modified files:**
- `src/butterfly_planner/flows/fetch.py` — add `fetch_gdd_temps()` task
- `src/butterfly_planner/flows/build.py` — add GDD section to HTML output
- `src/butterfly_planner/config.py` — add `gdd_base_temp` setting (default 50°F)

**Steps:**
1. Write `compute_daily_gdd()` and `compute_accumulated_gdd()` functions
2. Add fetch task for Open-Meteo archive API (current year + previous year)
3. Save to `data/raw/gdd.json`
4. Build "Today's GDD" card in HTML output
5. Tests for GDD computation (pure math, easy to test)

**Estimated scope:** ~200-300 lines of new code + tests.

### Phase 2: Timeline Visualization

**New files:**
- `src/butterfly_planner/templates/gdd_timeline.html.j2` — SVG chart

**Modified files:**
- `src/butterfly_planner/flows/fetch.py` — fetch 30 years of historical temps
  (cached, not daily)
- `src/butterfly_planner/flows/build.py` — render timeline SVG

**Steps:**
1. Fetch and cache 30-year historical temperature data
2. Compute GDD curves for each year + statistics (mean, stddev)
3. Generate SVG polylines for normal band + current year + previous years
4. Add "today" marker and optional forecast extension
5. Style to match existing site aesthetic

**Caching strategy:** Store `data/cache/gdd_historical.json` with all 30 years
of daily GDD. Regenerate annually (or on first run after Jan 1). Daily runs only
need to append the current day.

### Phase 3: Species GDD Correlation

**Modified files:**
- `src/butterfly_planner/inaturalist.py` — enrich observations with GDD
- `src/butterfly_planner/flows/build.py` — add GDD column to species table

**Steps:**
1. For each observation date+location, look up accumulated GDD
2. Build per-species GDD distribution (min, p10, median, p90, max)
3. Add GDD range bar to species table
4. Optionally mark species emergence thresholds on the timeline chart

**Challenge:** Observations span multiple locations and years. We need GDD for
each observation's specific location and date. Options:
- **Simple:** Use the configured location's GDD for all observations (since
  they're already filtered to a bounding box, this is a reasonable
  approximation)
- **Precise:** Fetch GDD per unique (lat, lon, year) — expensive, many API
  calls. Only worth it if observations span wide elevation ranges.

**Recommendation:** Start simple (single location). The bounding box is ~200km
across, so GDD variation within it is modest except for mountain observations.

### Phase 4: Map Overlay (Optional)

**Modified files:**
- `src/butterfly_planner/templates/sightings_map_script.html.j2` — add WMS layer

**Steps:**
1. Add USA-NPN WMS tile layer to Leaflet map
2. Add layer toggle control
3. Add legend for GDD color ramp

**Scope:** ~20 lines of JavaScript in the template. Low effort, high visual
impact.

---

## Data Storage

```
data/
├── raw/
│   ├── weather.json          (existing)
│   ├── sunshine.json         (existing)
│   ├── inaturalist.json      (existing)
│   └── gdd.json              (new: current + last year daily temps & GDD)
└── cache/
    └── gdd_historical.json   (new: 30-year daily temps, regenerated annually)
```

**`gdd.json` schema:**
```json
{
  "location": {"lat": 45.5, "lon": -122.6},
  "base_temp_f": 50,
  "upper_cutoff_f": 86,
  "current_year": {
    "year": 2026,
    "daily": [
      {"date": "2026-01-01", "tmax": 45.2, "tmin": 33.1, "gdd": 0.0, "accumulated": 0.0},
      {"date": "2026-01-02", "tmax": 52.1, "tmin": 38.4, "gdd": 0.0, "accumulated": 0.0}
    ],
    "total_gdd": 847.5
  },
  "previous_year": { ... },
  "normal": {
    "years": "1996-2025",
    "by_day_of_year": [
      {"doy": 1, "mean_accumulated": 0.0, "stddev": 0.0},
      {"doy": 2, "mean_accumulated": 0.1, "stddev": 0.2}
    ]
  }
}
```

---

## Open Questions

1. **Base temperature:** 50°F is standard for insects. Should we make this
   configurable, or just hardcode it? Recommendation: configurable setting with
   50°F default.

2. **GDD start date:** Jan 1 is conventional. Some models use a "biofix" date
   (e.g., first sustained warmth). Jan 1 is simpler and more comparable.

3. **Forecast extension:** Should the timeline show projected GDD using the
   16-day forecast? This would extend the current-year line ~2 weeks into the
   future. Easy to do since we already have forecast temps.

4. **Species-specific thresholds:** Literature has emergence GDD for some
   common species (Monarch ~600, Swallowtails ~400). Should we curate a lookup
   table? Could be a nice touch on the timeline but requires manual research.

5. **Cache invalidation:** The 30-year historical data is ~50MB of JSON (30
   years x 365 days x a few fields). Should we store as compressed JSON,
   SQLite, or Parquet? JSON is simplest; Parquet is smallest. Given the
   project's current JSON-everything approach, JSON with gzip seems pragmatic.

---

## Summary

| Phase | What | New Data Source | Effort |
|-------|------|-----------------|--------|
| 1 | Today's GDD card | Open-Meteo archive | Small |
| 2 | Year timeline chart | Open-Meteo archive (30yr) | Medium |
| 3 | Species GDD correlation | Cross-ref observations + GDD | Medium |
| 4 | Map GDD overlay | USA-NPN WMS | Small |

The project already fetches temperature data from Open-Meteo and renders static
HTML via Jinja2. GDD computation is a straightforward addition — the formula is
trivial, the data source is already integrated, and the rendering pipeline is
well-established. Phase 1 could ship quickly. The timeline chart (Phase 2) is
the most impactful visualization for trip planning.
