"""Tests for the forecast location registry and bounding boxes."""

from __future__ import annotations

from zoneinfo import ZoneInfo

import pytest

from butterfly_planner.datasources.inaturalist.client import NW_OREGON_SW_WASHINGTON
from butterfly_planner.reference.geography import (
    DEFAULT_LOCATION,
    LOCATIONS,
    PORTLAND,
    TARGET_REGION_BBOX,
    BoundingBox,
    get_location,
)


class TestBoundingBox:
    """Tests for BoundingBox helpers."""

    def test_as_dict_returns_inat_query_keys(self) -> None:
        bbox = BoundingBox(swlat=1.0, swlng=2.0, nelat=3.0, nelng=4.0)
        assert bbox.as_dict() == {"swlat": 1.0, "swlng": 2.0, "nelat": 3.0, "nelng": 4.0}

    def test_contains_inside_and_outside(self) -> None:
        bbox = BoundingBox(swlat=10.0, swlng=-20.0, nelat=12.0, nelng=-18.0)
        assert bbox.contains(11.0, -19.0)
        assert not bbox.contains(13.0, -19.0)
        assert not bbox.contains(11.0, -17.0)

    def test_center_is_midpoint(self) -> None:
        bbox = BoundingBox(swlat=10.0, swlng=-20.0, nelat=12.0, nelng=-18.0)
        assert bbox.center == (11.0, -19.0)

    def test_leaflet_bounds_are_sw_then_ne(self) -> None:
        bbox = BoundingBox(swlat=10.0, swlng=-20.0, nelat=12.0, nelng=-18.0)
        assert bbox.leaflet_bounds == [[10.0, -20.0], [12.0, -18.0]]


class TestLocationRegistry:
    """Invariants every registered location must satisfy."""

    def test_slugs_match_keys_and_are_unique(self) -> None:
        assert all(slug == loc.slug for slug, loc in LOCATIONS.items())

    def test_site_subdirs_unique_and_one_at_root(self) -> None:
        subdirs = [loc.site_subdir for loc in LOCATIONS.values()]
        assert len(subdirs) == len(set(subdirs))
        assert subdirs.count("") == 1

    def test_default_location_is_registered_at_site_root(self) -> None:
        assert LOCATIONS[DEFAULT_LOCATION.slug] is DEFAULT_LOCATION
        assert DEFAULT_LOCATION.site_subdir == ""

    @pytest.mark.parametrize("location", list(LOCATIONS.values()), ids=lambda loc: loc.slug)
    def test_bbox_corners_are_ordered(self, location) -> None:
        assert location.bbox.swlat < location.bbox.nelat
        assert location.bbox.swlng < location.bbox.nelng

    @pytest.mark.parametrize("location", list(LOCATIONS.values()), ids=lambda loc: loc.slug)
    def test_timezone_resolves(self, location) -> None:
        ZoneInfo(location.timezone)

    @pytest.mark.parametrize("location", list(LOCATIONS.values()), ids=lambda loc: loc.slug)
    def test_bbox_contains_weather_point_and_map_center(self, location) -> None:
        assert location.bbox.contains(location.lat, location.lon)
        assert location.bbox.contains(*location.map_center)

    @pytest.mark.parametrize("location", list(LOCATIONS.values()), ids=lambda loc: loc.slug)
    def test_bbox_contains_points_of_interest(self, location) -> None:
        for poi in location.points_of_interest:
            assert location.bbox.contains(poi.lat, poi.lon), poi.name


class TestPortland:
    """Portland keeps the values the site used before locations existed."""

    def test_portland_values_unchanged(self) -> None:
        assert PORTLAND.bbox == BoundingBox(swlat=44.5, swlng=-124.2, nelat=46.5, nelng=-121.5)
        assert (PORTLAND.lat, PORTLAND.lon) == (45.5, -122.6)
        assert PORTLAND.timezone == "America/Los_Angeles"
        assert PORTLAND.map_center == (45.5, -122.8)
        assert PORTLAND.map_zoom == 8

    def test_target_region_alias_is_portland_bbox(self) -> None:
        assert TARGET_REGION_BBOX is PORTLAND.bbox

    def test_inat_default_area_matches_portland_bbox(self) -> None:
        assert PORTLAND.bbox.as_dict() == NW_OREGON_SW_WASHINGTON


class TestGetLocation:
    """Tests for looking up a location by slug."""

    def test_known_slug(self) -> None:
        assert get_location("portland") is PORTLAND

    def test_unknown_slug_lists_valid_slugs(self) -> None:
        with pytest.raises(KeyError, match="portland"):
            get_location("nope")
