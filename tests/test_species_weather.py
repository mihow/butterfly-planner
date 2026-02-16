"""Tests for the species_weather analysis module."""

from __future__ import annotations

from butterfly_planner.analysis.species_weather import enrich_observations_with_weather


class TestEnrichObservationsWithWeather:
    """Test enriching observations with historical weather."""

    def test_matching_dates(self) -> None:
        """Test observations get weather attached for matching dates."""
        observations = [
            {"id": 1, "observed_on": "2024-06-15", "species": "Vanessa cardui"},
            {"id": 2, "observed_on": "2024-06-10", "species": "Pieris rapae"},
        ]
        weather_by_date = {
            "2024-06-15": {"high_c": 22.0, "low_c": 10.0, "precip_mm": 0.0, "weather_code": 0},
            "2024-06-10": {"high_c": 18.0, "low_c": 8.0, "precip_mm": 2.5, "weather_code": 61},
        }

        result = enrich_observations_with_weather(observations, weather_by_date)

        assert len(result) == 2
        assert result[0]["weather"] == weather_by_date["2024-06-15"]
        assert result[1]["weather"] == weather_by_date["2024-06-10"]
        # Original fields preserved
        assert result[0]["id"] == 1
        assert result[0]["species"] == "Vanessa cardui"

    def test_no_matching_date(self) -> None:
        """Test observations without matching weather get None."""
        observations = [
            {"id": 1, "observed_on": "2024-06-15", "species": "Vanessa cardui"},
        ]
        weather_by_date = {
            "2024-06-20": {"high_c": 22.0, "low_c": 10.0, "precip_mm": 0.0, "weather_code": 0},
        }

        result = enrich_observations_with_weather(observations, weather_by_date)

        assert len(result) == 1
        assert result[0]["weather"] is None

    def test_empty_observations(self) -> None:
        """Test with no observations returns empty list."""
        result = enrich_observations_with_weather([], {"2024-06-15": {"high_c": 22.0}})
        assert result == []

    def test_empty_weather(self) -> None:
        """Test with no weather data gives None weather on all observations."""
        observations = [{"id": 1, "observed_on": "2024-06-15"}]
        result = enrich_observations_with_weather(observations, {})

        assert len(result) == 1
        assert result[0]["weather"] is None

    def test_missing_observed_on(self) -> None:
        """Test observation without observed_on gets None weather."""
        observations = [{"id": 1, "species": "Vanessa cardui"}]
        weather_by_date = {
            "2024-06-15": {"high_c": 22.0, "low_c": 10.0, "precip_mm": 0.0, "weather_code": 0},
        }

        result = enrich_observations_with_weather(observations, weather_by_date)

        assert len(result) == 1
        assert result[0]["weather"] is None

    def test_does_not_mutate_originals(self) -> None:
        """Test that original observation dicts are not modified."""
        observations = [{"id": 1, "observed_on": "2024-06-15"}]
        weather_by_date = {
            "2024-06-15": {"high_c": 22.0, "low_c": 10.0, "precip_mm": 0.0, "weather_code": 0},
        }

        enrich_observations_with_weather(observations, weather_by_date)

        assert "weather" not in observations[0]
