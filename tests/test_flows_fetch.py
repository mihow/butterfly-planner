"""
Tests for the fetch flow module.
"""

from __future__ import annotations

import dataclasses
import json
from datetime import UTC, date, datetime, timedelta
from typing import TYPE_CHECKING, Any
from unittest.mock import Mock, patch

import pytest

from butterfly_planner.datasources.inaturalist import SpeciesRecord
from butterfly_planner.datasources.inaturalist.observations import ButterflyObservation
from butterfly_planner.datasources.sunshine import DailySunshine, SunshineSlot
from butterfly_planner.flows import fetch
from butterfly_planner.flows.paths import location_paths
from butterfly_planner.reference import geography
from butterfly_planner.reference.geography import PORTLAND, BoundingBox, Location
from butterfly_planner.store import DataStore

if TYPE_CHECKING:
    from pathlib import Path


class TestFetchWeather:
    """Test fetching weather data from API."""

    @patch("butterfly_planner.datasources.weather.forecast.session.get")
    def test_fetch_weather(self, mock_get: Mock) -> None:
        """Test fetching weather data from Open-Meteo."""
        mock_response = Mock()
        mock_response.json.return_value = {
            "daily": {
                "time": ["2026-02-04", "2026-02-05"],
                "temperature_2m_max": [15.0, 18.0],
                "temperature_2m_min": [5.0, 8.0],
                "precipitation_sum": [0, 2.5],
                "weather_code": [0, 61],
            }
        }
        mock_response.raise_for_status = Mock()
        mock_get.return_value = mock_response

        result = fetch.fetch_weather(PORTLAND)

        assert "daily" in result
        assert len(result["daily"]["time"]) == 2
        assert result["daily"]["weather_code"] == [0, 61]
        mock_get.assert_called_once()
        call_kwargs = mock_get.call_args.kwargs
        assert call_kwargs["params"]["latitude"] == 45.5
        assert call_kwargs["params"]["longitude"] == -122.6
        assert call_kwargs["params"]["forecast_days"] == 16
        assert call_kwargs["params"]["timezone"] == "America/Los_Angeles"
        assert "weather_code" in call_kwargs["params"]["daily"]


class TestFetchSunshine15Min:
    """Test fetching 15-minute sunshine data."""

    @patch("butterfly_planner.flows.fetch.sunshine.fetch_today_15min_sunshine")
    def test_fetch_sunshine_15min(self, mock_fetch: Mock) -> None:
        """Test fetching 15-minute sunshine data for 3 days."""
        mock_fetch.return_value = [
            SunshineSlot(time=datetime(2026, 2, 4, 12, 0), duration_seconds=900, is_day=True),
            SunshineSlot(time=datetime(2026, 2, 4, 12, 15), duration_seconds=450, is_day=True),
        ]

        result = fetch.fetch_sunshine_15min(PORTLAND)

        assert "minutely_15" in result
        assert len(result["minutely_15"]["time"]) == 2
        assert result["minutely_15"]["sunshine_duration"] == [900, 450]
        assert result["minutely_15"]["is_day"] == [1, 1]
        mock_fetch.assert_called_once_with(
            45.5, -122.6, timezone="America/Los_Angeles", forecast_days=3
        )


class TestFetchSunshine16Day:
    """Test fetching 16-day sunshine data."""

    @patch("butterfly_planner.flows.fetch.sunshine.fetch_16day_sunshine")
    def test_fetch_sunshine_16day(self, mock_fetch: Mock) -> None:
        """Test fetching 16-day sunshine data."""
        mock_fetch.return_value = [
            DailySunshine(date=date(2026, 2, 4), sunshine_seconds=14400, daylight_seconds=36000),
            DailySunshine(date=date(2026, 2, 5), sunshine_seconds=10800, daylight_seconds=36000),
        ]

        result = fetch.fetch_sunshine_16day(PORTLAND)

        assert "daily" in result
        assert len(result["daily"]["time"]) == 2
        assert result["daily"]["sunshine_duration"] == [14400, 10800]
        assert result["daily"]["daylight_duration"] == [36000, 36000]
        mock_fetch.assert_called_once_with(45.5, -122.6, timezone="America/Los_Angeles")


