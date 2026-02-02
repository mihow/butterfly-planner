"""
GBIF API integration.

Options:
1. pygbif library (pip install pygbif) - official client
2. Direct API calls - if pygbif doesn't meet needs

API docs: https://www.gbif.org/developer/occurrence

Example:
    from butterfly_planner.services import gbif
    results = gbif.search_occurrences(country="US")
"""

# Taxon keys (GBIF backbone)
LEPIDOPTERA = 797
BUTTERFLIES = 7017  # Papilionoidea

API_BASE = "https://api.gbif.org/v1"


# TODO: Implement occurrence search, name matching, and taxon lookup
