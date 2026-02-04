"""
iNaturalist API integration.

Options:
1. pyinaturalist library (pip install pyinaturalist) - easy but slow
2. Custom client (port from ebutterfly-taxonomy) - optimized for bulk fetching

API docs: https://api.inaturalist.org/v1/docs/
Rate limits: 1 req/sec, 10k/day (be conservative)

Example:
    from butterfly_planner.services import inat
    obs = inat.get_observations(place_id=inat.OREGON)
"""

# Taxon IDs
LEPIDOPTERA = 47157  # Moths + butterflies
BUTTERFLIES = 47224  # Papilionoidea only

# Place IDs (iNaturalist)
OREGON = 10
WASHINGTON = 46

API_BASE = "https://api.inaturalist.org/v1"


# TODO: Port optimized client from ebutterfly-taxonomy/services/inat.py
# Key functions needed:
# - get_observations(place_id, taxon_id, year) -> paginated results
# - get_species_counts(place_id) -> species list with counts
# - get_taxon(taxon_id) -> taxon details with ancestors
