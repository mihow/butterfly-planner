# Growing Degree Days (GDD) Data Sources Research

**Date:** 2026-02-06
**Author:** Claude (Research Agent)

## Question/Goal

Research GDD data availability for Oregon and Washington state to support butterfly emergence prediction. Determine which free APIs or datasets provide historical GDD data, understand data availability timelines, confirm appropriate base temperatures for butterfly/insect calculations, and identify standard calculation formulas.

---

## Executive Summary

**Best Options for Butterfly Planner:**

1. **USA-NPN (USA National Phenology Network)** - Best for pre-computed GDD with flexible base temperatures (32°F or 50°F), gridded data, WMS/WCS API access, no authentication required
2. **Open-Meteo Historical Weather API** - Best for computing custom GDD from daily temperature data, free, no API key, covers 1950-2050 via Climate API
3. **PRISM** - High-resolution gridded temperature data (800m resolution now free as of March 2025), ideal for spatial analysis
4. **NOAA CDO API** - Comprehensive historical data back to 1981, but API deprecated (use new endpoint), requires token, rate-limited

**Base Temperature:** 50°F (10°C) is standard for butterflies and most insects
**Calculation Formula:** GDD = max(0, (T_max + T_min)/2 - T_base)
**Upper Threshold:** 86°F commonly used with horizontal cutoff method

---

## 1. Free APIs and Datasets

### 1.1 USA National Phenology Network (USA-NPN)

**Status:** ✅ **HIGHLY RECOMMENDED** - Purpose-built for phenology with pre-computed GDD

**Overview:**
- Provides gridded Accumulated Growing Degree Days (AGDD) for the Contiguous United States
- Data available from 1981 to current year (2026)
- Base temperatures available: **32°F or 50°F**
- Spatial coverage: CONUS (includes Oregon and Washington)
- **No API key required** - just self-identify with name/institution

**API Access:**

**Base URL:** `http://geoserver.usanpn.org/geoserver/`

**Services:**
- WMS (Web Map Service) - for images/maps
- WCS (Web Coverage Service) - for raster data/GIS

**WCS GetCapabilities:**
```
http://geoserver.usanpn.org/geoserver/ows?service=WCS&version=2.0.1&request=GetCapabilities
```

**WCS GetCoverage Example (50°F base, Feb 6 2026):**
```
http://geoserver.usanpn.org/geoserver/ows?service=WCS&version=2.0.1&request=GetCoverage&coverageId=gdd:agdd_50f&SUBSET=time("2026-02-06T00:00:00.000Z")&format=image/geotiff
```

**WMS GetMap Example (50°F base, Feb 6 2026):**
```
http://geoserver.usanpn.org/geoserver/gdd/wms?service=WMS&request=GetMap&layers=gdd:agdd&time=2026-2-6&bbox=-125.020833333333,24.0625,-66.479166666662,49.937500000002&width=1000&height=500&srs=EPSG:4269&format=image/png
```

**Coverage IDs:**
- `gdd:agdd` - Default AGDD (check base temp in metadata)
- `gdd:agdd_50f` - Explicitly 50°F base
- `gdd:agdd_32f` - Explicitly 32°F base (if available)

**Interactive Request Builder:**
https://www.usanpn.org/geoserver-request-builder

**R Package Access:**
```r
library(rnpn)
# No API key required, just provide request_source
npn_download_geospatial(...)
```

**Rate Limits:** None specified - reasonable use expected

**Data Format:** GeoTIFF (WCS), PNG/GIF/PDF (WMS), NetCDF supported

**Spatial Resolution:** Gridded data (exact resolution not specified in search results, typically ~4km for CONUS products)

**Documentation:**
- Main: https://www.usanpn.org/data/maps/AGDD
- NPN Geoserver Docs: https://docs.google.com/document/d/1jDqeh8k30t0vEBAJu2ODiipaofLZ2PFgsaNzhhzz3xg/pub
- R Package: http://usa-npn.github.io/rnpn/articles/VI_geospatial.html

---

### 1.2 Open-Meteo APIs

**Status:** ✅ **RECOMMENDED** - Free, no API key, compute custom GDD from temperature

**Overview:**
- Free weather API with no API key required
- Multiple API endpoints for different time ranges
- Provides daily min/max temperature - compute GDD yourself
- High spatial resolution (10km)
- JSON response format

**Climate API (Best for 2026):**
- **URL:** https://open-meteo.com/en/docs/climate-api
- **Coverage:** 1950-2050 daily data
- **Resolution:** 10 km
- **Variables:** `temperature_2m_max`, `temperature_2m_min`
- **Perfect for:** Computing GDD for agricultural applications

