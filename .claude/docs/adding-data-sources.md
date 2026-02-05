# Adding New Data Sources & Modules

This guide walks through adding new data sources (APIs, datasets) and visualization modules to the butterfly-planner app.

## Architecture Overview

```
Data Flow:
┌─────────────┐      ┌──────────────┐      ┌─────────────┐
│   API/Data  │  →   │ flows/fetch  │  →   │ data/raw/   │
│   Source    │      │   (Prefect)  │      │  *.json     │
└─────────────┘      └──────────────┘      └─────────────┘
                                                    ↓
                                            ┌──────────────┐
                                            │ flows/build  │
                                            │  (Prefect)   │
                                            └──────────────┘
                                                    ↓
                                            ┌──────────────┐
                                            │  site/*.html │
                                            └──────────────┘
```

## Step-by-Step: Adding a New Module

Let's use two examples:
1. **Growing Degree Days** (weather-based calculation)
2. **iNaturalist Observations** (external API)

---

## Example 1: Growing Degree Days (GDD)

Growing degree days predict insect emergence based on accumulated heat.

### 1. Create the Module

**File:** `src/butterfly_planner/degree_days.py`

```python
"""
Growing Degree Days (GDD) calculation for butterfly emergence prediction.

GDD formula: max(0, (T_max + T_min) / 2 - T_base)
Base temperature: 10°C (50°F) for most butterflies
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date


@dataclass
class DailyGDD:
    """Growing degree days for a single day."""

    date: date
    temp_max: float
    temp_min: float
    base_temp: float = 10.0  # °C

    @property
    def gdd(self) -> float:
        """Calculate GDD for this day."""
        avg_temp = (self.temp_max + self.temp_min) / 2
        return max(0.0, avg_temp - self.base_temp)


@dataclass
class GDDAccumulation:
    """Accumulated GDD over a season."""

    start_date: date
    daily_values: list[DailyGDD]

    @property
    def total_gdd(self) -> float:
        """Total accumulated GDD."""
        return sum(d.gdd for d in self.daily_values)

    @property
    def days_to_emergence(self) -> int | None:
        """
        Estimate days until butterfly emergence.

        Common thresholds:
        - Monarch: ~600 GDD
        - Swallowtail: ~400 GDD
        - Painted Lady: ~350 GDD
        """
        threshold = 400.0  # Average threshold
        accumulated = 0.0
        for i, day in enumerate(self.daily_values):
            accumulated += day.gdd
            if accumulated >= threshold:
                return i
        return None  # Not reached in forecast period


def calculate_gdd_from_forecast(weather_data: dict) -> list[DailyGDD]:
    """
    Calculate GDD from weather forecast data.

    Args:
        weather_data: Weather data from flows/fetch.py

    Returns:
        List of DailyGDD objects
    """
    daily = weather_data.get("daily", {})
    dates = daily.get("time", [])
    temp_max = daily.get("temperature_2m_max", [])
    temp_min = daily.get("temperature_2m_min", [])

    gdd_values = []
    for i, date_str in enumerate(dates):
        gdd_values.append(
            DailyGDD(
                date=date.fromisoformat(date_str),
                temp_max=temp_max[i],
                temp_min=temp_min[i],
            )
        )

    return gdd_values
```

### 2. Add to Fetch Flow

**File:** `src/butterfly_planner/flows/fetch.py`

```python
# No new API call needed - GDD uses existing weather data!
# Just import the module:
from butterfly_planner.degree_days import calculate_gdd_from_forecast

@task(name="calculate-gdd")
def calculate_gdd(weather: dict[str, Any]) -> list[dict[str, Any]]:
    """Calculate GDD from weather data."""
    gdd_values = calculate_gdd_from_forecast(weather)

    # Convert to JSON-serializable format
    result: list[dict[str, Any]] = []
    for gdd in gdd_values:
        result.append({
            "date": gdd.date.isoformat(),
            "temp_max": gdd.temp_max,
            "temp_min": gdd.temp_min,
            "gdd": gdd.gdd,
        })
    return result

@task(name="save-gdd")
def save_gdd(gdd_data: list[dict[str, Any]]) -> Path:
    """Save GDD data to JSON."""
    output_path = Path("data/raw/degree_days.json")
    output_path.parent.mkdir(parents=True, exist_ok=True)

    output: dict[str, Any] = {
        "fetched_at": datetime.now().isoformat(),
        "source": "calculated",
        "gdd_values": gdd_data,
    }

    with output_path.open("w") as f:
        json.dump(output, f, indent=2)

    return output_path

# Update fetch_all flow:
@flow(name="fetch-data", log_prints=True)
def fetch_all(lat: float = 45.5, lon: float = -122.6) -> dict[str, Any]:
    """Fetch all data sources."""
    print(f"Fetching weather for ({lat}, {lon})...")
    weather = fetch_weather(lat, lon)
    save_weather(weather)

    # Calculate GDD from weather data
    print("Calculating growing degree days...")
    gdd_data = calculate_gdd(weather)
    save_gdd(gdd_data)

    # ... rest of flow
```

