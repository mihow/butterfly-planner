"""Structured daily data contract for multi-consumer use (v0.2, release candidate).

Transforms raw API data into a versioned, consumer-friendly JSON format.
The output is independent of both upstream API shapes and downstream HTML
rendering, suitable for widgets, mobile apps, and APIs.

Status: v0.2 is a hardened release candidate, NOT the stable 1.0 contract.
This revision is a structural refactor (contract relocated out of
``renderers/`` into ``serialization/``) plus correctness/typing hardening
(fully-typed Pydantic models, JSON Schema exported as a build artifact).
Promotion to 1.0 is deferred until a real consumer (widget / CLI / API)
has validated the contract end to end. The schema may still change before
1.0 based on consumer feedback.

Design decisions (carried into v0.2, kept stable through 1.0 unless a
consumer forces a change):
- ``conditions``: removed. Was a UI label with embedded emoji. Consumers
  should look up ``weather_code`` in ``WMO_DESCRIPTIONS`` for a plain-text
  label, or use the numeric code directly.  Single source of truth; no
  presentation logic in the contract.
- ``sunrise``/``sunset``: renamed to ``window_start``/``window_end``. The
  values were always derived from the first/last 15-minute ``is_day==1``
  slot, not from the actual civil sunrise/sunset.  The daily aggregate from
  Open-Meteo provides ``daylight_duration`` but not sunrise/sunset times.
  Renaming makes the semantics honest without requiring a new API call.
"""

from __future__ import annotations

from datetime import date, datetime
from typing import Any
from zoneinfo import ZoneInfo

from pydantic import BaseModel, Field

from butterfly_planner.analysis.weekly_forecast import merge_sunshine_weather
from butterfly_planner.reference.viewing import MIN_GOOD_SUNSHINE_HOURS, MIN_GOOD_SUNSHINE_PCT

# Schema version.  v0.2 = release candidate (structural + hardening).
# Promotion to "1.0" is deferred until a real consumer validates the
# contract end to end.  Bump the major on breaking changes after 1.0.
SCHEMA_VERSION = "0.2"

# Timezone for local display
_PST = ZoneInfo("America/Los_Angeles")

# ---------------------------------------------------------------------------
# WMO code → plain-text description (no emoji).
# Exposed so consumers can build their own labels without re-implementing
# the mapping.  Based on WMO Weather Interpretation Codes as documented by
# https://open-meteo.com/en/docs
# ---------------------------------------------------------------------------
WMO_DESCRIPTIONS: dict[int, str] = {
    0: "Clear",
    1: "Mostly Clear",
    2: "Partly Cloudy",
    3: "Overcast",
    45: "Fog",
    48: "Freezing Fog",
    51: "Light Drizzle",
    53: "Drizzle",
    55: "Heavy Drizzle",
    56: "Light Freezing Drizzle",
    57: "Freezing Drizzle",
    61: "Light Rain",
    63: "Rain",
    65: "Heavy Rain",
    66: "Light Freezing Rain",
    67: "Freezing Rain",
    71: "Light Snow",
    73: "Snow",
    75: "Heavy Snow",
    77: "Snow Grains",
    80: "Light Showers",
    81: "Showers",
    82: "Heavy Showers",
    85: "Light Snow Showers",
    86: "Snow Showers",
    95: "Thunderstorm",
    96: "Thunderstorm with Hail",
    99: "Heavy Thunderstorm",
}


# =============================================================================
# Pydantic models
# =============================================================================


class DailySunshine(BaseModel):
    """Sunshine summary for a single day."""

    today_hours: float = Field(..., description="Measured sunshine hours from 15-min data")
    daylight_hours: float = Field(..., description="Total daylight duration from daily aggregate")
    sunshine_pct: float = Field(..., description="Sunshine as percent of daylight")
    is_good_day: bool = Field(
        ..., description="True when sunshine meets butterfly-viewing thresholds"
    )
    window_start: str = Field(
        ...,
        description="First 15-min daylight slot (HH:MM); approximate day start, not civil sunrise",
    )
    window_end: str = Field(
        ..., description="Last 15-min daylight slot (HH:MM); approximate day end, not civil sunset"
    )
    hourly: list[dict[str, Any]] = Field(
        default_factory=list, description="Per-hour sun_minutes breakdown"
    )


class DailyWeather(BaseModel):
    """Weather summary for a single day (no presentation strings)."""

    high_c: float | None = Field(None, description="Daily high temperature in Celsius")
    low_c: float | None = Field(None, description="Daily low temperature in Celsius")
    precip_mm: float | None = Field(None, description="Total precipitation in mm")
    weather_code: int | None = Field(
        None, description="WMO weather interpretation code; see WMO_DESCRIPTIONS for labels"
    )