**Historical Weather API:**
- **URL:** https://open-meteo.com/en/docs/historical-weather-api
- **Coverage:** 1940-present (based on ERA5 reanalysis)
- **Endpoint:** `/v1/archive`
- **Variables:** Daily temperature, precipitation, etc.

**Example Request (Portland, OR - Daily Temps for Jan 2026):**
```
https://archive-api.open-meteo.com/v1/archive?latitude=45.5&longitude=-122.6&start_date=2026-01-01&end_date=2026-01-31&daily=temperature_2m_max,temperature_2m_min&timezone=America/Los_Angeles
```

**GDD Calculation:**
You must compute GDD yourself:
```python
def calculate_gdd(tmax, tmin, base=10.0):
    """Calculate GDD from daily temps (Celsius)"""
    avg_temp = (tmax + tmin) / 2
    return max(0.0, avg_temp - base)
```

**Rate Limits:**
- Free tier: Reasonable use
- No API key required
- Commercial use requires subscription

**Data Format:** JSON

**Spatial Resolution:** 10 km gridded (point queries)

---

### 1.3 PRISM Climate Data (Oregon State University)

**Status:** ✅ **RECOMMENDED** - High-resolution gridded temperature, 800m now free!

**Overview:**
- **MAJOR UPDATE:** As of March 2025, 800m resolution data is **FREE** (previously paid)
- Time series: Daily (1981-present), Monthly (1895-present), Annual (1895-present)
- Covers entire US including Oregon and Washington
- Highest spatial resolution available (800m = ~0.5 miles)

**Data Available:**
- Daily min/max temperature (`tmin`, `tmax`)
- Precipitation (`ppt`)
- Dew point temperature
- Vapor pressure deficit

**Resolution:**
- **800m (4km and 800m both free as of 2025)**
- 4km resolution

**Access Methods:**

**1. Web Service API (Bulk Downloads):**
```
https://services.nacse.org/prism/data/get/releaseDate/us/800m/tmax/[YYYYMMDD]
https://services.nacse.org/prism/data/get/releaseDate/us/4km/tmin/[YYYYMMDD]
```

**2. FTP Server:**
- Web-browseable FTP with all time series and normals
- Documentation: https://prism.oregonstate.edu/documents/PRISM_downloads_web_service.pdf

**3. Data Explorer (Time Series at Points):**
- https://prism.oregonstate.edu/explorer/
- Interactive tool for point location queries

**4. Google Earth Engine:**
- Dataset: `OREGONSTATE/PRISM/AN81d`
- Available from 1981-01-01 to 2025-10-13
- Variables: `ppt`, `tmean`, `tmin`, `tmax`, `tdmean`, `vpdmin`, `vpdmax`

**5. R Package:**
```r
library(prism)
# Download bulk data via web service API
```

**GDD Computation:**
- PRISM does **not** provide pre-computed GDD
- Download tmin/tmax grids and compute GDD yourself
- Ideal for high-resolution spatial GDD mapping

**Rate Limits:** None specified for web service

**Data Format:** GeoTIFF, BIL (Band Interleaved by Line)

**Authentication:** None required

**Documentation:**
- Main: https://prism.oregonstate.edu/
- Downloads: https://prism.oregonstate.edu/data/
- R Package: https://docs.ropensci.org/prism/

---

### 1.4 NOAA Climate Data Online (CDO) API

**Status:** ⚠️ **AVAILABLE BUT API DEPRECATED** - Still works, new endpoint available

**Overview:**
- Comprehensive historical weather data
- Station-level data (not gridded)
- Includes pre-computed degree days (GDD, HTDD, CLDD)
- Data back to 1981+ depending on station

**⚠️ IMPORTANT: API v2 Deprecated**

Old endpoint (still works): `https://www.ncei.noaa.gov/cdo-web/api/v2`
**New endpoint:** `https://www.ncei.noaa.gov/access/services/data/v1`

**New Documentation:**
- Data Service: https://www.ncei.noaa.gov/support/access-data-service-api-user-documentation
- Search Service: https://www.ncei.noaa.gov/support/access-search-service-api-user-documentation

**Authentication:**
- Requires API token (free)
- Request at: https://www.ncdc.noaa.gov/cdo-web/token
- Delivered via email

**Rate Limits:**
- **5 requests per second**
- **10,000 requests per day**

**Available Degree Day Datatypes:**