class TestSaveWeather:
    """Test saving weather data to file."""

    def test_save_weather(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test saving weather data to JSON file."""
        monkeypatch.setattr(fetch, "store", DataStore(tmp_path))

        weather_data = {
            "daily": {
                "time": ["2026-02-04"],
                "temperature_2m_max": [15.0],
            }
        }

        result = fetch.save_weather(weather_data, PORTLAND)

        assert result == tmp_path / "live" / "portland" / "weather.json"
        assert result.exists()

        saved_data = json.loads(result.read_text())
        assert saved_data["meta"]["source"] == "open-meteo.com"
        assert "fetched_at" in saved_data["meta"]
        assert "valid_until" in saved_data["meta"]
        assert saved_data["data"] == weather_data


class TestSaveSunshine:
    """Test saving sunshine data to file."""

    def test_save_sunshine(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test saving 15-minute sunshine data to JSON file."""
        monkeypatch.setattr(fetch, "store", DataStore(tmp_path))

        sunshine_15min = {
            "minutely_15": {
                "time": ["2026-02-04T12:00"],
                "sunshine_duration": [900],
                "is_day": [1],
            }
        }
        sunshine_16day = {
            "daily": {
                "time": ["2026-02-04"],
                "sunshine_duration": [14400],
                "daylight_duration": [36000],
            }
        }

        result = fetch.save_sunshine(sunshine_15min, sunshine_16day, PORTLAND)

        # Returns path to 15-min file (last write)
        assert result == tmp_path / "live" / "portland" / "sunshine_15min.json"
        assert result.exists()

        saved_15 = json.loads(result.read_text())
        assert saved_15["meta"]["source"] == "open-meteo.com"
        assert saved_15["data"] == sunshine_15min

        # Also writes 16-day file
        path_16 = tmp_path / "live" / "portland" / "sunshine_16day.json"
        assert path_16.exists()
        saved_16 = json.loads(path_16.read_text())
        assert saved_16["data"] == sunshine_16day


class TestFetchInaturalist:
    """Test fetching iNaturalist data."""

    @patch("butterfly_planner.datasources.inaturalist.weekly.fetch_observations_for_month")
    @patch("butterfly_planner.datasources.inaturalist.weekly.fetch_species_counts")
    def test_fetch_inaturalist(self, mock_fetch: Mock, mock_obs: Mock) -> None:
        """Test fetching iNaturalist species counts."""
        mock_fetch.return_value = [
            SpeciesRecord(
                taxon_id=48662,
                scientific_name="Vanessa cardui",
                common_name="Painted Lady",
                rank="species",
                observation_count=542,
                photo_url="https://example.com/photo.jpg",
                taxon_url="https://www.inaturalist.org/taxa/48662",
            ),
        ]
        mock_obs.return_value = []

        result = fetch.fetch_inaturalist(PORTLAND)

        assert "month" in result
        assert "species" in result
        assert len(result["species"]) == 1
        assert result["species"][0]["scientific_name"] == "Vanessa cardui"
        assert result["species"][0]["observation_count"] == 542

    @patch("butterfly_planner.datasources.inaturalist.weekly.fetch_observations_for_month")
    @patch("butterfly_planner.datasources.inaturalist.weekly.fetch_species_counts")
    def test_fetch_inaturalist_empty(self, mock_fetch: Mock, mock_obs: Mock) -> None:
        """Test fetching with no species found."""
        mock_fetch.return_value = []
        mock_obs.return_value = []

        result = fetch.fetch_inaturalist(PORTLAND)

        assert result["species"] == []


class TestFetchInaturalistDateFiltering:
    """Test that fetch_inaturalist filters observations to 14 days back / 7 days ahead."""

    def test_observations_outside_date_window_are_filtered(self) -> None:
        """Observations whose month-day is outside the window are excluded."""
        # Pin today to Feb 17 2026
        today = date(2026, 2, 17)

        obs_in_window = ButterflyObservation(
            id=1,
            species="Vanessa cardui",
            common_name="Painted Lady",
            observed_on=date(2024, 2, 15),  # Feb 15 — within window
            latitude=45.5,
            longitude=-122.6,
            quality_grade="research",
            url="https://example.com/1",
        )
        obs_outside_window = ButterflyObservation(
            id=2,
            species="Pieris rapae",
            common_name="Cabbage White",
            observed_on=date(2024, 3, 31),  # Mar 31 — well outside window
            latitude=45.5,
            longitude=-122.6,
            quality_grade="research",
            url="https://example.com/2",
        )

        with patch(
            "butterfly_planner.flows.fetch.inaturalist.get_current_week_species"
        ) as mock_current:
            mock_summary = Mock()
            mock_summary.month = 2
            mock_summary.weeks = [7, 8, 9]
            mock_summary.species = []
            mock_summary.observations = [obs_in_window, obs_outside_window]
            mock_current.return_value = mock_summary

            result = fetch.fetch_inaturalist(PORTLAND, today=today)

        assert len(result["observations"]) == 1
        assert result["observations"][0]["id"] == 1
        assert result["date_start"] == "2026-02-03"
        assert result["date_end"] == "2026-02-24"

    def test_year_boundary_in_window(self) -> None:
        """Observations from late Dec are included when today is early Jan."""
        # Pin today to Jan 3 2026 — window is Dec 20 to Jan 10
        today = date(2026, 1, 3)

        obs_dec = ButterflyObservation(
            id=10,
            species="Vanessa cardui",
            common_name="Painted Lady",
            observed_on=date(2023, 12, 25),  # Dec 25 — inside window
            latitude=45.5,
            longitude=-122.6,
            quality_grade="research",
            url="https://example.com/10",
        )
        obs_jan = ButterflyObservation(
            id=11,
            species="Vanessa cardui",
            common_name="Painted Lady",
            observed_on=date(2024, 1, 5),  # Jan 5 — inside window
            latitude=45.5,
            longitude=-122.6,
            quality_grade="research",
            url="https://example.com/11",
        )
        obs_outside = ButterflyObservation(
            id=12,
            species="Pieris rapae",
            common_name="Cabbage White",
            observed_on=date(2024, 2, 15),  # Feb 15 — outside window
            latitude=45.5,
            longitude=-122.6,
            quality_grade="research",
            url="https://example.com/12",
        )

        with patch(
            "butterfly_planner.flows.fetch.inaturalist.get_current_week_species"
        ) as mock_current:
            mock_summary = Mock()
            mock_summary.month = 1
            mock_summary.weeks = [1, 2, 52]
            mock_summary.species = []
            mock_summary.observations = [obs_dec, obs_jan, obs_outside]
            mock_current.return_value = mock_summary

            result = fetch.fetch_inaturalist(PORTLAND, today=today)

        obs_ids = [o["id"] for o in result["observations"]]
        assert 10 in obs_ids  # Dec 25
        assert 11 in obs_ids  # Jan 5
        assert 12 not in obs_ids  # Feb 15


class TestSaveInaturalist:
    """Test saving iNaturalist data to file."""

    def test_save_inaturalist(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test saving iNaturalist data to JSON file."""
        monkeypatch.setattr(fetch, "store", DataStore(tmp_path))

        inat_data = {
            "month": 2,
            "species": [
                {
                    "taxon_id": 48662,
                    "scientific_name": "Vanessa cardui",
                    "common_name": "Painted Lady",
                    "rank": "species",
                    "observation_count": 542,
                }
            ],
        }

        result = fetch.save_inaturalist(inat_data, PORTLAND)

        assert result == tmp_path / "live" / "portland" / "inaturalist.json"
        assert result.exists()

        saved_data = json.loads(result.read_text())
        assert saved_data["meta"]["source"] == "inaturalist.org"
        assert "fetched_at" in saved_data["meta"]
        assert saved_data["data"] == inat_data


class TestFetchHistoricalWeather:
    """Test fetching historical weather for observation dates."""

    @patch("butterfly_planner.flows.fetch.weather_historical.fetch_historical_daily")
    def test_fetch_historical_weather(self, mock_fetch: Mock) -> None:
        """Test fetching historical weather groups by year and returns by-date dict."""
        mock_fetch.return_value = {
            "daily": {
                "time": ["2024-06-15", "2024-06-16"],
                "temperature_2m_max": [22.0, 24.0],
                "temperature_2m_min": [10.0, 12.0],
                "precipitation_sum": [0.0, 1.5],
                "weather_code": [0, 3],
            }
        }

        observations = [
            {"observed_on": "2024-06-15", "latitude": 45.5, "longitude": -122.6},
            {"observed_on": "2024-06-16", "latitude": 45.6, "longitude": -122.7},
        ]

        result = fetch.fetch_historical_weather(observations, PORTLAND)

        assert "2024-06-15" in result
        assert result["2024-06-15"]["high_c"] == 22.0
        assert result["2024-06-15"]["weather_code"] == 0
        assert "2024-06-16" in result
        assert result["2024-06-16"]["precip_mm"] == 1.5
        mock_fetch.assert_called_once_with(
            "2024-06-15", "2024-06-16", 45.5, -122.6, timezone="America/Los_Angeles"
        )

    @patch("butterfly_planner.flows.fetch.weather_historical.fetch_historical_daily")
    def test_fetch_historical_weather_multiple_years(self, mock_fetch: Mock) -> None:
        """Test that observations from different years make separate API calls."""
        mock_fetch.return_value = {
            "daily": {
                "time": ["2024-06-15"],
                "temperature_2m_max": [20.0],
                "temperature_2m_min": [10.0],
                "precipitation_sum": [0.0],
                "weather_code": [1],
            }
        }

        observations = [
            {"observed_on": "2024-06-15"},
            {"observed_on": "2023-06-10"},
        ]

        fetch.fetch_historical_weather(observations, PORTLAND)

        assert mock_fetch.call_count == 2

    def test_fetch_historical_weather_no_observations(self) -> None:
        """Test with empty observation list."""
        result = fetch.fetch_historical_weather([], PORTLAND)
        assert result == {}


class TestSaveHistoricalWeather:
    """Test saving historical weather cache."""

    def test_save_historical_weather(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test saving historical weather to JSON file."""
        monkeypatch.setattr(fetch, "store", DataStore(tmp_path))

        weather_by_date = {
            "2024-06-15": {"high_c": 22.0, "low_c": 10.0, "precip_mm": 0.0, "weather_code": 0},
        }

        result = fetch.save_historical_weather(weather_by_date, PORTLAND)

        assert (
            result == tmp_path / "historical" / "portland" / "weather" / "historical_weather.json"
        )
        assert result.exists()

        saved_data = json.loads(result.read_text())
        assert saved_data["meta"]["source"] == "open-meteo.com (archive)"
        assert "fetched_at" in saved_data["meta"]
        assert saved_data["data"]["by_date"]["2024-06-15"]["high_c"] == 22.0


class TestFetchAllFlow:
    """Test the main fetch flow."""

    @patch("butterfly_planner.flows.fetch.gdd.fetch_year_gdd")
    @patch("butterfly_planner.flows.fetch.weather_historical.fetch_historical_daily")
    @patch("butterfly_planner.datasources.inaturalist.weekly.fetch_observations_for_month")
    @patch("butterfly_planner.datasources.inaturalist.weekly.fetch_species_counts")
    @patch("butterfly_planner.flows.fetch.sunshine.fetch_today_15min_sunshine")
    @patch("butterfly_planner.flows.fetch.sunshine.fetch_16day_sunshine")
    @patch("butterfly_planner.datasources.weather.forecast.session.get")
    def test_fetch_all(
        self,
        mock_get: Mock,
        mock_fetch_16day: Mock,
        mock_fetch_15min: Mock,
        mock_fetch_inat: Mock,
        mock_fetch_inat_obs: Mock,
        mock_fetch_hist: Mock,
        mock_fetch_gdd: Mock,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """Test fetching all data sources."""
        monkeypatch.setattr(fetch, "store", DataStore(tmp_path))

        # Mock weather API
        mock_response = Mock()
        mock_response.json.return_value = {
            "daily": {
                "time": ["2026-02-04", "2026-02-05"],
                "temperature_2m_max": [15.0, 18.0],
                "temperature_2m_min": [5.0, 8.0],
                "precipitation_sum": [0, 2.5],
                "weather_code": [0, 61],
            }
        }
        mock_response.raise_for_status = Mock()
        mock_get.return_value = mock_response

        # Mock sunshine functions
        mock_fetch_15min.return_value = [
            SunshineSlot(time=datetime(2026, 2, 4, 12, 0), duration_seconds=900, is_day=True),
        ]
        mock_fetch_16day.return_value = [
            DailySunshine(date=date(2026, 2, 4), sunshine_seconds=14400, daylight_seconds=36000),
        ]

        # Mock iNaturalist
        mock_fetch_inat_obs.return_value = []
        mock_fetch_inat.return_value = [
            SpeciesRecord(
                taxon_id=48662,
                scientific_name="Vanessa cardui",
                common_name="Painted Lady",
                rank="species",
                observation_count=542,
            ),
        ]

        # Mock historical weather (empty -- no observations have dates)
        mock_fetch_hist.return_value = {
            "daily": {
                "time": [],
                "temperature_2m_max": [],
                "temperature_2m_min": [],
                "precipitation_sum": [],
                "weather_code": [],
            }
        }

        # Mock GDD fetch
        mock_gdd_result = Mock()
        mock_gdd_result.total_gdd = 150.0
        mock_gdd_result.daily = []
        mock_fetch_gdd.return_value = mock_gdd_result

        # gdd.year_gdd_to_dict needs to handle the mock
        monkeypatch.setattr(
            fetch.gdd,
            "year_gdd_to_dict",
            lambda result: {"total_gdd": result.total_gdd, "daily": []},
        )

        result = fetch.fetch_all("portland")

        assert result["weather_days"] == 2
        assert result["sunshine_slots"] == 1
        assert result["inat_species"] == 1
        assert result["current_gdd"] == 150.0

        # Verify files were created at tiered paths
        assert (tmp_path / "live" / "portland" / "weather.json").exists()
        assert (tmp_path / "live" / "portland" / "sunshine_15min.json").exists()
        assert (tmp_path / "live" / "portland" / "sunshine_16day.json").exists()
        assert (tmp_path / "live" / "portland" / "inaturalist.json").exists()
        assert (
            tmp_path / "historical" / "portland" / "weather" / "historical_weather.json"
        ).exists()
        assert (tmp_path / "historical" / "portland" / "gdd" / "gdd.json").exists()


# A second location built only for these tests, so they do not depend on
# which locations are registered. Its bbox, point and timezone all differ
# from Portland's, so a call made with the wrong location is visible.
OTHER = dataclasses.replace(
    PORTLAND,
    slug="otherplace",
    name="Other Place",
    lat=31.4,
    lon=-109.9,
    bbox=BoundingBox(swlat=31.0, swlng=-110.5, nelat=32.0, nelng=-109.0),
    timezone="America/Phoenix",
    site_subdir="otherplace",
)


class TestLocalToday:
    """The local date follows the location's timezone, not the runner's."""

    def test_phoenix_is_a_day_ahead_of_los_angeles_at_this_instant(self) -> None:
        now = datetime(2026, 1, 10, 7, 30, tzinfo=UTC)
        assert fetch.local_today("America/Phoenix", now=now) == date(2026, 1, 10)
        assert fetch.local_today("America/Los_Angeles", now=now) == date(2026, 1, 9)


class TestFetchTasksUseLocation:
    """Each fetch task sends the location's own point, box and timezone."""

    def test_inaturalist_uses_bbox_and_local_today(self) -> None:
        summary = Mock(month=1, weeks=[1, 2, 3], species=[], observations=[])
        with (
            patch.object(
                fetch.inaturalist, "get_current_week_species", return_value=summary
            ) as mock_current,
            patch.object(fetch, "local_today", return_value=date(2026, 1, 10)) as mock_today,
        ):
            result = fetch.fetch_inaturalist(OTHER)

        mock_today.assert_called_once_with("America/Phoenix")
        mock_current.assert_called_once_with(bbox=OTHER.bbox.as_dict(), today=date(2026, 1, 10))
        assert mock_current.call_args.kwargs["bbox"]["swlat"] == 31.0
        assert result["date_start"] == "2025-12-27"

    def test_gdd_uses_point_timezone_and_local_year(self) -> None:
        with (
            patch.object(fetch.gdd, "fetch_year_gdd") as mock_year,
            patch.object(fetch.gdd, "year_gdd_to_dict", return_value={}),
            patch.object(fetch, "local_today", return_value=date(2026, 1, 1)),
        ):
            result = fetch.fetch_gdd(OTHER)

        years = [c.args[2] for c in mock_year.call_args_list]
        assert years == [2026, 2025]
        for c in mock_year.call_args_list:
            assert c.args[:2] == (31.4, -109.9)
            assert c.kwargs["timezone"] == "America/Phoenix"
        assert result["location"] == {"slug": "otherplace", "lat": 31.4, "lon": -109.9}

    def test_historical_weather_uses_point_and_timezone(self) -> None:
        with patch.object(
            fetch.weather_historical, "fetch_historical_daily", return_value={"daily": {}}
        ) as mock_hist:
            fetch.fetch_historical_weather([{"observed_on": "2024-06-15"}], OTHER)

        mock_hist.assert_called_once_with(
            "2024-06-15", "2024-06-15", 31.4, -109.9, timezone="America/Phoenix"
        )

    def test_save_records_location_slug(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setattr(fetch, "store", DataStore(tmp_path))

        path = fetch.save_weather({"daily": {}}, OTHER)

        assert path == tmp_path / "live" / "otherplace" / "weather.json"
        meta = json.loads(path.read_text())["meta"]
        assert meta["params"]["location"] == "otherplace"


def _mock_datasources(monkeypatch: pytest.MonkeyPatch) -> dict[str, Mock]:
    """Replace every external call the fetch flow makes with a mock."""
    mocks = {
        "forecast": Mock(return_value={"daily": {"time": ["2026-01-10"]}}),
        "sun_15min": Mock(
            return_value=[
                SunshineSlot(time=datetime(2026, 1, 10, 12, 0), duration_seconds=900, is_day=True)
            ]
        ),
        "sun_16day": Mock(
            return_value=[
                DailySunshine(date=date(2026, 1, 10), sunshine_seconds=3600, daylight_seconds=36000)
            ]
        ),
        "inat": Mock(return_value=Mock(month=1, weeks=[1, 2, 3], species=[], observations=[])),
        "historical": Mock(return_value={"daily": {}}),
        "gdd_year": Mock(return_value=Mock(total_gdd=10.0)),
    }
    monkeypatch.setattr(fetch.weather_forecast, "fetch_forecast", mocks["forecast"])
    monkeypatch.setattr(fetch.sunshine, "fetch_today_15min_sunshine", mocks["sun_15min"])
    monkeypatch.setattr(fetch.sunshine, "fetch_16day_sunshine", mocks["sun_16day"])
    monkeypatch.setattr(fetch.inaturalist, "get_current_week_species", mocks["inat"])
    monkeypatch.setattr(fetch.weather_historical, "fetch_historical_daily", mocks["historical"])
    monkeypatch.setattr(fetch.gdd, "fetch_year_gdd", mocks["gdd_year"])
    monkeypatch.setattr(
        fetch.gdd, "year_gdd_to_dict", lambda r: {"total_gdd": r.total_gdd, "daily": []}
    )
    return mocks


def _write_fresh_cache(store: DataStore, loc: Location) -> None:
    """Write a still-valid cache file for every source of ``loc``."""
    paths = location_paths(loc)
    valid = datetime.now(UTC) + timedelta(hours=6)
    for path in (
        paths.weather,
        paths.sunshine_15min,
        paths.sunshine_16day,
        paths.inaturalist,
        paths.historical_weather,
        paths.gdd,
    ):
        store.write(path, {"cached_for": loc.slug}, source="test", valid_until=valid)


class TestFetchAllLocations:
    """Fetching several locations keeps their data and failures apart."""

    def test_second_location_is_fetched_and_portland_cache_is_untouched(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        store = DataStore(tmp_path)
        monkeypatch.setattr(fetch, "store", store)
        monkeypatch.setitem(geography.LOCATIONS, OTHER.slug, OTHER)
        _write_fresh_cache(store, PORTLAND)
        portland_files = {p: p.read_bytes() for p in (tmp_path / "live" / "portland").iterdir()}
        portland_files |= {
            p: p.read_bytes() for p in (tmp_path / "historical" / "portland").rglob("*.json")
        }
        mocks = _mock_datasources(monkeypatch)

        results = fetch.fetch_all_locations()

        assert set(results) == {"portland", "otherplace"}
        assert "error" not in results["otherplace"]
        # Portland was fresh, so every external call was for the other location.
        mocks["forecast"].assert_called_once()
        assert mocks["forecast"].call_args.args == (31.4, -109.9)
        assert mocks["forecast"].call_args.kwargs["timezone"] == "America/Phoenix"
        assert mocks["sun_15min"].call_args.kwargs["timezone"] == "America/Phoenix"
        assert mocks["sun_16day"].call_args.kwargs["timezone"] == "America/Phoenix"
        mocks["inat"].assert_called_once()
        assert mocks["inat"].call_args.kwargs["bbox"] == OTHER.bbox.as_dict()
        assert {p: p.read_bytes() for p in portland_files} == portland_files
        assert (tmp_path / "live" / "otherplace" / "weather.json").exists()
        assert (tmp_path / "historical" / "otherplace" / "gdd" / "gdd.json").exists()

    def test_one_location_failing_does_not_stop_the_others(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
    ) -> None:
        monkeypatch.setattr(fetch, "store", DataStore(tmp_path))
        monkeypatch.setitem(geography.LOCATIONS, OTHER.slug, OTHER)
        _mock_datasources(monkeypatch)
        real_fetch_weather = fetch.fetch_weather

        def fetch_weather(loc: Location) -> dict[str, Any]:
            if loc.slug == OTHER.slug:
                raise RuntimeError("weather service down")
            return real_fetch_weather.fn(loc)

        monkeypatch.setattr(fetch, "fetch_weather", fetch_weather)

        results = fetch.fetch_all_locations()

        assert "weather service down" in results["otherplace"]["error"]
        warnings = [
            line for line in capsys.readouterr().err.splitlines() if line.startswith("::warning::")
        ]
        assert warnings == [
            "::warning::Fetching otherplace failed: RuntimeError('weather service down')"
        ]
        assert "error" not in results["portland"]
        assert (tmp_path / "live" / "portland" / "weather.json").exists()
        assert (tmp_path / "historical" / "portland" / "gdd" / "gdd.json").exists()


class TestMain:
    """The fetch script fails the job only when no location could be fetched."""

    @pytest.mark.parametrize(
        ("results", "expected"),
        [
            ({"portland": {"weather_days": 16}, "otherplace": {"weather_days": 16}}, 0),
            ({"portland": {"weather_days": 16}, "otherplace": {"error": "boom"}}, 0),
            ({"portland": {"error": "boom"}, "otherplace": {"error": "boom"}}, 1),
        ],
    )
    def test_exit_code(self, results: dict[str, dict[str, Any]], expected: int) -> None:
        with patch.object(fetch, "fetch_all_locations", return_value=results):
            assert fetch.main() == expected
