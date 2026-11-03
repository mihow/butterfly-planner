"""Tests that the sightings renderers draw the location they are given.

Each published site describes one location. The map view, search rectangle,
search label, points of interest and iNaturalist links must all come from
that location, so a second site never shows the first site's area.
"""

from __future__ import annotations

import dataclasses
import json
import re

from butterfly_planner.reference.geography import (
    PORTLAND,
    BoundingBox,
    PointOfInterest,
)
from butterfly_planner.renderers.sightings_map import build_butterfly_map_html
from butterfly_planner.renderers.sightings_table import build_butterfly_sightings_html

TEST_AREA = dataclasses.replace(
    PORTLAND,
    slug="testarea",
    name="Test Town, AZ",
    region_label="Test Canyon & Hills",
    lat=31.4,
    lon=-109.9,
    bbox=BoundingBox(swlat=31.33, swlng=-110.45, nelat=32.05, nelng=-109.05),
    timezone="America/Phoenix",
    map_center=(31.69, -109.75),
    map_zoom=9,
    site_subdir="testarea",
    points_of_interest=(
        PointOfInterest(
            name="Test Refuge",
            lat=31.637,
            lon=-109.4816,
            url="https://example.org/refuge",
        ),
    ),
)

INAT_DATA: dict = {
    "data": {
        "month": 6,
        "date_start": "2026-06-01",
        "date_end": "2026-06-15",
        "species": [
            {
                "taxon_id": 48662,
                "scientific_name": "Vanessa cardui",
                "common_name": "Painted Lady",
                "observation_count": 3,
            }
        ],
        "observations": [
            {
                "id": 1,
                "species": "Vanessa cardui",
                "common_name": "Painted Lady",
                "observed_on": "2026-06-10",
                "latitude": 31.6,
                "longitude": -109.6,
                "url": "https://www.inaturalist.org/observations/1",
                "photo_url": None,
            }
        ],
    }
}


def _pois_json(map_script: str) -> list[dict]:
    match = re.search(r"var pois\s*=\s*(\[.*?\]);", map_script, re.DOTALL)
    assert match, "points of interest array not found in map script"
    return json.loads(match.group(1))


class TestMapUsesLocation:
    def test_view_rectangle_and_label_come_from_location(self) -> None:
        map_div, map_script = build_butterfly_map_html(INAT_DATA, location=TEST_AREA)

        assert "setView([31.69, -109.75], 9)" in map_script
        assert "L.rectangle([[31.33, -110.45], [32.05, -109.05]]" in map_script
        assert '"Test Canyon \\u0026 Hills"' in map_script
        assert "Test Canyon &amp; Hills" in map_div

    def test_no_portland_values_leak(self) -> None:
        map_div, map_script = build_butterfly_map_html(INAT_DATA, location=TEST_AREA)

        for text in (map_div, map_script):
            assert "44.5" not in text
            assert "Oregon" not in text

    def test_points_of_interest_are_drawn(self) -> None:
        _, map_script = build_butterfly_map_html(INAT_DATA, location=TEST_AREA)

        assert _pois_json(map_script) == [
            {
                "name": "Test Refuge",
                "lat": 31.637,
                "lon": -109.4816,
                "url": "https://example.org/refuge",
            }
        ]

    def test_no_points_of_interest_means_no_marker_code(self) -> None:
        _, map_script = build_butterfly_map_html(INAT_DATA, location=PORTLAND)

        assert "var pois" not in map_script

    def test_portland_output_is_unchanged(self) -> None:
        map_div, map_script = build_butterfly_map_html(INAT_DATA, location=PORTLAND)

        assert "setView([45.5, -122.8], 8)" in map_script
        assert "L.rectangle([[44.5, -124.2], [46.5, -121.5]]" in map_script
        assert "'Search area: ' + \"NW Oregon / SW Washington\"" in map_script
        assert "NW Oregon / SW Washington" in map_div


class TestTableUsesLocation:
    def test_links_and_label_come_from_location(self) -> None:
        html = build_butterfly_sightings_html(INAT_DATA, location=TEST_AREA)

        assert "swlat=31.33&amp;swlng=-110.45&amp;nelat=32.05&amp;nelng=-109.05" in html
        assert "Test Canyon &amp; Hills" in html
        assert "swlat=44.5" not in html
        assert "Oregon" not in html

    def test_portland_output_is_unchanged(self) -> None:
        html = build_butterfly_sightings_html(INAT_DATA, location=PORTLAND)

        assert "swlat=44.5" in html
        assert "NW Oregon / SW Washington" in html