**GDD (Growing Degree Days):**
- Datatype ID: `GDD` (check documentation for exact ID)
- Formula: GDD = (T_max + T_min)/2 - 50°F
- Note: Uses 50°F base for corn/agriculture
- Max/min temps capped at 86°F/50°F

**HTDD (Heating Degree Days):**
- Base: 65°F
- Formula: When avg temp < 65°F, HTDD = 65 - avg_temp

**CLDD (Cooling Degree Days):**
- Base: 65°F
- Formula: When avg temp > 65°F, CLDD = avg_temp - 65

**Datasets:**
- `GHCND` - Global Historical Climatology Network Daily (most comprehensive)
- `GSOM` - Global Summary of the Month
- `GSOY` - Global Summary of the Year

**Example API v2 Request (Daily data for location):**
```
https://www.ncei.noaa.gov/cdo-web/api/v2/data?datasetid=GHCND&locationid=ZIP:97202&startdate=2026-01-01&enddate=2026-01-31&datatypeid=TMAX,TMIN
```

**Headers Required:**
```
token: YOUR_TOKEN_HERE
```

**Data Format:** JSON

**Spatial Resolution:** Point data from weather stations (not gridded)

**Historical Availability:**
- Daily: 1981 to present (varies by station)
- Monthly summaries: Longer records available

**Python Libraries:**
- `noaa-cdo-api` (PyPI)
- `cdo-api-py` (PyPI)

**Documentation:**
- API v2 Docs: https://www.ncdc.noaa.gov/cdo-web/webservices/v2
- Datasets: https://www.ncei.noaa.gov/cdo-web/datasets

---

### 1.5 AgWeatherNet (Washington State University)

**Status:** ⚠️ **REGIONAL (WA only)** - Station network, API access restricted

**Overview:**
- Washington State's agricultural weather network
- 175+ weather stations across Washington
- Real-time and historical data
- Pre-computed GDD with custom base temperatures

**Coverage:** **Washington State only** (not Oregon)

**GDD Features:**
- Calculate GDD with custom base temperature (e.g., 50°F)
- No upper threshold by default
- Accumulation from custom start dates

**Access Methods:**

**1. Web Interface (Free Account Required):**
- https://weather.wsu.edu/
- Sign up for free account
- Access via "AWN Reports" → "Degree Day"
- Select station, base temp (e.g., 50°F), date range

**2. API Access (Permission Required):**
- API exists (Python wrapper: `AWNPy` on GitHub)
- **Requires registration and permission** from AgWeatherNet
- Contact AgWeatherNet to request API access
- Authentication: Username/password

**Python Wrapper:**
```python
# GitHub: joejoezz/AWNPy
# Requires AWN account and API permission
```

**GDD Calculation:**
- All GDD in °F
- Base temperature: User-defined (default 50°F for grapes)
- Method: Not specified (likely simple average method)

**Data Format:** Web interface (CSV export available), API returns JSON

**Spatial Resolution:** Point data from weather stations (~175 stations across WA)

**Rate Limits:** Unknown - API access is restricted

**Historical Availability:** Historical data available through registered accounts

**Limitations:**
- Washington State only
- API access requires explicit permission
- Not suitable for Oregon coverage

**Documentation:**
- Main site: https://weather.wsu.edu/
- GDD Info: https://wine.wsu.edu/extension/weather/growing-degree-days/
- Python wrapper: https://github.com/joejoezz/AWNPy

---

## 2. Historical Data Availability

| Source | Time Range | Update Frequency | Restrictions |
|--------|-----------|------------------|--------------|
| **USA-NPN** | 1981 - Current Year (2026) | Daily | None - free access |
| **Open-Meteo Climate API** | 1950 - 2050 | Daily | None - free for non-commercial |
| **Open-Meteo Historical** | 1940 - Present | Daily | None - free for non-commercial |
| **PRISM** | Daily: 1981-present<br>Monthly: 1895-present | Daily updates | None - now free as of 2025 |
| **NOAA CDO API** | 1981+ (varies by station) | Daily | Token required, rate limited |
| **AgWeatherNet** | Historical available | Real-time + historical | Washington only, API restricted |

**Answer to Question 2:**

✅ **Yes, we can get historical GDD for any given day of previous years**

- **USA-NPN:** Daily GDD from 1981-2026 (45 years of history)
- **Open-Meteo:** Daily temperature data 1940-present (compute GDD yourself)
- **PRISM:** Daily temperature 1981-present (compute GDD from gridded data)
- **NOAA CDO:** Daily station data 1981+ (varies by station location)

