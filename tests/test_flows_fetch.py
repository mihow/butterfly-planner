"""
Tests for the fetch flow module.
"""

from __future__ import annotations

import json
from datetime import date, datetime
from typing import TYPE_CHECKING
from unittest.mock import Mock, patch

from butterfly_planner.flows import fetch
from butterfly_planner.inaturalist import SpeciesRecord
from butterfly_planner.sunshine import DailySunshine, SunshineSlot

if TYPE_CHECKING:
    from pathlib import Path

    import pytest


class TestFetchWeather:
    """Test fetching weather data from API."""

    @patch("butterfly_planner.flows.fetch.requests.get")
    def test_fetch_weather(self, mock_get: Mock) -> None:
        """Test fetching weather data from Open-Meteo."""
        mock_response = Mock()
        mock_response.json.return_value = {
            "daily": {
                "time": ["2026-02-04", "2026-02-05"],
                "temperature_2m_max": [15.0, 18.0],
                "temperature_2m_min": [5.0, 8.0],
                "precipitation_sum": [0, 2.5],
            }
        }
        mock_response.raise_for_status = Mock()
        mock_get.return_value = mock_response

        result = fetch.fetch_weather(lat=45.5, lon=-122.6)

        assert "daily" in result
        assert len(result["daily"]["time"]) == 2
        mock_get.assert_called_once()
        call_kwargs = mock_get.call_args.kwargs
        assert call_kwargs["params"]["latitude"] == 45.5
        assert call_kwargs["params"]["longitude"] == -122.6


class TestFetchSunshine15Min:
    """Test fetching 15-minute sunshine data."""

    @patch("butterfly_planner.flows.fetch.sunshine.fetch_today_15min_sunshine")
    def test_fetch_sunshine_15min(self, mock_fetch: Mock) -> None:
        """Test fetching 15-minute sunshine data."""
        mock_fetch.return_value = [
            SunshineSlot(time=datetime(2026, 2, 4, 12, 0), duration_seconds=900, is_day=True),
            SunshineSlot(time=datetime(2026, 2, 4, 12, 15), duration_seconds=450, is_day=True),
        ]

        result = fetch.fetch_sunshine_15min(lat=45.5, lon=-122.6)

        assert "minutely_15" in result
        assert len(result["minutely_15"]["time"]) == 2
        assert result["minutely_15"]["sunshine_duration"] == [900, 450]
        assert result["minutely_15"]["is_day"] == [1, 1]
        mock_fetch.assert_called_once_with(45.5, -122.6)


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
        raw_dir = tmp_path / "data" / "raw"
        monkeypatch.setattr(fetch, "RAW_DIR", raw_dir)

        weather_data = {
            "daily": {
                "time": ["2026-02-04"],
                "temperature_2m_max": [15.0],
            }
        }

        result = fetch.save_weather(weather_data)

        assert result == raw_dir / "weather.json"
        assert result.exists()

        saved_data = json.loads(result.read_text())
        assert "fetched_at" in saved_data
        assert saved_data["source"] == "open-meteo.com"
        assert saved_data["data"] == weather_data


class TestSaveSunshine:
    """Test saving sunshine data to file."""

    def test_save_sunshine(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test saving sunshine data to JSON file."""
        raw_dir = tmp_path / "data" / "raw"
        monkeypatch.setattr(fetch, "RAW_DIR", raw_dir)

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

        assert result == raw_dir / "sunshine.json"
        assert result.exists()

        saved_data = json.loads(result.read_text())
        assert "fetched_at" in saved_data
        assert saved_data["source"] == "open-meteo.com"
        assert saved_data["today_15min"] == sunshine_15min
        assert saved_data["daily_16day"] == sunshine_16day


class TestFetchInaturalist:
    """Test fetching iNaturalist data."""

    @patch("butterfly_planner.flows.fetch.inaturalist.fetch_species_counts")
    def test_fetch_inaturalist(self, mock_fetch: Mock) -> None:
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

        result = fetch.fetch_inaturalist()

        assert "month" in result
        assert "species" in result
        assert len(result["species"]) == 1
        assert result["species"][0]["scientific_name"] == "Vanessa cardui"
        assert result["species"][0]["observation_count"] == 542

    @patch("butterfly_planner.flows.fetch.inaturalist.fetch_species_counts")
    def test_fetch_inaturalist_empty(self, mock_fetch: Mock) -> None:
        """Test fetching with no species found."""
        mock_fetch.return_value = []

        result = fetch.fetch_inaturalist()

        assert result["species"] == []


class TestSaveInaturalist:
    """Test saving iNaturalist data to file."""

    def test_save_inaturalist(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test saving iNaturalist data to JSON file."""
        raw_dir = tmp_path / "data" / "raw"
        monkeypatch.setattr(fetch, "RAW_DIR", raw_dir)

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

        assert result == raw_dir / "inaturalist.json"
        assert result.exists()

        saved_data = json.loads(result.read_text())
        assert "fetched_at" in saved_data
        assert saved_data["source"] == "inaturalist.org"
        assert saved_data["data"] == inat_data


class TestFetchAllFlow:
    """Test the main fetch flow."""

    @patch("butterfly_planner.flows.fetch.inaturalist.fetch_species_counts")
    @patch("butterfly_planner.flows.fetch.sunshine.fetch_today_15min_sunshine")
    @patch("butterfly_planner.flows.fetch.sunshine.fetch_16day_sunshine")
    @patch("butterfly_planner.flows.fetch.requests.get")
    def test_fetch_all(
        self,
        mock_get: Mock,
        mock_fetch_16day: Mock,
        mock_fetch_15min: Mock,
        mock_fetch_inat: Mock,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """Test fetching all data sources."""
        raw_dir = tmp_path / "data" / "raw"
        monkeypatch.setattr(fetch, "RAW_DIR", raw_dir)

        # Mock weather API
        mock_response = Mock()
        mock_response.json.return_value = {
            "daily": {
                "time": ["2026-02-04", "2026-02-05"],
                "temperature_2m_max": [15.0, 18.0],
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
        mock_fetch_inat.return_value = [
            SpeciesRecord(
                taxon_id=48662,
                scientific_name="Vanessa cardui",
                common_name="Painted Lady",
                rank="species",
                observation_count=542,
            ),
        ]

        result = fetch.fetch_all(lat=45.5, lon=-122.6)

        assert result["weather_days"] == 2
        assert result["sunshine_slots"] == 1
        assert result["inat_species"] == 1
        assert "weather" in result["outputs"]
        assert "sunshine" in result["outputs"]
        assert "inaturalist" in result["outputs"]

        # Verify files were created
        assert (raw_dir / "weather.json").exists()
        assert (raw_dir / "sunshine.json").exists()
        assert (raw_dir / "inaturalist.json").exists()