class DailyGDD(BaseModel):
    """Growing Degree Days summary."""

    accumulated: float = Field(..., description="Accumulated GDD for the current year to date")
    daily: float = Field(..., description="GDD for this specific day")
    base_temp_f: int = Field(
        ..., description="Base temperature used for GDD calculation (Fahrenheit)"
    )
    year_comparison: str | None = Field(
        None, description="Human-readable comparison to same point last year"
    )


class SpeciesRecord(BaseModel):
    """A butterfly species from recent observations."""

    common_name: str
    scientific_name: str
    observation_count: int
    photo_url: str | None = None


class DailyButterflies(BaseModel):
    """Butterfly observation summary for the recent window."""

    observation_window: dict[str, str] = Field(
        ..., description="Date range of the observations (start/end ISO dates)"
    )
    species_count: int
    top_species: list[SpeciesRecord]
    recent_observations_count: int


class DailyLocation(BaseModel):
    """Location label and coordinates."""

    name: str = Field(..., description="Human-readable location label")
    lat: float = Field(..., description="Latitude")
    lon: float = Field(..., description="Longitude")


class DailyForecastDay(BaseModel):
    """A single future day in the forecast array.

    Fields match the dict produced by ``_extract_forecast``. Sunshine
    fields are absent when no sunshine data is available, hence optional.
    """

    date: str = Field(..., description="ISO date string (YYYY-MM-DD)")
    high_c: float | None = Field(None, description="Daily high temperature in Celsius")
    low_c: float | None = Field(None, description="Daily low temperature in Celsius")
    precip_mm: float | None = Field(None, description="Total precipitation in mm")
    weather_code: int | None = Field(
        None, description="WMO weather interpretation code; see WMO_DESCRIPTIONS"
    )
    sunshine_hours: float | None = Field(None, description="Sunshine hours from daily aggregate")
    daylight_hours: float | None = Field(None, description="Daylight duration in hours")
    sunshine_pct: float | None = Field(None, description="Sunshine as percent of daylight")
    is_good_day: bool = Field(
        ..., description="True when sunshine meets butterfly-viewing thresholds"
    )


class DailyData(BaseModel):
    """Top-level daily data snapshot (v0.2, release candidate).

    This is the single source of truth for the daily-data contract.
    Export the JSON Schema with ``DailyData.model_json_schema()``.
    """

    version: str = Field(..., description="Schema version, e.g. '0.2'")
    date: str = Field(..., description="ISO date string (YYYY-MM-DD)")
    location: DailyLocation = Field(..., description="Location label and coordinates")
    generated_at: str = Field(..., description="ISO datetime when this record was built")
    sunshine: DailySunshine | None = None
    weather: DailyWeather | None = None
    gdd: DailyGDD | None = None
    butterflies: DailyButterflies | None = None
    forecast: list[DailyForecastDay] = Field(
        default_factory=list, description="Next 7 days forecast array"
    )


# =============================================================================
# Extraction functions
# =============================================================================


def build_daily_data(
    weather_data: dict[str, Any] | None = None,
    sunshine_data: dict[str, Any] | None = None,
    inat_data: dict[str, Any] | None = None,
    gdd_data: dict[str, Any] | None = None,
    target_date: date | None = None,
    location_name: str = "Portland, OR",
    lat: float = 45.5,
    lon: float = -122.6,
) -> dict[str, Any]:
    """Build structured daily data from all data sources.

    This is a pure function that extracts and reshapes data for a single day.
    It produces a versioned JSON-serializable dict suitable for file output,
    API responses, or widget consumption.

    The raw extracted dict is validated through ``DailyData`` (Pydantic) and
    the function returns ``DailyData.model_dump(mode="json")``.  Returning a
    plain dict (rather than the model instance) keeps ``today.json`` byte-
    stable: ``model_dump(mode="json")`` emits the same JSON-native primitives
    the hand-built dict did, so existing ``json.dump`` call sites and tests
    that index the result (``result["weather"]["weather_code"]``) keep
    working unchanged.  The validation step is the enforcement gate — a
    schema regression raises ``ValidationError`` here, on the build path.

    Args:
        weather_data: Weather forecast envelope (with ``data.daily`` arrays).
        sunshine_data: Combined sunshine dict with ``today_15min`` and ``daily_16day``.
        inat_data: iNaturalist envelope with ``data.species`` and ``data.observations``.
        gdd_data: GDD envelope with ``data.current_year`` and ``data.previous_year``.
        target_date: Date to extract data for (defaults to today).
        location_name: Human-readable location label.
        lat: Latitude.
        lon: Longitude.

    Returns:
        Validated, JSON-native daily data dict (``DailyData.model_dump(
        mode="json")``) with schema version.
    """
    today = target_date or datetime.now(_PST).date()
    today_str = today.isoformat()
    now = datetime.now(_PST)

    result: dict[str, Any] = {
        "version": SCHEMA_VERSION,
        "date": today_str,
        "location": {"name": location_name, "lat": lat, "lon": lon},
        "generated_at": now.isoformat(),
    }

    result["sunshine"] = _extract_sunshine(sunshine_data, today_str)
    result["weather"] = _extract_weather(weather_data, today_str)
    result["gdd"] = _extract_gdd(gdd_data, today)
    result["butterflies"] = _extract_butterflies(inat_data)
    result["forecast"] = _extract_forecast(weather_data, sunshine_data, today_str)

    # Validate against the contract, then return a plain JSON-native dict.
    # model_dump(mode="json") is byte-stable vs. the hand-built dict.
    return DailyData.model_validate(result).model_dump(mode="json")


