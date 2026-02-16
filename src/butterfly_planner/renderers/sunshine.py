"""Sunshine visualization renderers.

Today's timeline bar and 16-day forecast table. Merges sunshine data
with weather forecast for the combined daily view.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any

from butterfly_planner.renderers import render_template
from butterfly_planner.renderers.weather_utils import wmo_code_to_conditions


def _sunshine_color_class(pct: float) -> str:
    """Return CSS class name for a sunshine percentage (0-100)."""
    if pct == 0:
        return "sunshine-none"
    if pct < 25:
        return "sunshine-low"
    if pct < 50:
        return "sunshine-med"
    if pct < 75:
        return "sunshine-high"
    return "sunshine-full"


def build_sunshine_today_html(sunshine_data: dict[str, Any]) -> str:
    """Build HTML for today's sunshine as a horizontal timeline bar."""
    minutely = sunshine_data["today_15min"].get("minutely_15", {})
    times = minutely.get("time", [])
    durations = minutely.get("sunshine_duration", [])
    is_day = minutely.get("is_day", [])

    if not times:
        return "<p>No 15-minute sunshine data available.</p>"

    today_str = times[0][:10]

    daylight_slots = [
        (times[i], durations[i])
        for i in range(len(times))
        if is_day[i] and times[i][:10] == today_str
    ]

    if not daylight_slots:
        return "<p>No daylight hours in forecast.</p>"

    n_slots = len(daylight_slots)
    total_sunshine_sec = sum(dur for _, dur in daylight_slots)
    total_sunshine_hours = total_sunshine_sec / 3600

    segments = []
    for time_str, duration in daylight_slots:
        dt = datetime.fromisoformat(time_str)
        pct = (duration / 900) * 100
        segments.append(
            {
                "color_class": _sunshine_color_class(pct),
                "title": f"{dt.strftime('%I:%M %p')}: {duration / 60:.0f} min sun",
            }
        )

    labels = []
    seen_hours: set[int] = set()
    for idx, (time_str, _) in enumerate(daylight_slots):
        dt = datetime.fromisoformat(time_str)
        if dt.hour not in seen_hours:
            seen_hours.add(dt.hour)
            labels.append(
                {
                    "left_pct": f"{(idx / n_slots) * 100:.1f}",
                    "text": dt.strftime("%-I%p").lower(),
                }
            )

    sunrise_dt = datetime.fromisoformat(daylight_slots[0][0])
    sunset_dt = datetime.fromisoformat(daylight_slots[-1][0])

    return render_template(
        "sunshine_today.html.j2",
        today_date=sunrise_dt.strftime("%B %d"),
        total_sunshine_hours=f"{total_sunshine_hours:.1f} hours",
        sunrise=sunrise_dt.strftime("%-I:%M %p"),
        sunset=sunset_dt.strftime("%-I:%M %p"),
        labels=labels,
        segments=segments,
    )


def _group_15min_by_date(
    sunshine_data: dict[str, Any],
) -> dict[str, list[tuple[str, int, bool]]]:
    """Group 15-minute sunshine slots by date."""
    minutely = sunshine_data.get("today_15min", {}).get("minutely_15", {})
    times = minutely.get("time", [])
    durations = minutely.get("sunshine_duration", [])
    is_day = minutely.get("is_day", [])

    by_date: dict[str, list[tuple[str, int, bool]]] = {}
    for i, time_str in enumerate(times):
        date_str = time_str[:10]
        by_date.setdefault(date_str, []).append((time_str, durations[i], bool(is_day[i])))
    return by_date


