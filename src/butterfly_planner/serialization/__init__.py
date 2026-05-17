"""Serialization package for butterfly planner data contracts.

Produces versioned, consumer-facing JSON artifacts from processed data.
Modules here are data-contract owners: they define Pydantic models, export
JSON Schemas, and implement the extraction logic.

This package is deliberately separate from renderers/ (data → HTML) and
from analysis/ (pure computation).

Modules:
    daily_data: Daily snapshot JSON (v1.0) consumed by widgets and APIs.
"""
