"""Tests for building one static page per location.

Each location is published as its own page: the default location at the
site root and every other location in its own subdirectory. The pages link
to each other with relative links, so the same build works at the site root
and under a preview prefix. A location without data is skipped and left out
of the links, so no page links to a page that was not built.
"""

from __future__ import annotations

import dataclasses
import json
from typing import TYPE_CHECKING

import pytest

from butterfly_planner.flows import build
from butterfly_planner.reference.geography import BISBEE, PORTLAND, BoundingBox

if TYPE_CHECKING:
    from pathlib import Path

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
)

OTHER_AREA = dataclasses.replace(TEST_AREA, slug="other", name="Other, AZ", site_subdir="other")

WEATHER_PAYLOAD = {
    "daily": {
        "time": ["2026-07-04"],
        "temperature_2m_max": [30.0],
        "temperature_2m_min": [15.0],
        "precipitation_sum": [0],
        "weather_code": [0],
    }
}


def _weather_envelope(fetched_at: str) -> dict[str, object]:
    return {"fetched_at": fetched_at, "source": "open-meteo.com", "data": WEATHER_PAYLOAD}


def _seed_weather(base: Path, slug: str) -> None:
    path = base / "live" / slug / "weather.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    envelope = {
        "meta": {"source": "open-meteo.com", "fetched_at": "2026-07-04T19:30:00+00:00"},
        "data": WEATHER_PAYLOAD,
    }
    path.write_text(json.dumps(envelope))


class TestLocationNav:
    """``location_nav`` gives each page relative links to every page."""

    LOCATIONS = (PORTLAND, TEST_AREA, OTHER_AREA)

    def _hrefs(self, current: object) -> dict[str, str]:
        nav = build.location_nav(current, self.LOCATIONS)  # type: ignore[arg-type]
        return {item["slug"]: item["href"] for item in nav}

    def test_root_page_links_down_into_subdirectories(self) -> None:
        hrefs = self._hrefs(PORTLAND)
        assert hrefs == {"portland": "./", "testarea": "testarea/", "other": "other/"}

    def test_subdirectory_page_links_up_to_root_and_across(self) -> None:
        hrefs = self._hrefs(TEST_AREA)
        assert hrefs == {"portland": "../", "testarea": "./", "other": "../other/"}

    def test_marks_only_the_current_location(self) -> None:
        nav = build.location_nav(TEST_AREA, self.LOCATIONS)
        assert [item["current"] for item in nav] == [False, True, False]
        assert [item["name"] for item in nav] == ["Portland, OR", "Test Town, AZ", "Other, AZ"]


class TestBuildHtmlForLocation:
    """The page header names the location and its local time zone."""

    def test_header_names_location_and_derived_timezone(self) -> None:
        html = build.build_html.fn(
            _weather_envelope("2026-07-04T19:30:00+00:00"), None, loc=TEST_AREA
        )
        assert "<title>Butterfly Planner &mdash; Test Town, AZ</title>" in html
        assert "Last updated 2026-07-04 12:30 MST" in html
        assert "Portland" not in html
        assert "Oregon" not in html

    def test_portland_summer_time_is_labelled_pdt(self) -> None:
        html = build.build_html.fn(
            _weather_envelope("2026-07-04T19:30:00+00:00"), None, loc=PORTLAND
        )
        assert "Last updated 2026-07-04 12:30 PDT" in html

    def test_portland_winter_time_is_labelled_pst(self) -> None:
        html = build.build_html.fn(
            _weather_envelope("2026-02-04T20:00:00+00:00"), None, loc=PORTLAND
        )
        assert "Last updated 2026-02-04 12:00 PST" in html

    def test_no_nav_for_a_single_location(self) -> None:
        nav = build.location_nav(PORTLAND, [PORTLAND])
        html = build.build_html.fn(
            _weather_envelope("2026-07-04T19:30:00+00:00"), None, loc=PORTLAND, nav=nav
        )
        assert 'class="locations"' not in html

    def test_nav_links_with_current_page_marked(self) -> None:
        nav = build.location_nav(TEST_AREA, [PORTLAND, TEST_AREA])
        html = build.build_html.fn(
            _weather_envelope("2026-07-04T19:30:00+00:00"), None, loc=TEST_AREA, nav=nav
        )
        assert '<nav class="locations"' in html
        assert '<a href="../">Portland, OR</a>' in html
        assert '<span aria-current="page">Test Town, AZ</span>' in html