**Typical availability: 40-80+ years depending on source**

---

## 3. Base Temperatures for Butterfly/Insect GDD

**Standard Base Temperature:**

**✅ 50°F (10°C)** is the **most commonly used** base temperature for insects, including butterflies.

### Why 50°F?

From research findings:

> "A developmental threshold (baseline) temperature of 50°F is commonly used, as 50°F is used for insect and mite pests of woody ornamental plants in the Northeast as most of these plants initiate their growth between 45°F-55°F in our region."

> "50°F is used for insect and mite pests of woody ornamental plants"

### Butterfly-Specific Thresholds

From the existing documentation in `/home/user/butterfly-planner/.claude/docs/adding-data-sources.md`:

**Common butterfly emergence thresholds (accumulated GDD with 50°F base):**
- **Monarch:** ~600 GDD
- **Swallowtail:** ~400 GDD
- **Painted Lady:** ~350 GDD

### Other Base Temperatures (for reference)

- **32°F (0°C):** Sometimes used for very cold-tolerant insects
- **41°F (5°C):** Some early-season insects
- **50°F (10°C):** ✅ **Standard for most insects and butterflies**
- **65°F (18°C):** Used for HTDD/CLDD (heating/cooling degree days) - NOT for insects

**Recommendation:** Use **50°F (10°C)** as the base temperature for butterfly GDD calculations.

---

## 4. Standard GDD Calculation Formulas

### 4.1 Simple Average Method (Most Common)

**Basic Formula:**
```
GDD = max(0, (T_max + T_min) / 2 - T_base)
```

Where:
- `T_max` = Daily maximum temperature
- `T_min` = Daily minimum temperature
- `T_base` = Base temperature (50°F / 10°C for butterflies)
- `max(0, x)` = If result is negative, use 0

**Example:**
```
T_max = 75°F, T_min = 55°F, T_base = 50°F
GDD = max(0, (75 + 55) / 2 - 50)
GDD = max(0, 65 - 50)
GDD = 15 degree days
```

**When temperature below base:**
```
T_max = 45°F, T_min = 35°F, T_base = 50°F
GDD = max(0, (45 + 35) / 2 - 50)
GDD = max(0, 40 - 50)
GDD = max(0, -10)
GDD = 0 degree days
```

### 4.2 Modified Method with Upper/Lower Thresholds

Used by NOAA and many agricultural systems:

**Formula:**
```
T_max_adjusted = min(T_max, upper_threshold)
T_min_adjusted = max(T_min, lower_threshold)
GDD = max(0, (T_max_adjusted + T_min_adjusted) / 2 - T_base)
```

**Common thresholds for insects:**
- Lower threshold: 50°F (same as base)
- Upper threshold: 86°F (30°C)

**Example (with 86°F cap):**
```
T_max = 95°F, T_min = 60°F, T_base = 50°F
T_max_adjusted = min(95, 86) = 86°F
T_min_adjusted = max(60, 50) = 60°F
GDD = max(0, (86 + 60) / 2 - 50)
GDD = 73 - 50 = 23 degree days
```

**Rationale:** Insects don't develop faster above certain temperatures (86°F), so GDD is capped.

### 4.3 Single Sine Method

More accurate for insect modeling - uses sine wave to approximate daily temperature curve.

**Method:**
1. Fit sine curve from T_min (sunrise) to T_max (afternoon) back to next T_min
2. Calculate area under curve above T_base
3. Divide by 24 hours to get daily GDD

**When to use:** More accurate for insects with known thermal response curves.

**Complexity:** Requires numerical integration or lookup tables.

### 4.4 Double Sine Method

Most mathematically complex - fits separate sine curves for daytime and nighttime.

**Method:**
1. Sine curve from T_min to T_max (first half of day)
2. Separate sine curve from T_max to next T_min (second half)
3. Calculate area under curves above T_base

**When to use:** Most accurate for detailed insect phenology models.

**Used by:** Codling moth, peach twig borer models (with horizontal cutoff at 86°F)

### 4.5 Horizontal Cutoff vs Vertical Cutoff

**Horizontal Cutoff (most common):**
- Temperature above upper threshold is set to upper threshold
- GDD continues to accumulate at max rate
- Example: If T > 86°F, treat as if T = 86°F

**Vertical Cutoff (rare):**
- No GDD accumulation when T > upper threshold
- Used for heat-sensitive organisms

### 4.6 Accumulated GDD

**Seasonal accumulation:**
```
Accumulated_GDD = Σ(Daily_GDD)
```

