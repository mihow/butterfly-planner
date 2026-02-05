# Ensemble Confidence Module - Implementation Plan

## Status: Stubbed (API + Statistics Ready)

The ensemble module foundation is complete (`src/butterfly_planner/sunshine.py:220-270`), but the visualization and user-facing features are stubbed out.

## What's Already Done

✅ **API Integration** (`fetch_ensemble_sunshine`)
- Fetches from Open-Meteo Ensemble API
- Supports GFS Seamless model (31 ensemble members)
- Returns hourly data for up to 35 days
- Properly parses `sunshine_duration_member00` ... `sunshine_duration_member30`

✅ **Data Model** (`EnsembleSunshine`)
- Stores time + list of member values
- Statistical properties: `mean`, `std`, `min`, `max`
- Percentiles: `p10`, `p50` (median), `p90`
- Confidence width: `p90 - p10` (narrower = higher confidence)

✅ **Tests**
- Full test coverage in `tests/test_sunshine.py:113-122`
- Validates statistics and percentiles

## What Needs Implementation

### 1. Visualization Component

**Option A: Text-based ASCII (Simple)**
```
Sunshine Confidence (Feb 7)
Hour    Low ── Mean ── High
10am    [====|████|====]  30-45-55 min  (moderate)
11am    [==|████████|==]  40-52-58 min  (high confidence)
12pm    [========|██|==]  20-48-55 min  (low confidence)
```

**Option B: HTML Chart (Recommended)**
- Use confidence bands (shaded regions between p10-p90)
- Line chart showing mean with error ribbons
- Color coding: green (narrow band) to red (wide band)
- Interactive tooltips with all ensemble member values

**Implementation Location:**
- Add `render_ensemble_confidence()` in `flows/build.py`
- Template HTML in `build_html()` function

### 2. Smart Fetching Strategy

**Problem:** Ensemble API costs ~4x regular API calls

**Solutions:**
1. **Fetch only for interesting days**
   - Only fetch for days 3-7 (where uncertainty matters most)
   - Days 0-2: Use standard forecast (already accurate)
   - Days 8+: Too far out, confidence always low

2. **Cache ensemble data**
   - Store in `data/raw/ensemble.json`
   - TTL: 6 hours (ensemble models update 4x daily)
   - Only refetch if cache is stale

3. **User-triggered mode**
   - Add `--with-ensemble` flag to CLI
   - Don't fetch by default (cost optimization)
   - Example: `butterfly-planner refresh --with-ensemble`

### 3. UI/UX Decisions

**Where to display?**
- Add new section: "📊 Forecast Confidence (Days 3-7)"
- Place between 16-day forecast and regular weather
- Show only days where confidence matters

**What to show?**
- Visual confidence bands (p10-p90 range)
- Mean sunshine hours
- Confidence rating: "High" / "Medium" / "Low"
  - High: confidence_width < 1800 sec (30 min)
  - Medium: 1800-3600 sec
  - Low: > 3600 sec (1 hour)

**Interpretation help:**
```
🟢 High confidence: All models agree - trust this forecast
🟡 Medium confidence: Some model disagreement - conditions may vary
🔴 Low confidence: Models strongly disagree - uncertainty high
```

## Implementation Steps

### Phase 1: Basic Visualization (1-2 hours)
1. Add `render_ensemble_confidence()` to `build.py`
2. Create simple HTML table with p10/mean/p90
3. Add confidence width indicator (color-coded)
4. Wire into `build_html()` (conditional on ensemble data)

### Phase 2: Smart Fetching (30 min)
1. Add `--with-ensemble` flag to CLI
2. Update `flows/fetch.py` to conditionally fetch
3. Add cache logic with TTL checking
4. Update refresh command documentation

### Phase 3: Enhanced Visualization (2-3 hours)
1. Switch from table to chart visualization
2. Add confidence bands (shaded regions)
3. Interactive hover tooltips
4. Compare to standard forecast (show divergence)

### Phase 4: Testing & Documentation (1 hour)
1. Add integration test for ensemble flow
2. Update README with ensemble usage
3. Document API cost implications
4. Add example screenshots

## Code Example: Basic Visualization

```python
# In flows/build.py

def render_ensemble_confidence(ensemble: list[EnsembleSunshine]) -> str:
    """Render ensemble confidence visualization."""
    html = ['<h2>📊 Forecast Confidence (Days 3-7)</h2>']
    html.append('<table><tr><th>Time</th><th>Range</th><th>Mean</th><th>Confidence</th></tr>')

    for slot in ensemble:
        # Filter to daytime hours (6am-8pm)
        if slot.time.hour < 6 or slot.time.hour > 20:
            continue

        # Calculate confidence
        width_min = slot.confidence_width / 60
        if width_min < 30:
            conf = '🟢 High'
        elif width_min < 60:
            conf = '🟡 Medium'
        else:
            conf = '🔴 Low'

        # Format
        time_str = slot.time.strftime('%b %d %I%p')
        p10_min = slot.p10 / 60
        p90_min = slot.p90 / 60
        mean_min = slot.mean / 60

        html.append(
            f'<tr>'
            f'<td>{time_str}</td>'
            f'<td>{p10_min:.0f}-{p90_min:.0f} min</td>'
            f'<td>{mean_min:.0f} min</td>'
            f'<td>{conf}</td>'
            f'</tr>'
        )

    html.append('</table>')
    return '\n'.join(html)
```

## API Cost Analysis

**Standard Forecast API:** ~1 API call per location
**Ensemble API:** ~4 API calls per location

**Recommended Usage:**
- Default: Standard forecast only (free tier: 10,000/day)
- Manual: `--with-ensemble` for important trips (reduces to ~2,500/day)
- Scheduled: Fetch ensemble 1x per day at 6am UTC (31 members refresh overnight)

**Free Tier Limits:**
- Open-Meteo free tier: 10,000 requests/day
- With ensemble: ~2,500 locations/day
- Current usage: 1 location (Portland) = 2 calls/day max

## References

- Open-Meteo Ensemble API: https://open-meteo.com/en/docs/ensemble-api
- GFS Ensemble docs: https://www.ncei.noaa.gov/products/weather-climate-models/global-ensemble-forecast
- Current implementation: `src/butterfly_planner/sunshine.py:220-270`
- Tests: `tests/test_sunshine.py:113-122`

## Future Enhancements

1. **Multi-model ensemble**
   - Combine GFS + ECMWF ensembles
   - Better uncertainty quantification

2. **Probabilistic forecasts**
   - "70% chance of >4 hours sunshine"
   - Risk-based butterfly trip planning

3. **Historical accuracy tracking**
   - Compare ensemble forecast to actual weather
   - Learn which conditions have higher uncertainty

4. **Location-specific tuning**
   - Coastal vs inland accuracy differences
   - Seasonal confidence patterns