### 3. Add to Build Flow

**File:** `src/butterfly_planner/flows/build.py`

```python
@task(name="load-gdd")
def load_gdd() -> dict[str, Any] | None:
    """Load GDD data from JSON."""
    path = Path("data/raw/degree_days.json")
    if not path.exists():
        return None

    with path.open() as f:
        data: dict[str, Any] = json.load(f)
    return data


def render_gdd_section(gdd_data: dict[str, Any]) -> str:
    """Render growing degree days section."""
    gdd_values = gdd_data.get("gdd_values", [])

    html = ['<h2>🌡️ Growing Degree Days (Butterfly Emergence)</h2>']
    html.append('<table>')
    html.append('<tr><th>Date</th><th>Daily GDD</th><th>Accumulated</th></tr>')

    accumulated = 0.0
    for gdd in gdd_values:
        accumulated += gdd["gdd"]
        html.append(
            f'<tr>'
            f'<td>{gdd["date"]}</td>'
            f'<td>{gdd["gdd"]:.1f}</td>'
            f'<td>{accumulated:.1f}</td>'
            f'</tr>'
        )

    html.append('</table>')

    # Add emergence prediction
    if accumulated >= 400:
        html.append('<p class="good-day">🦋 Emergence threshold reached! Watch for butterflies.</p>')
    else:
        remaining = 400 - accumulated
        html.append(f'<p>Need {remaining:.1f} more GDD for emergence.</p>')

    return '\n'.join(html)


@task(name="build-html")
def build_html(weather: dict[str, Any], sunshine: dict[str, Any] | None, gdd: dict[str, Any] | None) -> str:
    """Build HTML from all data sources."""
    # ... existing code ...

    # Add GDD section
    if gdd:
        html.append(render_gdd_section(gdd))

    # ... rest of template
```

### 4. Write Tests

**File:** `tests/test_degree_days.py`

```python
from datetime import date
from butterfly_planner import degree_days


def test_gdd_calculation():
    """Test basic GDD calculation."""
    day = degree_days.DailyGDD(
        date=date(2026, 4, 15),
        temp_max=20.0,
        temp_min=10.0,
        base_temp=10.0
    )

    # (20 + 10) / 2 - 10 = 5.0
    assert day.gdd == 5.0


def test_gdd_below_threshold():
    """Test GDD when temp below base."""
    day = degree_days.DailyGDD(
        date=date(2026, 2, 1),
        temp_max=5.0,
        temp_min=0.0,
        base_temp=10.0
    )

    # (5 + 0) / 2 - 10 = -7.5, max(0, -7.5) = 0
    assert day.gdd == 0.0


def test_accumulation():
    """Test GDD accumulation."""
    days = [
        degree_days.DailyGDD(date=date(2026, 4, i), temp_max=20.0, temp_min=10.0)
        for i in range(1, 8)
    ]

    accum = degree_days.GDDAccumulation(start_date=date(2026, 4, 1), daily_values=days)

    # 5 GDD per day × 7 days = 35
    assert accum.total_gdd == 35.0
```

---

## Example 2: iNaturalist Observations

Pull butterfly observations from iNaturalist API to show recent sightings.

### 1. Create the Module

**File:** `src/butterfly_planner/inaturalist.py`

```python
"""
iNaturalist API integration for butterfly observations.

API docs: https://api.inaturalist.org/v1/docs/
"""

from __future__ import annotations

import requests
from dataclasses import dataclass
from datetime import date, datetime, timedelta


INAT_API = "https://api.inaturalist.org/v1"


@dataclass
class ButterflyObservation:
    """A butterfly sighting from iNaturalist."""

    id: int
    species: str
    common_name: str | None
    observed_on: date
    latitude: float
    longitude: float
    url: str
    photo_url: str | None


def fetch_recent_observations(
    lat: float,
    lon: float,
    radius_km: int = 50,
    days: int = 30
) -> list[ButterflyObservation]:
    """
    Fetch recent butterfly observations near a location.

    Args:
        lat: Latitude
        lon: Longitude
        radius_km: Search radius in kilometers
        days: Days of history to search

    Returns:
        List of butterfly observations
    """
    params = {
        "taxon_id": 47224,  # Lepidoptera (butterflies & moths)
        "lat": lat,
        "lng": lon,
        "radius": radius_km,
        "d1": (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d"),
        "order": "desc",
        "order_by": "observed_on",
        "per_page": 50,
    }

    resp = requests.get(f"{INAT_API}/observations", params=params, timeout=30)
    resp.raise_for_status()
    data = resp.json()

    observations = []
    for obs in data.get("results", []):
        # Extract species info
        taxon = obs.get("taxon", {})
        species = taxon.get("name", "Unknown")
        common = taxon.get("preferred_common_name")

        # Extract photo
        photos = obs.get("photos", [])
        photo_url = photos[0]["url"] if photos else None

        observations.append(
            ButterflyObservation(
                id=obs["id"],
                species=species,
                common_name=common,
                observed_on=date.fromisoformat(obs["observed_on"]),
                latitude=obs["location"].split(",")[0],
                longitude=obs["location"].split(",")[1],
                url=f"https://www.inaturalist.org/observations/{obs['id']}",
                photo_url=photo_url,
            )
        )

    return observations
```