Sum GDD from:
- **January 1** (standard for USA-NPN, NOAA)
- **March 1** (spring crops/insects)
- **Custom start date** (first frost, biofix date, etc.)

**Example Python Implementation:**
```python
def calculate_daily_gdd(t_max: float, t_min: float, t_base: float = 10.0,
                       upper_threshold: float = 30.0) -> float:
    """
    Calculate GDD for a single day (Celsius).

    Args:
        t_max: Daily maximum temperature (°C)
        t_min: Daily minimum temperature (°C)
        t_base: Base temperature (°C), default 10°C = 50°F
        upper_threshold: Upper temperature threshold (°C), default 30°C = 86°F

    Returns:
        Growing degree days for the day
    """
    # Apply thresholds
    t_max_adj = min(t_max, upper_threshold)
    t_min_adj = max(t_min, t_base)

    # Calculate average
    avg_temp = (t_max_adj + t_min_adj) / 2

    # Calculate GDD (cannot be negative)
    return max(0.0, avg_temp - t_base)

def accumulate_gdd(daily_temps: list[tuple[float, float]],
                  t_base: float = 10.0) -> float:
    """
    Accumulate GDD over a season.

    Args:
        daily_temps: List of (t_max, t_min) tuples
        t_base: Base temperature (°C)

    Returns:
        Total accumulated GDD
    """
    return sum(calculate_daily_gdd(tmax, tmin, t_base)
               for tmax, tmin in daily_temps)
```

**Summary:**

| Method | Accuracy | Complexity | Use Case |
|--------|----------|------------|----------|
| Simple Average | Good | Low | General use, quick estimates |
| Modified w/ Thresholds | Better | Low | Agricultural systems, NOAA |
| Single Sine | Better | Medium | Detailed insect models |
| Double Sine | Best | High | Research, precision agriculture |

**Recommendation for Butterfly Planner:** Start with **Modified Method with Upper Threshold (86°F)** - it's accurate, widely used, and easy to implement.

---

## 5. Computing GDD from Daily Min/Max Temperature

### Answer: ✅ **YES - GDD can easily be computed from daily min/max temperature**

### Requirements:
1. Daily maximum temperature (T_max)
2. Daily minimum temperature (T_min)
3. Base temperature (T_base = 50°F / 10°C)
4. Optional: Upper threshold (T_upper = 86°F / 30°C)

### Data Sources for Computing GDD:

**Best Options:**

1. **Open-Meteo (FREE, no API key):**
   ```
   https://archive-api.open-meteo.com/v1/archive?latitude=45.5&longitude=-122.6
     &start_date=2026-01-01&end_date=2026-01-31
     &daily=temperature_2m_max,temperature_2m_min
     &timezone=America/Los_Angeles
   ```
   - Returns JSON: `{"daily": {"time": [...], "temperature_2m_max": [...], "temperature_2m_min": [...]}}`
   - Loop through days, compute GDD, accumulate

2. **PRISM (FREE, high-resolution spatial):**
   - Download tmax/tmin GeoTIFF grids
   - Compute GDD for each grid cell
   - Results in high-resolution GDD maps (800m resolution)

3. **NOAA CDO API (FREE with token):**
   - Request `TMAX` and `TMIN` datatypes
   - Compute GDD from station data

**Implementation Example:**

```python
import requests
from datetime import date, timedelta

def fetch_and_compute_gdd(lat: float, lon: float, start: date, end: date) -> list[dict]:
    """
    Fetch temperature data from Open-Meteo and compute GDD.

    Returns list of {date, tmax, tmin, gdd, accumulated_gdd}
    """
    # Fetch temperature data
    url = "https://archive-api.open-meteo.com/v1/archive"
    params = {
        "latitude": lat,
        "longitude": lon,
        "start_date": start.isoformat(),
        "end_date": end.isoformat(),
        "daily": "temperature_2m_max,temperature_2m_min",
        "temperature_unit": "fahrenheit"  # or celsius
    }

    response = requests.get(url, params=params, timeout=30)
    response.raise_for_status()
    data = response.json()

    # Extract daily values
    daily = data["daily"]
    dates = daily["time"]
    tmax_values = daily["temperature_2m_max"]
    tmin_values = daily["temperature_2m_min"]

    # Compute GDD
    results = []
    accumulated = 0.0

    for i, date_str in enumerate(dates):
        tmax = tmax_values[i]
        tmin = tmin_values[i]

        # Apply thresholds (50°F base, 86°F upper)
        tmax_adj = min(tmax, 86.0)
        tmin_adj = max(tmin, 50.0)

        # Calculate daily GDD
        avg_temp = (tmax_adj + tmin_adj) / 2
        daily_gdd = max(0.0, avg_temp - 50.0)

        accumulated += daily_gdd

        results.append({
            "date": date_str,
            "tmax": tmax,
            "tmin": tmin,
            "daily_gdd": daily_gdd,
            "accumulated_gdd": accumulated
        })

    return results

# Example usage
gdd_data = fetch_and_compute_gdd(
    lat=45.5,  # Portland, OR
    lon=-122.6,
    start=date(2026, 1, 1),
    end=date(2026, 2, 6)
)

print(f"Accumulated GDD so far in 2026: {gdd_data[-1]['accumulated_gdd']:.1f}")
```

