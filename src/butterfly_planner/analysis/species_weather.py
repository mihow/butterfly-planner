"""Join butterfly observations with historical weather records.

Matches weather data to observations by date, producing enriched
observation dicts that renderers can consume directly.
"""

from __future__ import annotations

from typing import Any


def enrich_observations_with_weather(
    observations: list[dict[str, Any]],
    weather_by_date: dict[str, dict[str, Any]],
) -> list[dict[str, Any]]:
    """Attach historical weather data to observations by date.

    For each observation, looks up the weather record for its ``observed_on``
    date and adds a ``"weather"`` key with the matched record (or None).

    Args:
        observations: List of observation dicts with ``observed_on`` date strings.
        weather_by_date: Mapping of ISO date string -> weather dict
            (keys: ``high_c``, ``low_c``, ``precip_mm``, ``weather_code``).

    Returns:
        New list of observation dicts, each with an added ``"weather"`` key.
    """
    enriched: list[dict[str, Any]] = []
    for obs in observations:
        obs_date = obs.get("observed_on", "")
        weather = weather_by_date.get(obs_date) if obs_date else None
        enriched.append({**obs, "weather": weather})
    return enriched
