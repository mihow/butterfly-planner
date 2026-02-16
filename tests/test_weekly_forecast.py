"""Tests for the weekly_forecast analysis module."""

from __future__ import annotations

from butterfly_planner.analysis.weekly_forecast import merge_sunshine_weather


class TestMergeSunshineWeather:
    """Test merging weather forecast into date-keyed lookup."""

    def test_basic_merge(self) -> None:
        """Test extracting weather data into date-keyed dict."""
        weather_data = {
            "data": {
                "daily": {
                    "time": ["2026-02-04", "2026-02-05"],
                    "temperature_2m_max": [15.0, 8.0],
                    "temperature_2m_min": [5.0, 2.0],
                    "precipitation_sum": [0.0, 5.2],
                    "weather_code": [0, 61],
                }
            }
        }

        result = merge_sunshine_weather(weather_data)

        assert len(result) == 2
        assert result["2026-02-04"] == {
            "high_c": 15.0,
            "low_c": 5.0,
            "precip_mm": 0.0,
            "weather_code": 0,
        }
        assert result["2026-02-05"] == {
            "high_c": 8.0,
            "low_c": 2.0,
            "precip_mm": 5.2,
            "weather_code": 61,
        }

    def test_none_weather_data(self) -> None:
        """Test with None weather data returns empty dict."""
        result = merge_sunshine_weather(None)
        assert result == {}

    def test_empty_weather_data(self) -> None:
        """Test with empty dict returns empty dict."""
        result = merge_sunshine_weather({})
        assert result == {}

    def test_missing_daily_key(self) -> None:
        """Test with missing daily key returns empty dict."""
        result = merge_sunshine_weather({"data": {}})
        assert result == {}

    def test_missing_optional_arrays(self) -> None:
        """Test with dates but missing weather arrays returns None values."""
        weather_data = {
            "data": {
                "daily": {
                    "time": ["2026-02-04"],
                }
            }
        }

        result = merge_sunshine_weather(weather_data)

        assert len(result) == 1
        assert result["2026-02-04"]["high_c"] is None
        assert result["2026-02-04"]["low_c"] is None
        assert result["2026-02-04"]["precip_mm"] is None
        assert result["2026-02-04"]["weather_code"] is None