### Advantages of Computing GDD Yourself:

✅ **Full control** over base temperature (can use butterfly-specific values)
✅ **Custom thresholds** (try different upper limits)
✅ **Custom start dates** (Jan 1, Mar 1, first frost, etc.)
✅ **No dependency** on pre-computed GDD products
✅ **Works with any temperature data source**

### Disadvantages:

❌ Requires computation step
❌ Must handle missing data
❌ Need to choose calculation method (simple vs sine)

**Recommendation:** Compute GDD from Open-Meteo or PRISM temperature data for maximum flexibility.

---

## 6. Spatial Resolution Comparison

| Source | Type | Resolution | Coverage | Notes |
|--------|------|------------|----------|-------|
| **USA-NPN** | Gridded | ~4km (typical CONUS) | CONUS | Pre-computed GDD grids |
| **Open-Meteo** | Gridded (point queries) | 10 km | Global | Query by lat/lon, returns point value |
| **PRISM** | Gridded | **800m** (0.5 miles) | CONUS | Highest resolution! 800m now free |
| **NOAA CDO** | Station | Point data | Station locations | Not gridded, varies by station density |
| **AgWeatherNet** | Station | Point data | Washington stations | 175+ stations in WA only |

### Detailed Comparison:

**USA-NPN:**
- ✅ Gridded coverage (good for mapping)
- ✅ Pre-computed GDD (no calculation needed)
- ⚠️ Moderate resolution (~4km)
- ✅ Easy WMS/WCS access

**Open-Meteo:**
- ✅ Gridded with point queries (10km)
- ✅ Global coverage
- ⚠️ Must compute GDD yourself
- ✅ Very easy API

**PRISM:**
- ✅✅ **Highest resolution (800m!)** - best for detailed spatial analysis
- ✅ Gridded raster data (ideal for GIS)
- ⚠️ Must compute GDD yourself
- ✅ Now FREE as of March 2025
- ✅ Best for creating high-resolution GDD maps

**NOAA CDO:**
- ❌ Point data only (not gridded)
- ⚠️ Interpolation required for spatial coverage
- ✅ Very long historical records
- ⚠️ Station density varies (sparse in rural areas)

**AgWeatherNet:**
- ❌ Point data only (station network)
- ❌ Washington only
- ✅ Pre-computed GDD with custom base temps
- ⚠️ ~175 stations = good density in WA agricultural areas

### Recommendation for Butterfly Planner:

**Best approach: Hybrid strategy**

1. **For high-resolution GDD maps (Oregon & Washington):**
   - Use **PRISM 800m** temperature grids
   - Compute GDD using modified method (50°F base, 86°F upper)
   - Result: High-resolution GDD raster suitable for mapping

2. **For quick point-location GDD:**
   - Use **USA-NPN WCS/WMS** for pre-computed values
   - Or **Open-Meteo** API for custom calculations

3. **For Washington-specific station data:**
   - Optionally integrate **AgWeatherNet** for real-time station data

**Implementation Priority:**
1. Start with Open-Meteo (easiest, no auth, compute GDD)
2. Add USA-NPN WMS maps for visualization
3. Later: PRISM for high-resolution spatial analysis

---

## 7. Authentication and Rate Limits Summary

| Source | Authentication | Rate Limits | Cost |
|--------|----------------|-------------|------|
| **USA-NPN** | None (self-identify in request) | None specified | FREE |
| **Open-Meteo** | None | Reasonable use | FREE (non-commercial) |
| **PRISM** | None | None | **FREE** (as of Mar 2025) |
| **NOAA CDO** | API token (free, emailed) | 5 req/sec, 10k req/day | FREE |
| **AgWeatherNet** | Username/password (permission) | Unknown | FREE (WA only) |

**Best for immediate use:** Open-Meteo (no auth) or USA-NPN (no auth)

