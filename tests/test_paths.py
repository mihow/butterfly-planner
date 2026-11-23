"""Tests for per-location cache and site paths."""

from __future__ import annotations

import dataclasses
from pathlib import Path

from butterfly_planner.flows.paths import LocationPaths, location_paths
from butterfly_planner.reference.geography import PORTLAND

# A second location built only for these tests, so they do not depend on
# which locations are registered.
OTHER = dataclasses.replace(PORTLAND, slug="otherplace", site_subdir="otherplace")


def _all_paths(paths: LocationPaths) -> list[Path]:
    return [getattr(paths, f.name) for f in dataclasses.fields(paths)]


class TestLocationPaths:
    """The cache layout keeps each location's files apart."""

    def test_two_locations_share_no_paths(self) -> None:
        assert set(_all_paths(location_paths(PORTLAND))).isdisjoint(
            _all_paths(location_paths(OTHER))
        )

    def test_every_cache_path_contains_the_slug(self) -> None:
        paths = location_paths(OTHER)
        for field in dataclasses.fields(paths):
            if field.name == "site_file":
                continue
            assert "otherplace" in getattr(paths, field.name).parts, field.name

    def test_cache_layout(self) -> None:
        paths = location_paths(PORTLAND)
        assert paths.weather == Path("live/portland/weather.json")
        assert paths.sunshine_15min == Path("live/portland/sunshine_15min.json")
        assert paths.sunshine_16day == Path("live/portland/sunshine_16day.json")
        assert paths.inaturalist == Path("live/portland/inaturalist.json")
        assert paths.historical_weather == Path(
            "historical/portland/weather/historical_weather.json"
        )
        assert paths.gdd == Path("historical/portland/gdd/gdd.json")
        assert paths.daily_dir == Path("daily/portland")

    def test_portland_site_file_is_the_site_root(self) -> None:
        assert location_paths(PORTLAND).site_file == Path("index.html")

    def test_subdir_location_site_file(self) -> None:
        assert location_paths(OTHER).site_file == Path("otherplace/index.html")