def _build_hourly_bar(slots: list[tuple[str, int, bool]]) -> str:
    """Build an inline hourly sunshine bar from 15-min slot data."""
    daylight = [(t, d) for t, d, is_day in slots if is_day]
    if not daylight:
        return ""

    hours: dict[int, int] = {}
    for time_str, dur in daylight:
        dt = datetime.fromisoformat(time_str)
        hours.setdefault(dt.hour, 0)
        hours[dt.hour] += dur

    if not hours:
        return ""

    first_hour = min(hours)
    last_hour = max(hours)

    segments = []
    for h in range(first_hour, last_hour + 1):
        sun_secs = hours.get(h, 0)
        pct = (sun_secs / 3600) * 100 if sun_secs else 0
        if pct == 0:
            color = "#e8e8e8"
        elif pct < 25:
            color = "#f5eec2"
        elif pct < 50:
            color = "#e8d44d"
        elif pct < 75:
            color = "#d4a017"
        else:
            color = "#b8860b"

        dt_hour = datetime.fromisoformat(daylight[0][0]).replace(hour=h, minute=0)
        title = f"{dt_hour.strftime('%I %p')}: {sun_secs / 60:.0f}min sun"
        segments.append(f'<div class="hour-seg" style="background:{color};" title="{title}"></div>')

    return f'<div class="hour-bar">{"".join(segments)}</div>'


def build_sunshine_16day_html(
    sunshine_data: dict[str, Any], weather_data: dict[str, Any] | None = None
) -> str:
    """Build HTML for the merged 16-day forecast (sunshine + weather)."""
    daily = sunshine_data["daily_16day"].get("daily", {})
    dates = daily.get("time", [])
    sunshine_secs = daily.get("sunshine_duration", [])
    daylight_secs = daily.get("daylight_duration", [])

    if not dates:
        return "<p>No 16-day sunshine data available.</p>"

    weather_by_date: dict[str, dict[str, Any]] = {}
    if weather_data:
        w_daily = weather_data.get("data", {}).get("daily", {})
        w_dates = w_daily.get("time", [])
        for j, w_date in enumerate(w_dates):
            weather_by_date[w_date] = {
                "high_c": w_daily.get("temperature_2m_max", [None])[j],
                "low_c": w_daily.get("temperature_2m_min", [None])[j],
                "precip_mm": w_daily.get("precipitation_sum", [None])[j],
                "weather_code": w_daily.get("weather_code", [None])[j],
            }

    slots_by_date = _group_15min_by_date(sunshine_data)

    rows = []
    for i, date_str in enumerate(dates):
        sun_sec = sunshine_secs[i] if sunshine_secs[i] is not None else 0
        day_sec = daylight_secs[i] if daylight_secs[i] is not None else 0
        sunshine_hours = sun_sec / 3600
        daylight_hours = day_sec / 3600
        sunshine_pct = (sun_sec / day_sec * 100) if day_sec > 0 else 0

        is_good = sunshine_hours > 3.0 or sunshine_pct > 40.0

        day_slots = slots_by_date.get(date_str)
        if day_slots:
            bar = _build_hourly_bar(day_slots)
        else:
            bar_width = int(sunshine_pct * 3)
            bar = f'<div class="sunshine-bar" style="width: {bar_width}px;"></div>'

        w = weather_by_date.get(date_str)
        if w and w["high_c"] is not None:
            temp_cell = (
                f'<span class="temp-high">{w["high_c"]:.0f}\u00b0C</span> / '
                f'<span class="temp-low">{w["low_c"]:.0f}\u00b0C</span>'
            )
            precip_mm = w["precip_mm"] if w["precip_mm"] is not None else 0
            precip_cell = f"{precip_mm:.1f}mm"
        else:
            temp_cell = "\u2014"
            precip_cell = "\u2014"

        if w and w["weather_code"] is not None:
            conditions = wmo_code_to_conditions(w["weather_code"])
        else:
            conditions = "\u2014"

        rows.append(
            {
                "row_class": "good-day" if is_good else "",
                "date": date_str,
                "sunshine_hours": f"{sunshine_hours:.1f}",
                "daylight_hours": f"{daylight_hours:.1f}",
                "sunshine_pct": f"{sunshine_pct:.0f}",
                "bar": bar,
                "temp_cell": temp_cell,
                "precip_cell": precip_cell,
                "conditions": conditions,
            }
        )

    return render_template("sunshine_16day.html.j2", rows=rows)