---

## 8. Recommendations for Butterfly Planner

### Phase 1: Quick Implementation (Week 1)

**Use Open-Meteo + Compute GDD:**

```python
# src/butterfly_planner/gdd.py
import requests
from datetime import date

def fetch_gdd_from_openmeteo(lat: float, lon: float,
                             start: date, end: date) -> dict:
    """Fetch temps from Open-Meteo and compute GDD."""
    url = "https://archive-api.open-meteo.com/v1/archive"
    params = {
        "latitude": lat,
        "longitude": lon,
        "start_date": start.isoformat(),
        "end_date": end.isoformat(),
        "daily": "temperature_2m_max,temperature_2m_min",
        "temperature_unit": "fahrenheit"
    }

    resp = requests.get(url, params=params, timeout=30)
    resp.raise_for_status()
    data = resp.json()

    # Compute GDD (see implementation above)
    # ...

    return {"daily_gdd": results, "accumulated_gdd": accumulated}
```

**Benefits:**
- ✅ No API key needed
- ✅ Works immediately
- ✅ Historical data back to 1940
- ✅ Custom base temps possible

### Phase 2: Add Mapping (Week 2-3)

**Integrate USA-NPN WMS for GDD map layers:**

```python
# src/butterfly_planner/gdd_maps.py
def get_gdd_map_url(date: str, bbox: tuple) -> str:
    """Generate USA-NPN WMS map URL for GDD visualization."""
    west, south, east, north = bbox
    return (
        f"http://geoserver.usanpn.org/geoserver/gdd/wms?"
        f"service=WMS&request=GetMap&layers=gdd:agdd_50f&time={date}"
        f"&bbox={west},{south},{east},{north}"
        f"&width=800&height=600&srs=EPSG:4326&format=image/png"
    )
```

**Benefits:**
- ✅ Pre-computed GDD layers
- ✅ Professional visualization
- ✅ No computation required

### Phase 3: High-Resolution Analysis (Later)

**Use PRISM for detailed spatial GDD mapping:**

```python
# src/butterfly_planner/gdd_prism.py
import rasterio

def download_prism_temps(date: str, variable: str) -> str:
    """Download PRISM tmax/tmin grid."""
    url = f"https://services.nacse.org/prism/data/get/releaseDate/us/800m/{variable}/{date}"
    # Download GeoTIFF
    # ...

def compute_gdd_grid(tmax_file: str, tmin_file: str) -> array:
    """Compute GDD for each grid cell."""
    # Load rasters, compute GDD spatially
    # ...
```

**Benefits:**
- ✅ 800m resolution (extremely detailed)
- ✅ Create custom GDD maps
- ✅ Overlay with butterfly habitat, isochrones

---

## 9. Code Integration Example

Based on existing `/home/user/butterfly-planner/.claude/docs/adding-data-sources.md`, here's an updated implementation:

**File:** `src/butterfly_planner/flows/fetch.py`

```python
@task(name="fetch-gdd-openmeteo")
def fetch_gdd(lat: float, lon: float, start_date: date, end_date: date) -> dict[str, Any]:
    """
    Fetch GDD using Open-Meteo Historical API.

    Returns:
        {
            "daily_values": [{"date": "2026-01-01", "tmax": 45, "tmin": 35, "gdd": 0, "accumulated": 0}, ...],
            "total_gdd": 150.5,
            "source": "open-meteo",
            "base_temp_f": 50,
            "upper_threshold_f": 86
        }
    """
    from butterfly_planner.gdd import compute_gdd_openmeteo

    result = compute_gdd_openmeteo(lat, lon, start_date, end_date)
    return result

@task(name="save-gdd")
def save_gdd(gdd_data: dict[str, Any]) -> Path:
    """Save GDD data to JSON."""
    output_path = Path("data/raw/gdd.json")
    output_path.parent.mkdir(parents=True, exist_ok=True)

    output = {
        "fetched_at": datetime.now().isoformat(),
        "source": gdd_data["source"],
        "base_temp_f": gdd_data["base_temp_f"],
        "data": gdd_data
    }

    with output_path.open("w") as f:
        json.dump(output, f, indent=2)

    return output_path
```

---

## 10. References

### Data Sources