class TestWriteSiteSubdirectory:
    """A location's page is written to its own subdirectory."""

    def test_write_site_creates_subdirectory(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setattr(build, "SITE_DIR", tmp_path / "site")
        out = build.write_site.fn("<html></html>", build.location_paths(TEST_AREA))
        assert out == tmp_path / "site" / "testarea" / "index.html"
        assert out.read_text() == "<html></html>"


class TestBuildAllLocations:
    """``build_all_locations`` builds every location that has data."""

    @pytest.fixture
    def store(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> build.DataStore:
        ds = build.DataStore(tmp_path)
        monkeypatch.setattr(build, "store", ds)
        monkeypatch.setattr(build, "SITE_DIR", ds.derived / "site")
        monkeypatch.setattr(build, "LOCATIONS", {"portland": PORTLAND, "testarea": TEST_AREA})
        return ds

    def test_builds_one_linked_page_per_location(self, store: build.DataStore) -> None:
        _seed_weather(store.base, "portland")
        _seed_weather(store.base, "testarea")

        result = build.build_all_locations()

        assert result["pages"] == 2
        site = store.derived / "site"
        root_html = (site / "index.html").read_text()
        sub_html = (site / "testarea" / "index.html").read_text()
        assert '<a href="testarea/">Test Town, AZ</a>' in root_html
        assert '<span aria-current="page">Portland, OR</span>' in root_html
        assert '<a href="../">Portland, OR</a>' in sub_html
        assert "Test Town, AZ" in sub_html

        daily = store.derived / "daily"
        portland_today = json.loads((daily / "portland" / "today.json").read_text())
        area_today = json.loads((daily / "testarea" / "today.json").read_text())
        assert portland_today["location"]["name"] == "Portland, OR"
        assert area_today["location"]["name"] == "Test Town, AZ"
        assert area_today["location"]["lat"] == pytest.approx(31.4)
        assert (daily / "daily-data.schema.json").exists()

    def test_location_without_data_is_skipped_and_not_linked(self, store: build.DataStore) -> None:
        _seed_weather(store.base, "portland")

        result = build.build_all_locations()

        assert result["pages"] == 1
        assert result["locations"]["testarea"] == {"error": "no data"}
        site = store.derived / "site"
        root_html = (site / "index.html").read_text()
        assert not (site / "testarea").exists()
        assert "testarea/" not in root_html
        assert 'class="locations"' not in root_html


BISBEE_INAT = {
    "month": 8,
    "weeks": [31, 32, 33],
    "date_start": "2026-08-01",
    "date_end": "2026-08-15",
    "species": [
        {
            "taxon_id": 48662,
            "scientific_name": "Vanessa cardui",
            "common_name": "Painted Lady",
            "rank": "species",
            "observation_count": 12,
            "photo_url": None,
            "taxon_url": "https://www.inaturalist.org/taxa/48662",
        },
    ],
    "observations": [
        {
            "id": 1,
            "species": "Vanessa cardui",
            "common_name": "Painted Lady",
            "observed_on": "2025-08-10",
            "latitude": 31.64,
            "longitude": -109.48,
            "quality_grade": "research",
            "url": "https://www.inaturalist.org/observations/1",
            "photo_url": None,
        },
    ],
}


class TestBisbeePage:
    """The registered Bisbee location builds a page about Bisbee only."""

    @pytest.fixture
    def store(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> build.DataStore:
        ds = build.DataStore(tmp_path)
        monkeypatch.setattr(build, "store", ds)
        monkeypatch.setattr(build, "SITE_DIR", ds.derived / "site")
        return ds

    def test_bisbee_page_and_daily_data(self, store: build.DataStore) -> None:
        _seed_weather(store.base, "portland")
        _seed_weather(store.base, "bisbee")
        inat_path = store.base / "live" / "bisbee" / "inaturalist.json"
        inat_path.write_text(
            json.dumps({"meta": {"source": "inaturalist.org"}, "data": BISBEE_INAT})
        )

        result = build.build_all_locations()

        assert result["pages"] == 2
        html = (store.derived / "site" / "bisbee" / "index.html").read_text()
        assert "Bisbee, AZ" in html
        assert "MST" in html
        assert "31.33" in html
        assert "Leslie Canyon" in html
        assert "Portland" not in html.replace('<a href="../">Portland, OR</a>', "")
        assert "NW Oregon" not in html

        today = json.loads((store.derived / "daily" / "bisbee" / "today.json").read_text())
        assert today["location"]["name"] == "Bisbee, AZ"
        assert BISBEE.slug in result["locations"]