def _extract_sunshine(
    sunshine_data: dict[str, Any] | None, today_str: str
) -> dict[str, Any] | None:
    """Extract today's sunshine summary from 15-min and daily data.

    ``window_start``/``window_end`` are the first/last 15-min daylight slots,
    not civil sunrise/sunset.  The daily aggregate from Open-Meteo provides
    ``daylight_duration`` but not actual sunrise/sunset times.
    """
    if not sunshine_data:
        return None

    # --- 15-min data for hourly breakdown ---
    minutely = sunshine_data.get("today_15min", {}).get("minutely_15", {})
    times = minutely.get("time", [])
    durations = minutely.get("sunshine_duration", [])
    is_day = minutely.get("is_day", [])

    # Filter to today's daylight slots
    daylight_slots: list[tuple[str, int]] = []
    for i, t in enumerate(times):
        if t[:10] == today_str and i < len(is_day) and is_day[i]:
            daylight_slots.append((t, durations[i] if i < len(durations) else 0))

    # Hourly aggregation
    hours: dict[int, int] = {}
    for time_str, dur in daylight_slots:
        dt = datetime.fromisoformat(time_str)
        hours.setdefault(dt.hour, 0)
        hours[dt.hour] += dur

    hourly = [{"hour": h, "sun_minutes": round(secs / 60, 1)} for h, secs in sorted(hours.items())]

    total_sun_secs = sum(dur for _, dur in daylight_slots)
    total_sun_hours = total_sun_secs / 3600

    # Window bounds from first/last daylight slot (not civil sunrise/sunset)
    window_start = ""
    window_end = ""
    if daylight_slots:
        start_dt = datetime.fromisoformat(daylight_slots[0][0])
        end_dt = datetime.fromisoformat(daylight_slots[-1][0])
        window_start = start_dt.strftime("%H:%M")
        window_end = end_dt.strftime("%H:%M")

    # --- Daily 16-day data for daylight duration ---
    daily = sunshine_data.get("daily_16day", {}).get("daily", {})
    daily_dates = daily.get("time", [])
    daylight_secs_list = daily.get("daylight_duration", [])
    sunshine_secs_list = daily.get("sunshine_duration", [])

    daylight_hours = 0.0
    sunshine_pct = 0.0
    for i, d in enumerate(daily_dates):
        if d == today_str:
            day_sec = daylight_secs_list[i] if i < len(daylight_secs_list) else 0
            sun_sec = sunshine_secs_list[i] if i < len(sunshine_secs_list) else 0
            daylight_hours = (day_sec or 0) / 3600
            sunshine_pct = (sun_sec / day_sec * 100) if day_sec else 0.0
            if not daylight_slots and sun_sec:
                total_sun_hours = (sun_sec or 0) / 3600
            break

    is_good = total_sun_hours > MIN_GOOD_SUNSHINE_HOURS or sunshine_pct > MIN_GOOD_SUNSHINE_PCT

    return {
        "today_hours": round(total_sun_hours, 1),
        "daylight_hours": round(daylight_hours, 1),
        "sunshine_pct": round(sunshine_pct, 1),
        "is_good_day": is_good,
        "window_start": window_start,
        "window_end": window_end,
        "hourly": hourly,
    }


def _extract_weather(weather_data: dict[str, Any] | None, today_str: str) -> dict[str, Any] | None:
    """Extract today's weather from the forecast data.

    Returns only machine-readable fields; ``conditions`` (the emoji-laden UI
    string) is intentionally omitted.  Consumers should look up
    ``weather_code`` in ``WMO_DESCRIPTIONS``.
    """
    if not weather_data:
        return None

    daily = weather_data.get("data", {}).get("daily", {})
    dates = daily.get("time", [])

    for i, d in enumerate(dates):
        if d == today_str:
            high = daily.get("temperature_2m_max", [None])[i]
            low = daily.get("temperature_2m_min", [None])[i]
            precip = daily.get("precipitation_sum", [None])[i]
            code = daily.get("weather_code", [None])[i]
            return {
                "high_c": high,
                "low_c": low,
                "precip_mm": precip,
                "weather_code": code,
            }

    return None


