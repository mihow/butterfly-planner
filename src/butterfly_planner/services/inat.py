"""
iNaturalist API client.

Low-level HTTP client for the iNaturalist API v1.
Handles rate limiting, request building, and pagination helpers.

API docs: https://api.inaturalist.org/v1/docs/
Rate limits: ~1 req/sec, 10k/day
Recommended practices: https://www.inaturalist.org/pages/api+recommended+practices
"""

from __future__ import annotations

import time
from typing import Any

from butterfly_planner.services.http import session

# ---------------------------------------------------------------------------
# Taxon IDs
# ---------------------------------------------------------------------------
LEPIDOPTERA = 47157  # Moths + butterflies (order)
BUTTERFLIES = 47224  # Papilionoidea (superfamily — butterflies only)

# ---------------------------------------------------------------------------
# Place IDs (iNaturalist)
# ---------------------------------------------------------------------------
OREGON = 10
WASHINGTON = 46

# ---------------------------------------------------------------------------
# API configuration
# ---------------------------------------------------------------------------
API_BASE = "https://api.inaturalist.org/v1"
MAX_PER_PAGE = 200  # API maximum for /observations
MAX_RESULTS = 10_000  # API hard ceiling per query

# ---------------------------------------------------------------------------
# Rate limiting (module-level state)
# ---------------------------------------------------------------------------
_last_request_time: float = 0.0
MIN_REQUEST_INTERVAL: float = 1.1  # seconds — stay safely under 1 req/s


def _rate_limit() -> None:
    """Sleep if needed to honour the ~1 req/s rate limit."""
    global _last_request_time  # noqa: PLW0603
    now = time.monotonic()
    elapsed = now - _last_request_time
    if elapsed < MIN_REQUEST_INTERVAL:
        time.sleep(MIN_REQUEST_INTERVAL - elapsed)
    _last_request_time = time.monotonic()


def _get(endpoint: str, params: dict[str, Any] | None = None) -> dict[str, Any]:
    """Make a rate-limited GET request to the iNaturalist API v1."""
    _rate_limit()
    url = f"{API_BASE}/{endpoint}"
    resp = session.get(url, params=params or {})
    resp.raise_for_status()
    data: dict[str, Any] = resp.json()
    return data


# ---------------------------------------------------------------------------
# Public helpers
# ---------------------------------------------------------------------------


def get_observations(params: dict[str, Any]) -> dict[str, Any]:
    """GET /observations — search observations."""
    return _get("observations", params)


def get_species_counts(params: dict[str, Any]) -> dict[str, Any]:
    """GET /observations/species_counts — species with observation counts."""
    return _get("observations/species_counts", params)


def get_histogram(params: dict[str, Any]) -> dict[str, Any]:
    """GET /observations/histogram — observation counts bucketed by time."""
    return _get("observations/histogram", params)


def get_observations_paginated(
    params: dict[str, Any],
    *,
    max_pages: int = 5,
) -> list[dict[str, Any]]:
    """
    Fetch observations with automatic pagination via ``id_above``.

    Uses the recommended ``id_above`` + ``order_by=id`` + ``order=asc``
    strategy to page through results without hitting the 10k ceiling.

    Returns a flat list of observation dicts (``results`` concatenated).
    """
    page_params = {
        **params,
        "order_by": "id",
        "order": "asc",
        "per_page": MAX_PER_PAGE,
    }
    all_results: list[dict[str, Any]] = []
    for _ in range(max_pages):
        data = get_observations(page_params)
        results: list[dict[str, Any]] = data.get("results", [])
        if not results:
            break
        all_results.extend(results)
        # Use last observation ID to page forward
        last_id = results[-1]["id"]
        page_params["id_above"] = last_id
    return all_results
