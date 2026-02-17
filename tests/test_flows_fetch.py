"""
Tests for the fetch flow module.
"""

from __future__ import annotations

import json
from datetime import date, datetime
from typing import TYPE_CHECKING
from unittest.mock import Mock, patch

from butterfly_planner.datasources.inaturalist import SpeciesRecord
from butterfly_planner.datasources.inaturalist.observations import ButterflyObservation
from butterfly_planner.datasources.sunshine import DailySunshine, SunshineSlot
from butterfly_planner.flows import fetch
from butterfly_planner.store import DataStore

if TYPE_CHECKING:
    from pathlib import Path

    import pytest


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

        result = fetch.fetch_weather(lat=45.5, lon=-122.6)

        assert "daily" in result
        assert len(result["daily"]["time"]) == 2
        assert result["daily"]["weather_code"] == [0, 61]
        mock_get.assert_called_once()
        call_kwargs = mock_get.call_args.kwargs
        assert call_kwargs["params"]["latitude"] == 45.5
        assert call_kwargs["params"]["longitude"] == -122.6
        assert call_kwargs["params"]["forecast_days"] == 16
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

        result = fetch.fetch_sunshine_15min(lat=45.5, lon=-122.6)

        assert "minutely_15" in result
        assert len(result["minutely_15"]["time"]) == 2
        assert result["minutely_15"]["sunshine_duration"] == [900, 450]
        assert result["minutely_15"]["is_day"] == [1, 1]
        mock_fetch.assert_called_once_with(45.5, -122.6, forecast_days=3)


class TestFetchSunshine16Day:
    """Test fetching 16-day sunshine data."""

    @patch("butterfly_planner.flows.fetch.sunshine.fetch_16day_sunshine")
    def test_fetch_sunshine_16day(self, mock_fetch: Mock) -> None:
        """Test fetching 16-day sunshine data."""
        mock_fetch.return_value = [
            DailySunshine(date=date(2026, 2, 4), sunshine_seconds=14400, daylight_seconds=36000),
            DailySunshine(date=date(2026, 2, 5), sunshine_seconds=10800, daylight_seconds=36000),
        ]

        result = fetch.fetch_sunshine_16day(lat=45.5, lon=-122.6)

        assert "daily" in result
        assert len(result["daily"]["time"]) == 2
        assert result["daily"]["sunshine_duration"] == [14400, 10800]
        assert result["daily"]["daylight_duration"] == [36000, 36000]
        mock_fetch.assert_called_once_with(45.5, -122.6)


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

        result = fetch.save_weather(weather_data)

        assert result == tmp_path / "live" / "weather.json"
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

        result = fetch.save_sunshine(sunshine_15min, sunshine_16day)

        # Returns path to 15-min file (last write)
        assert result == tmp_path / "live" / "sunshine_15min.json"
        assert result.exists()

        saved_15 = json.loads(result.read_text())
        assert saved_15["meta"]["source"] == "open-meteo.com"
        assert saved_15["data"] == sunshine_15min

        # Also writes 16-day file
        path_16 = tmp_path / "live" / "sunshine_16day.json"
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

        result = fetch.fetch_inaturalist()

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

        result = fetch.fetch_inaturalist()

        assert result["species"] == []


class TestFetchInaturalistWeekFiltering:
    """Test that fetch_inaturalist filters observations to target weeks."""

    @patch("butterfly_planner.datasources.inaturalist.weekly.fetch_observations_for_month")
    @patch("butterfly_planner.datasources.inaturalist.weekly.fetch_species_counts")
    def test_observations_outside_target_weeks_are_filtered(
        self, mock_species: Mock, mock_obs: Mock
    ) -> None:
        """Observations whose week-of-year is outside the target window are excluded."""
        mock_species.return_value = []

        # Week 8 of 2024 starts Feb 19; week 12 starts Mar 18
        obs_in_window = ButterflyObservation(
            id=1,
            species="Vanessa cardui",
            common_name="Painted Lady",
            observed_on=date(2024, 2, 20),  # week 8
            latitude=45.5,
            longitude=-122.6,
            quality_grade="research",
            url="https://example.com/1",
        )
        obs_outside_window = ButterflyObservation(
            id=2,
            species="Pieris rapae",
            common_name="Cabbage White",
            observed_on=date(2024, 3, 31),  # week 13 — well outside ±1
            latitude=45.5,
            longitude=-122.6,
            quality_grade="research",
            url="https://example.com/2",
        )
        mock_obs.return_value = [obs_in_window, obs_outside_window]

        # Patch get_current_week_species to control the weeks window
        with patch(
            "butterfly_planner.flows.fetch.inaturalist.get_current_week_species"
        ) as mock_current:
            mock_summary = Mock()
            mock_summary.month = 2
            mock_summary.weeks = [7, 8, 9]
            mock_summary.species = []
            mock_summary.observations = [obs_in_window, obs_outside_window]
            mock_current.return_value = mock_summary

            result = fetch.fetch_inaturalist()

        assert len(result["observations"]) == 1
        assert result["observations"][0]["id"] == 1


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

        result = fetch.save_inaturalist(inat_data)

        assert result == tmp_path / "live" / "inaturalist.json"
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

        result = fetch.fetch_historical_weather(observations)

        assert "2024-06-15" in result
        assert result["2024-06-15"]["high_c"] == 22.0
        assert result["2024-06-15"]["weather_code"] == 0
        assert "2024-06-16" in result
        assert result["2024-06-16"]["precip_mm"] == 1.5
        mock_fetch.assert_called_once_with("2024-06-15", "2024-06-16", 45.5, -122.6)

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

        fetch.fetch_historical_weather(observations)

        assert mock_fetch.call_count == 2

    def test_fetch_historical_weather_no_observations(self) -> None:
        """Test with empty observation list."""
        result = fetch.fetch_historical_weather([])
        assert result == {}


class TestSaveHistoricalWeather:
    """Test saving historical weather cache."""

    def test_save_historical_weather(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test saving historical weather to JSON file."""
        monkeypatch.setattr(fetch, "store", DataStore(tmp_path))

        weather_by_date = {
            "2024-06-15": {"high_c": 22.0, "low_c": 10.0, "precip_mm": 0.0, "weather_code": 0},
        }

        result = fetch.save_historical_weather(weather_by_date)

        assert result == tmp_path / "historical" / "weather" / "historical_weather.json"
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

        result = fetch.fetch_all(lat=45.5, lon=-122.6)

        assert result["weather_days"] == 2
        assert result["sunshine_slots"] == 1
        assert result["inat_species"] == 1
        assert result["current_gdd"] == 150.0

        # Verify files were created at tiered paths
        assert (tmp_path / "live" / "weather.json").exists()
        assert (tmp_path / "live" / "sunshine_15min.json").exists()
        assert (tmp_path / "live" / "sunshine_16day.json").exists()
        assert (tmp_path / "live" / "inaturalist.json").exists()
        assert (tmp_path / "historical" / "weather" / "historical_weather.json").exists()
        assert (tmp_path / "historical" / "gdd" / "gdd.json").exists()
