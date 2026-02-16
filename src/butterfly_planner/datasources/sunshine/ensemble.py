"""Ensemble sunshine forecast from Open-Meteo Ensemble API."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from butterfly_planner.datasources.sunshine.models import EnsembleSunshine
from butterfly_planner.services.http import session

ENSEMBLE_API = "https://ensemble-api.open-meteo.com/v1/ensemble"


def fetch_ensemble_sunshine(
    lat: float, lon: float, timezone: str = "America/Los_Angeles", forecast_days: int = 7
) -> list[EnsembleSunshine]:
    """
    Fetch ensemble sunshine forecast for confidence analysis.

    This provides uncertainty estimates by running multiple weather model variations.

    Args:
        lat: Latitude
        lon: Longitude
        timezone: Timezone name
        forecast_days: Number of days (max 35 for ensemble)

    Returns:
        List of EnsembleSunshine objects with hourly forecasts

    Note:
        Ensemble API counts as ~4x API calls due to computational cost.
        Use sparingly.
    """
    params: dict[str, str | int | float] = {
        "latitude": lat,
        "longitude": lon,
        "hourly": "sunshine_duration",
        "models": "gfs_seamless",  # 31 ensemble members
        "timezone": timezone,
        "forecast_days": forecast_days,
    }

    resp = session.get(ENSEMBLE_API, params=params, timeout=60)
    resp.raise_for_status()
    data: dict[str, Any] = resp.json()

    # Parse ensemble response
    hourly = data.get("hourly", {})
    times = hourly.get("time", [])

    # Extract all member data
    # Keys are like: sunshine_duration_member00, sunshine_duration_member01, ...
    member_keys = [k for k in hourly if k.startswith("sunshine_duration_member")]
    member_keys.sort()  # Ensure consistent ordering

    forecasts = []
    for i, time_str in enumerate(times):
        dt = datetime.fromisoformat(time_str)
        member_values = [hourly[key][i] for key in member_keys]
        forecasts.append(EnsembleSunshine(time=dt, member_values=member_values))

    return forecasts