### 2. Add to Fetch Flow

```python
from butterfly_planner.inaturalist import fetch_recent_observations

@task(name="fetch-observations", retries=2)
def fetch_observations(lat: float, lon: float) -> list[dict[str, Any]]:
    """Fetch iNaturalist observations."""
    observations = fetch_recent_observations(lat, lon, radius_km=50, days=30)

    # Serialize to JSON
    result: list[dict[str, Any]] = []
    for obs in observations:
        result.append({
            "id": obs.id,
            "species": obs.species,
            "common_name": obs.common_name,
            "observed_on": obs.observed_on.isoformat(),
            "latitude": obs.latitude,
            "longitude": obs.longitude,
            "url": obs.url,
            "photo_url": obs.photo_url,
        })
    return result
```

### 3. Visualization Ideas

- **Map View:** Plot observations on interactive map
- **Species List:** Show top 10 species seen recently
- **Activity Timeline:** Bar chart of sightings per day
- **Photo Gallery:** Thumbnail grid of recent photos

---

## Best Practices

### 1. Data Models

✅ **Use dataclasses** for type safety:
```python
@dataclass
class MyData:
    field: str
    value: int
```

❌ **Avoid raw dicts** in application code:
```python
# Bad - no type checking
data = {"field": "value", "value": 123}
```

### 2. API Calls

✅ **Always add timeouts**:
```python
requests.get(url, timeout=30)
```

✅ **Add retries** for unreliable APIs:
```python
@task(name="fetch-data", retries=3, retry_delay_seconds=5)
```

✅ **Cache expensive calls**:
```python
# Check cache first
if cache_file.exists() and is_fresh(cache_file):
    return load_from_cache()
```

### 3. Error Handling

✅ **Graceful degradation**:
```python
try:
    data = fetch_api()
except Exception as e:
    logger.warning(f"API failed: {e}")
    data = None  # Site still builds without this module
```

### 4. Testing

✅ **Mock external APIs**:
```python
@patch("my_module.requests.get")
def test_fetch(mock_get):
    mock_get.return_value.json.return_value = {"data": "test"}
    result = fetch_data()
    assert result == expected
```

✅ **Test data models separately**:
```python
def test_data_calculations():
    # No API calls - pure logic testing
    obj = MyDataClass(value=10)
    assert obj.calculated_field == 20
```

---

## Checklist for New Modules

- [ ] Create module in `src/butterfly_planner/<name>.py`
- [ ] Define data models with type annotations
- [ ] Add fetch function (or calculation from existing data)
- [ ] Add to `flows/fetch.py` as a task
- [ ] Save raw data to `data/raw/<name>.json`
- [ ] Add loader in `flows/build.py`
- [ ] Create render function for HTML
- [ ] Wire into `build_html()` template
- [ ] Write comprehensive tests
- [ ] Update README with new feature
- [ ] Document API costs/limits if applicable
- [ ] Add example output to docs

---

## Common Patterns

### Pattern 1: API → JSON → HTML
```
fetch_api() → save_to_json() → load_from_json() → render_html()
```

### Pattern 2: Calculated from Existing Data
```
load_weather() → calculate_metric() → save_to_json() → render_html()
```

### Pattern 3: Hybrid (API + Calculation)
```
fetch_api() → enrich_with_calculation() → save_to_json() → render_html()
```

---

## Future Data Source Ideas

1. **USGS Stream Flow** - Water levels for riparian butterflies
2. **NOAA Climate Data** - Historical weather patterns
3. **GBIF Species Data** - Known butterfly ranges
4. **Soil Moisture** - Affects nectar plant blooms
5. **Air Quality Index** - Butterfly activity correlation
6. **Moon Phase** - Some species more active during full moon
7. **Wildfire Smoke** - Impacts visibility and air quality

---

## References

- Open-Meteo API: https://open-meteo.com/en/docs
- iNaturalist API: https://api.inaturalist.org/v1/docs/
- Prefect docs: https://docs.prefect.io/
- Python dataclasses: https://docs.python.org/3/library/dataclasses.html
