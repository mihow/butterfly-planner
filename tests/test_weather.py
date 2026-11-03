"""Tests for the Open-Meteo weather request builders."""

from __future__ import annotations

from unittest.mock import patch

from butterfly_planner.datasources.weather.forecast import fetch_forecast
from butterfly_planner.datasources.weather.historical import fetch_historical_daily


class TestFetchForecastTimezone:
    """fetch_forecast sends the requested timezone to Open-Meteo."""

    @patch("butterfly_planner.datasources.weather.forecast.session.get")
    def test_passes_given_timezone(self, mock_get) -> None:
        fetch_forecast(31.4482, -109.9284, timezone="America/Phoenix")
        assert mock_get.call_args.kwargs["params"]["timezone"] == "America/Phoenix"

    @patch("butterfly_planner.datasources.weather.forecast.session.get")
    def test_defaults_to_pacific(self, mock_get) -> None:
        fetch_forecast()
        assert mock_get.call_args.kwargs["params"]["timezone"] == "America/Los_Angeles"


class TestFetchHistoricalTimezone:
    """fetch_historical_daily sends the requested timezone to Open-Meteo."""

    @patch("butterfly_planner.datasources.weather.historical.session.get")
    def test_passes_given_timezone(self, mock_get) -> None:
        fetch_historical_daily(
            "2025-01-01", "2025-01-31", 31.4482, -109.9284, timezone="America/Phoenix"
        )
        assert mock_get.call_args.kwargs["params"]["timezone"] == "America/Phoenix"

    @patch("butterfly_planner.datasources.weather.historical.session.get")
    def test_defaults_to_pacific(self, mock_get) -> None:
        fetch_historical_daily("2025-01-01", "2025-01-31")
        assert mock_get.call_args.kwargs["params"]["timezone"] == "America/Los_Angeles"
