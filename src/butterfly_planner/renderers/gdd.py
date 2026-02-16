"""GDD (Growing Degree Days) HTML renderers.

Today's GDD summary card and the accumulated GDD timeline SVG chart.
Imports data types from butterfly_planner.gdd for type annotations.
"""

from __future__ import annotations

from datetime import date
from typing import Any

from butterfly_planner.datasources.gdd import (
    DEFAULT_BASE_TEMP_F,
    DayOfYearStats,
    SpeciesGDDProfile,
)
from butterfly_planner.renderers import render_template

# Month abbreviations for x-axis labels (index 1 = Jan)
_MONTH_ABBREVS = [
    "",
    "Jan",
    "Feb",
    "Mar",
    "Apr",
    "May",
    "Jun",
    "Jul",
    "Aug",
    "Sep",
    "Oct",
    "Nov",
    "Dec",
]


def build_gdd_today_html(gdd_data: dict[str, Any]) -> str:
    """Build the "Today's GDD" card HTML.

    Args:
        gdd_data: Raw GDD data dict (as saved to gdd.json) with 'data' key.

    Returns:
        Rendered HTML string for the GDD today card.
    """
    data = gdd_data.get("data", {})
    current = data.get("current_year", {})
    previous = data.get("previous_year", {})
    base_temp = data.get("base_temp_f", DEFAULT_BASE_TEMP_F)

    current_total = current.get("total_gdd", 0)

    # Find the previous year's accumulated GDD through the same day-of-year
    today = date.today()
    today_doy = today.timetuple().tm_yday
    previous_at_same_doy: float | None = None
    for entry in previous.get("daily", []):
        entry_date = date.fromisoformat(entry["date"])
        if entry_date.timetuple().tm_yday >= today_doy:
            previous_at_same_doy = entry["accumulated"]
            break

    # Date display
    current_daily = current.get("daily", [])
    if current_daily:
        last_entry = current_daily[-1]
        last_date = date.fromisoformat(last_entry["date"])
        current_date_str = last_date.strftime("%B %d, %Y")
    else:
        current_date_str = today.strftime("%B %d, %Y")

    # Status comparison (early/on-track/late relative to last year)
    status_text = ""
    status_pct = 50.0  # center = on track
    if previous_at_same_doy is not None and previous_at_same_doy > 0:
        ratio = current_total / previous_at_same_doy
        diff = current_total - previous_at_same_doy
        if ratio > 1.05:
            status_text = f"{diff:+.0f} GDD ahead of last year"
            status_pct = min(85.0, 50 + (ratio - 1) * 200)
        elif ratio < 0.95:
            status_text = f"{diff:+.0f} GDD behind last year"
            status_pct = max(15.0, 50 + (ratio - 1) * 200)
        else:
            status_text = "Tracking close to last year"

    return render_template(
        "gdd_today.html.j2",
        base_temp=int(base_temp),
        current_gdd=f"{current_total:.0f}",
        current_date=current_date_str,
        previous_gdd=f"{previous_at_same_doy:.0f}" if previous_at_same_doy is not None else None,
        previous_year=previous.get("year", today.year - 1),
        normal_gdd=None,  # Phase 2: will add when normals are computed
        normal_range=None,
        status_text=status_text,
        status_pct=f"{status_pct:.0f}",
    )


