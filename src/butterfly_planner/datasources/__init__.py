"""External data source integrations.

Each subdirectory is one data source (iNaturalist, Open-Meteo weather,
Open-Meteo sunshine). Each has:
  - client.py: Low-level HTTP calls
  - Domain modules: Parsing, aggregation, dataclasses
  - README.md: API docs, rate limits, gotchas

To add a new data source, copy an existing directory and adapt.
"""
