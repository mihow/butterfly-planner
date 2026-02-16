"""Cross-datasource joins, correlations, and composite indexes.

Each module combines outputs from 2+ datasources into enriched structures
that renderers can consume directly. This is the domain logic layer.

Dependency rule: analysis/ imports from datasources/ models only.
It never fetches data or produces HTML.

Modules:
  - species_gdd: observations + GDD accumulation -> emergence profiles
"""