def _extract_gdd(gdd_data: dict[str, Any] | None, today: date) -> dict[str, Any] | None:
    """Extract today's GDD summary."""
    if not gdd_data:
        return None

    data = gdd_data.get("data", {})
    current = data.get("current_year", {})
    previous = data.get("previous_year", {})
    base_temp = data.get("base_temp_f", 50)

    current_total = current.get("total_gdd", 0)

    daily_gdd = 0.0
    today_str = today.isoformat()
    for entry in current.get("daily", []):
        if entry.get("date") == today_str:
            daily_gdd = entry.get("daily_gdd", 0)
            break

    today_doy = today.timetuple().tm_yday
    previous_at_doy: float | None = None
    for entry in previous.get("daily", []):
        entry_date = date.fromisoformat(entry["date"])
        if entry_date.timetuple().tm_yday >= today_doy:
            previous_at_doy = entry.get("accumulated", 0)
            break

    year_comparison: str | None = None
    if previous_at_doy is not None and previous_at_doy > 0:
        diff = current_total - previous_at_doy
        if abs(diff) / previous_at_doy > 0.05:
            year_comparison = f"{diff:+.0f} GDD {'ahead of' if diff > 0 else 'behind'} last year"
        else:
            year_comparison = "Tracking close to last year"

    return {
        "accumulated": round(current_total, 1),
        "daily": round(daily_gdd, 1),
        "base_temp_f": base_temp,
        "year_comparison": year_comparison,
    }


def _extract_butterflies(
    inat_data: dict[str, Any] | None,
) -> dict[str, Any] | None:
    """Extract butterfly summary from iNaturalist data."""
    if not inat_data:
        return None

    data = inat_data.get("data", {})
    species_list: list[dict[str, Any]] = data.get("species", [])
    observations: list[dict[str, Any]] = data.get("observations", [])

    if not species_list:
        return None

    top_species = sorted(species_list, key=lambda s: s.get("observation_count", 0), reverse=True)[
        :10
    ]

    return {
        "observation_window": {
            "start": data.get("date_start", ""),
            "end": data.get("date_end", ""),
        },
        "species_count": len(species_list),
        "top_species": [
            {
                "common_name": sp.get("common_name", ""),
                "scientific_name": sp.get("scientific_name", ""),
                "observation_count": sp.get("observation_count", 0),
                "photo_url": sp.get("photo_url"),
            }
            for sp in top_species
        ],
        "recent_observations_count": len(observations),
    }


def _extract_forecast(
    weather_data: dict[str, Any] | None,
    sunshine_data: dict[str, Any] | None,
    today_str: str,
) -> list[dict[str, Any]]:
    """Extract multi-day forecast array (excluding today).

    Merges weather and sunshine data into per-day records for the
    next 7 days.  No ``conditions`` field; consumers use ``weather_code``.
    """
    if not weather_data:
        return []

    weather_by_date = merge_sunshine_weather(weather_data)

    sun_daily: dict[str, dict[str, Any]] = {}
    if sunshine_data:
        daily = sunshine_data.get("daily_16day", {}).get("daily", {})
        dates = daily.get("time", [])
        sun_secs = daily.get("sunshine_duration", [])
        day_secs = daily.get("daylight_duration", [])
        for i, d in enumerate(dates):
            sun_sec = sun_secs[i] if i < len(sun_secs) and sun_secs[i] is not None else 0
            day_sec = day_secs[i] if i < len(day_secs) and day_secs[i] is not None else 0
            sun_daily[d] = {
                "sunshine_hours": round(sun_sec / 3600, 1),
                "daylight_hours": round(day_sec / 3600, 1),
                "sunshine_pct": round(sun_sec / day_sec * 100, 1) if day_sec else 0.0,
            }

    forecast: list[dict[str, Any]] = []
    w_daily = weather_data.get("data", {}).get("daily", {})
    dates_list = w_daily.get("time", [])

    for d in dates_list:
        if d <= today_str:
            continue
        if len(forecast) >= 7:
            break

        w = weather_by_date.get(d, {})
        sun = sun_daily.get(d, {})

        entry: dict[str, Any] = {
            "date": d,
            "high_c": w.get("high_c"),
            "low_c": w.get("low_c"),
            "precip_mm": w.get("precip_mm"),
            "weather_code": w.get("weather_code"),
        }
        entry.update(sun)

        is_good = (
            sun.get("sunshine_hours", 0) > MIN_GOOD_SUNSHINE_HOURS
            or sun.get("sunshine_pct", 0) > MIN_GOOD_SUNSHINE_PCT
        )
        entry["is_good_day"] = is_good

        forecast.append(entry)

    return forecast
