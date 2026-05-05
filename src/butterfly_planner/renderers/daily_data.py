"""Structured daily data extraction for multi-consumer use.

Transforms raw API data into a versioned, consumer-friendly JSON format.
The output is independent of both upstream API shapes and downstream HTML
rendering, suitable for widgets, mobile apps, and APIs.

The canonical schema is defined by ``build_daily_data()`` — see the
``docs/daily-data-format-options.md`` planning document for the full spec.
"""

from __future__ import annotations

from datetime import date, datetime
from typing import Any
from zoneinfo import ZoneInfo

from butterfly_planner.analysis.weekly_forecast import merge_sunshine_weather
from butterfly_planner.reference.viewing import MIN_GOOD_SUNSHINE_HOURS, MIN_GOOD_SUNSHINE_PCT
from butterfly_planner.renderers.weather_utils import wmo_code_to_conditions

# Schema version — bump on breaking changes
SCHEMA_VERSION = "1.0"

# Timezone for local display
_PST = ZoneInfo("America/Los_Angeles")


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
        Structured daily data dict with schema version.
    """
    today = target_date or date.today()
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

    return result


def _extract_sunshine(
    sunshine_data: dict[str, Any] | None, today_str: str
) -> dict[str, Any] | None:
    """Extract today's sunshine summary from 15-min and daily data."""
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

    # Sunrise/sunset from first/last daylight slot
    sunrise = ""
    sunset = ""
    if daylight_slots:
        sunrise_dt = datetime.fromisoformat(daylight_slots[0][0])
        sunset_dt = datetime.fromisoformat(daylight_slots[-1][0])
        sunrise = sunrise_dt.strftime("%H:%M")
        sunset = sunset_dt.strftime("%H:%M")

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
            # Prefer daily aggregate sunshine hours if no 15-min data
            if not daylight_slots and sun_sec:
                total_sun_hours = (sun_sec or 0) / 3600
            break

    is_good = total_sun_hours > MIN_GOOD_SUNSHINE_HOURS or sunshine_pct > MIN_GOOD_SUNSHINE_PCT

    return {
        "today_hours": round(total_sun_hours, 1),
        "daylight_hours": round(daylight_hours, 1),
        "sunshine_pct": round(sunshine_pct, 1),
        "is_good_day": is_good,
        "sunrise": sunrise,
        "sunset": sunset,
        "hourly": hourly,
    }


def _extract_weather(weather_data: dict[str, Any] | None, today_str: str) -> dict[str, Any] | None:
    """Extract today's weather from the forecast data."""
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
                "conditions": wmo_code_to_conditions(code) if code is not None else None,
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

    # Find today's daily GDD
    daily_gdd = 0.0
    today_str = today.isoformat()
    for entry in current.get("daily", []):
        if entry.get("date") == today_str:
            daily_gdd = entry.get("daily_gdd", 0)
            break

    # Year comparison
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
    next 7 days.
    """
    if not weather_data:
        return []

    weather_by_date = merge_sunshine_weather(weather_data)

    # Sunshine daily data
    sun_daily = {}
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
    dates = w_daily.get("time", [])

    for d in dates:
        if d <= today_str:
            continue
        if len(forecast) >= 7:
            break

        w = weather_by_date.get(d, {})
        sun = sun_daily.get(d, {})

        code = w.get("weather_code")
        entry: dict[str, Any] = {
            "date": d,
            "high_c": w.get("high_c"),
            "low_c": w.get("low_c"),
            "precip_mm": w.get("precip_mm"),
            "weather_code": code,
            "conditions": wmo_code_to_conditions(code) if code is not None else None,
        }
        entry.update(sun)

        is_good = (
            sun.get("sunshine_hours", 0) > MIN_GOOD_SUNSHINE_HOURS
            or sun.get("sunshine_pct", 0) > MIN_GOOD_SUNSHINE_PCT
        )
        entry["is_good_day"] = is_good

        forecast.append(entry)

    return forecast