def build_gdd_timeline_html(
    gdd_data: dict[str, Any],
    normals: list[DayOfYearStats] | None = None,
    normal_year_range: str = "",
    species_profiles: dict[str, SpeciesGDDProfile] | None = None,
) -> str:
    """Build the GDD timeline SVG chart HTML.

    Renders an SVG showing accumulated GDD curves for the current year,
    previous year, and optionally the 30-year normal band.

    Args:
        gdd_data: Raw GDD data dict with 'data' key.
        normals: Optional list of DayOfYearStats for the normal band.
        normal_year_range: Label for the normal range (e.g. "1996-2025").
        species_profiles: Optional species GDD profiles for threshold markers.

    Returns:
        Rendered HTML string with inline SVG chart.
    """
    data = gdd_data.get("data", {})
    current = data.get("current_year", {})
    previous = data.get("previous_year", {})
    base_temp = data.get("base_temp_f", DEFAULT_BASE_TEMP_F)

    # SVG dimensions
    svg_width = 760
    svg_height = 340
    margin_left = 55
    margin_top = 25
    margin_right = 80  # Space for species labels
    margin_bottom = 30
    plot_right = svg_width - margin_right
    plot_bottom = svg_height - margin_bottom
    plot_width = plot_right - margin_left
    plot_height = plot_bottom - margin_top

    # Determine Y-axis range from all available data
    all_accumulated: list[float] = []
    for entry in current.get("daily", []):
        all_accumulated.append(entry["accumulated"])
    for entry in previous.get("daily", []):
        all_accumulated.append(entry["accumulated"])
    if normals:
        for s in normals:
            all_accumulated.append(s.mean_accumulated + s.stddev)

    y_max = max(all_accumulated) * 1.1 if all_accumulated else 100.0
    y_max = _round_up_nice(y_max)

    def x_for_doy(doy: int) -> float:
        """Convert day-of-year to SVG x coordinate."""
        return margin_left + (doy - 1) / 365.0 * plot_width

    def y_for_gdd(gdd_val: float) -> float:
        """Convert GDD value to SVG y coordinate (inverted)."""
        return plot_bottom - (gdd_val / y_max) * plot_height

    # Y-axis ticks
    n_ticks = 5
    y_ticks = []
    for i in range(n_ticks + 1):
        val = y_max * i / n_ticks
        y_ticks.append({"y": round(y_for_gdd(val), 1), "label": f"{val:.0f}"})

    # X-axis month labels
    x_labels = []
    for month in range(1, 13):
        doy = date(2024, month, 1).timetuple().tm_yday  # Use leap year for even spacing
        x_labels.append({"x": round(x_for_doy(doy), 1), "text": _MONTH_ABBREVS[month]})

    # Build polyline points for current year
    current_year_points = _build_polyline(current.get("daily", []), x_for_doy, y_for_gdd)

    # Build polyline points for previous year
    previous_year_points = _build_polyline(previous.get("daily", []), x_for_doy, y_for_gdd)

    # Build normal band, today marker, and species markers
    normal_band_points, normal_mean_points = _build_normal_band(normals, x_for_doy, y_for_gdd)
    today = date.today()
    today_x = round(x_for_doy(today.timetuple().tm_yday), 1)
    species_markers = _build_species_markers(species_profiles, y_max, y_for_gdd)

    return render_template(
        "gdd_timeline.html.j2",
        base_temp=int(base_temp),
        svg_width=svg_width,
        svg_height=svg_height,
        margin_left=margin_left,
        margin_top=margin_top,
        plot_right=plot_right,
        plot_bottom=plot_bottom,
        y_ticks=y_ticks,
        x_labels=x_labels,
        current_year_points=current_year_points,
        previous_year_points=previous_year_points,
        normal_band_points=normal_band_points,
        normal_mean_points=normal_mean_points,
        today_x=today_x,
        species_markers=species_markers,
        current_year_label=str(current.get("year", today.year)),
        previous_year_label=str(previous.get("year", today.year - 1)),
        normal_range=normal_year_range or None,
    )


def _build_normal_band(
    normals: list[DayOfYearStats] | None,
    x_fn: Any,
    y_fn: Any,
) -> tuple[str, str]:
    """Build SVG polygon (band) and polyline (mean) for GDD normals.

    Returns:
        Tuple of (band_polygon_points, mean_polyline_points) as SVG point strings.
    """
    if not normals:
        return "", ""
    upper_pts = []
    lower_pts = []
    mean_pts = []
    for s in normals:
        x = x_fn(s.doy)
        upper_pts.append(f"{x:.1f},{y_fn(s.mean_accumulated + s.stddev):.1f}")
        lower_pts.append(f"{x:.1f},{y_fn(max(0, s.mean_accumulated - s.stddev)):.1f}")
        mean_pts.append(f"{x:.1f},{y_fn(s.mean_accumulated):.1f}")
    band = " ".join(upper_pts + list(reversed(lower_pts)))
    mean = " ".join(mean_pts)
    return band, mean


def _build_species_markers(
    profiles: dict[str, SpeciesGDDProfile] | None,
    y_max: float,
    y_fn: Any,
) -> list[dict[str, str]]:
    """Build species GDD threshold markers for the timeline SVG."""
    if not profiles:
        return []
    markers = []
    for _name, profile in sorted(profiles.items(), key=lambda kv: kv[1].gdd_median):
        if profile.gdd_median <= y_max:
            markers.append(
                {
                    "y": round(y_fn(profile.gdd_median), 1),
                    "label": profile.common_name,
                    "color": "#666",
                }
            )
    return markers


def _build_polyline(
    daily_entries: list[dict[str, Any]],
    x_fn: Any,
    y_fn: Any,
) -> str:
    """Build SVG polyline points string from daily GDD entries."""
    points = []
    for entry in daily_entries:
        dt = date.fromisoformat(entry["date"])
        doy = dt.timetuple().tm_yday
        x = x_fn(doy)
        y = y_fn(entry["accumulated"])
        points.append(f"{x:.1f},{y:.1f}")
    return " ".join(points)


def _round_up_nice(value: float) -> float:
    """Round a value up to a 'nice' number for axis scaling."""
    if value <= 0:
        return 100.0
    nice_steps = [100, 200, 500, 1000, 1500, 2000, 2500, 3000, 4000, 5000]
    for step in nice_steps:
        if step >= value:
            return float(step)
    return float(int(value / 1000 + 1) * 1000)