- [USA National Phenology Network - AGDD Products](https://www.usanpn.org/data/maps/AGDD)
- [USA-NPN Geoserver Documentation](https://docs.google.com/document/d/1jDqeh8k30t0vEBAJu2ODiipaofLZ2PFgsaNzhhzz3xg/pub)
- [USA-NPN R Package Geospatial Guide](http://usa-npn.github.io/rnpn/articles/VI_geospatial.html)
- [Open-Meteo Historical Weather API](https://open-meteo.com/en/docs/historical-weather-api)
- [Open-Meteo Climate API](https://open-meteo.com/en/docs/climate-api)
- [PRISM Climate Group - Oregon State University](https://prism.oregonstate.edu/)
- [PRISM Data Explorer](https://prism.oregonstate.edu/explorer/)
- [PRISM Downloads Web Service Documentation](https://prism.oregonstate.edu/documents/PRISM_downloads_web_service.pdf)
- [NOAA CDO Web Services v2](https://www.ncdc.noaa.gov/cdo-web/webservices/v2)
- [NOAA CDO Token Request](https://www.ncdc.noaa.gov/cdo-web/token)
- [AgWeatherNet - Washington State University](https://weather.wsu.edu/)
- [AgWeatherNet GDD Information](https://wine.wsu.edu/extension/weather/growing-degree-days/)

### GDD Calculation Methods

- [Understanding Growing Degree Days - Nebraska Extension](https://hles.unl.edu/news/understanding-growing-degree-days/)
- [Growing Degree Days for Insect Pests - UMass Extension](https://www.umass.edu/agriculture-food-environment/landscape/fact-sheets/growing-degree-days-for-management-of-insect-pests-in-landscape)
- [Growing Degree Days for Insect Pests - Iowa State Extension](https://crops.extension.iastate.edu/encyclopedia/growing-degree-days-insect-pests)
- [Using Degree Days to Time Treatments for Insect Pests - USU](https://extension.usu.edu/planthealth/research/degree-days)
- [Degree-Day Models - Washington State University](https://treefruit.wsu.edu/crop-protection/opm/dd-models/)
- [GDD Glossary - Ohio State University](https://weather.cfaes.osu.edu/gdd/glossary.asp)

### Technical Documentation

- [NOAA Climate Prediction Center - GDD Explanation](https://www.cpc.ncep.noaa.gov/products/analysis_monitoring/cdus/degree_days/gdd.shtml)
- [PRISM High-Resolution Spatial Climate Data - UCAR](https://climatedataguide.ucar.edu/climate-data/prism-high-resolution-spatial-climate-data-united-states-maxmin-temp-dewpoint)
- [PRISM Google Earth Engine Dataset](https://developers.google.com/earth-engine/datasets/catalog/OREGONSTATE_PRISM_AN81d)
- [USA-NPN Gridded Products USGS Publication](https://pubs.usgs.gov/publication/ofr20171003)

---

## Appendix A: Quick Decision Matrix

**Choose your data source:**

| If you need... | Use... | Why... |
|----------------|--------|--------|
| Pre-computed GDD grids | USA-NPN | No calculation needed, WMS/WCS ready |
| Easiest API, no auth | Open-Meteo | Zero setup, compute GDD yourself |
| Highest spatial resolution | PRISM 800m | Best for detailed maps, now free |
| Long historical records | NOAA CDO or Open-Meteo | NOAA: 1981+, Open-Meteo: 1940+ |
| Station-level data | NOAA CDO | Station metadata, quality flags |
| Washington-specific | AgWeatherNet | 175+ stations, pre-computed GDD |

---

## Appendix B: Example Workflow for Butterfly Planner

```python
from datetime import date
from butterfly_planner.gdd import (
    fetch_openmeteo_gdd,
    fetch_usanpn_gdd_map,
    compute_butterfly_emergence
)

# 1. Get point-location GDD for Portland, OR
portland_gdd = fetch_openmeteo_gdd(
    lat=45.5231,
    lon=-122.6765,
    start=date(2026, 1, 1),
    end=date(2026, 2, 6)
)

print(f"Accumulated GDD: {portland_gdd['total_gdd']:.1f}")

# 2. Predict butterfly emergence
emergence = compute_butterfly_emergence(
    gdd=portland_gdd['total_gdd'],
    species="monarch"  # Needs ~600 GDD
)

if emergence['ready']:
    print("🦋 Monarchs emerging soon!")
else:
    print(f"Need {emergence['remaining_gdd']:.1f} more GDD")

# 3. Get GDD map for Oregon/Washington
map_url = fetch_usanpn_gdd_map(
    date="2026-02-06",
    bbox=(-124.0, 42.0, -116.5, 49.0)  # OR/WA bounding box
)

# Display map in HTML
# <img src="{map_url}" alt="Growing Degree Days Map">
```

---

**End of Report**
