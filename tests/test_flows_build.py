"""
Tests for the build flow module.
"""

from __future__ import annotations

import json
from typing import TYPE_CHECKING

import pytest

from butterfly_planner.flows import build

if TYPE_CHECKING:
    from pathlib import Path


class TestCelsiusToFahrenheit:
    """Test temperature conversion."""

    @pytest.mark.parametrize(
        ("celsius", "fahrenheit"),
        [(0, 32.0), (100, 212.0), (-40, -40.0)],
    )
    def test_c_to_f(self, celsius: float, fahrenheit: float) -> None:
        """Test Celsius to Fahrenheit conversion."""
        assert build.c_to_f(celsius) == fahrenheit


class TestLoadWeather:
    """Test loading weather data from file."""

    def test_load_weather_exists(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test loading weather data when file exists."""
        raw_dir = tmp_path / "data" / "raw"
        raw_dir.mkdir(parents=True)
        weather_file = raw_dir / "weather.json"
        weather_data = {"fetched_at": "2026-02-04T12:00:00", "data": {"daily": {}}}
        weather_file.write_text(json.dumps(weather_data))

        monkeypatch.setattr(build, "RAW_DIR", raw_dir)

        result = build.load_weather()
        assert result == weather_data

    def test_load_weather_not_exists(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test loading weather data when file doesn't exist."""
        raw_dir = tmp_path / "data" / "raw"
        raw_dir.mkdir(parents=True)
        monkeypatch.setattr(build, "RAW_DIR", raw_dir)

        result = build.load_weather()
        assert result is None


class TestLoadSunshine:
    """Test loading sunshine data from file."""

    def test_load_sunshine_exists(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test loading sunshine data when file exists."""
        raw_dir = tmp_path / "data" / "raw"
        raw_dir.mkdir(parents=True)
        sunshine_file = raw_dir / "sunshine.json"
        sunshine_data = {"fetched_at": "2026-02-04T12:00:00", "today_15min": {}, "daily_16day": {}}
        sunshine_file.write_text(json.dumps(sunshine_data))

        monkeypatch.setattr(build, "RAW_DIR", raw_dir)

        result = build.load_sunshine()
        assert result == sunshine_data

    def test_load_sunshine_not_exists(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Test loading sunshine data when file doesn't exist."""
        raw_dir = tmp_path / "data" / "raw"
        raw_dir.mkdir(parents=True)
        monkeypatch.setattr(build, "RAW_DIR", raw_dir)

        result = build.load_sunshine()
        assert result is None


class TestBuildSunshineTodayHtml:
    """Test building today's sunshine HTML."""

    def test_build_sunshine_today_html_with_data(self) -> None:
        """Test building HTML with 15-minute sunshine data as timeline."""
        sunshine_data = {
            "today_15min": {
                "minutely_15": {
                    "time": [
                        "2026-02-04T08:00:00",
                        "2026-02-04T08:15:00",
                        "2026-02-04T08:30:00",
                        "2026-02-04T08:45:00",
                    ],
                    "sunshine_duration": [0, 450, 675, 900],  # 0%, 50%, 75%, 100%
                    "is_day": [1, 1, 1, 1],
                }
            }
        }

        result = build.build_sunshine_today_html(sunshine_data)

        assert "Today's Sun Breaks" in result
        assert "February 04" in result
        assert "sunshine-none" in result  # For 0% slot
        assert "sunshine-full" in result  # For 100% slot
        assert "timeline" in result  # Timeline container
        assert "tl-bar" in result  # Timeline bar
        assert "tl-seg" in result  # Timeline segments
        assert "tl-label" in result  # Hour labels
        assert "8am" in result  # Hour label for 8 AM
        assert "Sunrise" in result
        assert "Sunset" in result

    def test_build_sunshine_today_html_filters_to_first_day(self) -> None:
        """Test that multi-day 15-min data only shows the first day."""
        sunshine_data = {
            "today_15min": {
                "minutely_15": {
                    "time": [
                        "2026-02-04T10:00:00",
                        "2026-02-04T10:15:00",
                        "2026-02-05T10:00:00",  # Next day - should be excluded
                        "2026-02-05T10:15:00",
                    ],
                    "sunshine_duration": [900, 900, 900, 900],
                    "is_day": [1, 1, 1, 1],
                }
            }
        }

        result = build.build_sunshine_today_html(sunshine_data)

        assert "February 04" in result
        # 2 slots x 900 sec = 1800 sec = 0.5 hours (only day 1)
        assert "0.5 hours" in result

    def test_build_sunshine_today_html_no_times(self) -> None:
        """Test with empty time array."""
        sunshine_data = {
            "today_15min": {"minutely_15": {"time": [], "sunshine_duration": [], "is_day": []}}
        }

        result = build.build_sunshine_today_html(sunshine_data)
        assert "No 15-minute sunshine data available" in result

    def test_build_sunshine_today_html_no_daylight(self) -> None:
        """Test with no daylight hours."""
        sunshine_data = {
            "today_15min": {
                "minutely_15": {
                    "time": ["2026-02-04T06:00:00", "2026-02-04T06:15:00"],
                    "sunshine_duration": [0, 0],
                    "is_day": [0, 0],
                }
            }
        }

        result = build.build_sunshine_today_html(sunshine_data)
        assert "No daylight hours" in result


class TestWmoCodeToConditions:
    """Test WMO weather code mapping."""

    def test_known_codes(self) -> None:
        """Test known WMO codes return correct conditions with emojis."""
        result_clear = build.wmo_code_to_conditions(0)
        assert "Clear" in result_clear
        assert "\u2600" in result_clear  # sun emoji

        result_overcast = build.wmo_code_to_conditions(3)
        assert "Overcast" in result_overcast
        assert "\u2601" in result_overcast  # cloud emoji

        result_rain = build.wmo_code_to_conditions(61)
        assert "Light Rain" in result_rain

        result_thunder = build.wmo_code_to_conditions(95)
        assert "Thunderstorm" in result_thunder

    def test_unknown_code(self) -> None:
        """Test unknown WMO code returns fallback string."""
        assert build.wmo_code_to_conditions(999) == "Unknown (999)"


class TestBuildSunshine16DayHtml:
    """Test building 16-day sunshine HTML."""

    def test_build_sunshine_16day_html_with_data(self) -> None:
        """Test building HTML with 16-day sunshine data and weather."""
        sunshine_data = {
            "today_15min": {"minutely_15": {"time": [], "sunshine_duration": [], "is_day": []}},
            "daily_16day": {
                "daily": {
                    "time": ["2026-02-04", "2026-02-05"],
                    "sunshine_duration": [14400, 3600],  # 4h and 1h
                    "daylight_duration": [36000, 36000],  # 10h each
                }
            },
        }
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

        result = build.build_sunshine_16day_html(sunshine_data, weather_data)

        assert "16-Day Sunshine Forecast" in result
        assert "2026-02-04" in result
        assert "4.0h of 10.0h" in result  # Combined sun column
        assert "Sun" in result  # Header
        assert "High / Low" in result
        assert "Precip" in result
        assert "Clear" in result
        assert "Light Rain" in result
        assert "15\u00b0C" in result
        assert "5.2mm" in result

    def test_build_sunshine_16day_html_with_hourly_bar(self) -> None:
        """Test that days with 15-min data get hourly bar charts."""
        sunshine_data = {
            "today_15min": {
                "minutely_15": {
                    "time": [
                        "2026-02-04T08:00:00",
                        "2026-02-04T08:15:00",
                        "2026-02-04T08:30:00",
                        "2026-02-04T08:45:00",
                    ],
                    "sunshine_duration": [900, 900, 450, 0],
                    "is_day": [1, 1, 1, 1],
                }
            },
            "daily_16day": {
                "daily": {
                    "time": ["2026-02-04"],
                    "sunshine_duration": [14400],
                    "daylight_duration": [36000],
                }
            },
        }

        result = build.build_sunshine_16day_html(sunshine_data)

        assert "hour-bar" in result
        assert "hour-seg" in result

    def test_build_sunshine_16day_html_without_weather(self) -> None:
        """Test building HTML without weather data (em-dash fallbacks)."""
        sunshine_data = {
            "today_15min": {"minutely_15": {"time": [], "sunshine_duration": [], "is_day": []}},
            "daily_16day": {
                "daily": {
                    "time": ["2026-02-04"],
                    "sunshine_duration": [14400],
                    "daylight_duration": [36000],
                }
            },
        }

        result = build.build_sunshine_16day_html(sunshine_data)

        assert "16-Day Sunshine Forecast" in result
        assert "\u2014" in result  # em-dash for missing weather

    def test_build_sunshine_16day_html_no_data(self) -> None:
        """Test with empty data."""
        sunshine_data = {
            "today_15min": {"minutely_15": {"time": [], "sunshine_duration": [], "is_day": []}},
            "daily_16day": {
                "daily": {
                    "time": [],
                    "sunshine_duration": [],
                    "daylight_duration": [],
                }
            },
        }

        result = build.build_sunshine_16day_html(sunshine_data)
        assert "No 16-day sunshine data available" in result

    def test_build_sunshine_16day_html_zero_daylight(self) -> None:
        """Test with zero daylight (edge case)."""
        sunshine_data = {
            "today_15min": {"minutely_15": {"time": [], "sunshine_duration": [], "is_day": []}},
            "daily_16day": {
                "daily": {
                    "time": ["2026-02-04"],
                    "sunshine_duration": [0],
                    "daylight_duration": [0],
                }
            },
        }

        result = build.build_sunshine_16day_html(sunshine_data)
        assert "0%" in result


class TestBuildHtml:
    """Test building complete HTML page."""

    def test_build_html_with_sunshine(self) -> None:
        """Test building complete HTML with weather and sunshine data."""
        weather_data = {
            "fetched_at": "2026-02-04T12:00:00+00:00",
            "data": {
                "daily": {
                    "time": ["2026-02-04", "2026-02-05"],
                    "temperature_2m_max": [15.0, 18.0],
                    "temperature_2m_min": [5.0, 8.0],
                    "precipitation_sum": [0, 2.5],
                    "weather_code": [0, 63],
                }
            },
        }
        sunshine_data = {
            "today_15min": {
                "minutely_15": {
                    "time": ["2026-02-04T12:00:00"],
                    "sunshine_duration": [900],
                    "is_day": [1],
                }
            },
            "daily_16day": {
                "daily": {
                    "time": ["2026-02-04"],
                    "sunshine_duration": [14400],
                    "daylight_duration": [36000],
                }
            },
        }

        result = build.build_html(weather_data, sunshine_data)

        assert "<!DOCTYPE html>" in result
        assert "Butterfly Planner" in result
        assert "2026-02-04" in result
        assert "15\u00b0C" in result
        assert "Today's Sun Breaks" in result
        assert "16-Day Sunshine Forecast" in result
        assert "Clear" in result  # WMO code 0 (with emoji)

    def test_build_html_without_sunshine(self) -> None:
        """Test building HTML without sunshine data."""
        weather_data = {
            "fetched_at": "2026-02-04T12:00:00+00:00",
            "data": {
                "daily": {
                    "time": ["2026-02-04"],
                    "temperature_2m_max": [15.0],
                    "temperature_2m_min": [5.0],
                    "precipitation_sum": [0],
                    "weather_code": [2],
                }
            },
        }

        result = build.build_html(weather_data, None)

        assert "<!DOCTYPE html>" in result
        assert "Butterfly Planner" in result
        # Should not have sunshine sections
        assert "Today's Sun Breaks" not in result


class TestWriteSite:
    """Test writing site to disk."""

    def test_write_site(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test writing HTML to site directory."""
        site_dir = tmp_path / "site"
        monkeypatch.setattr(build, "SITE_DIR", site_dir)

        html_content = "<html><body>Test</body></html>"
        result = build.write_site(html_content)

        assert result == site_dir / "index.html"
        assert result.exists()
        assert result.read_text() == html_content


class TestBuildAllFlow:
    """Test the main build flow."""

    def test_build_all_no_weather(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test flow when no weather data exists."""
        raw_dir = tmp_path / "data" / "raw"
        raw_dir.mkdir(parents=True)
        monkeypatch.setattr(build, "RAW_DIR", raw_dir)

        result = build.build_all()
        assert result == {"error": "no data"}

    def test_build_all_with_weather_no_sunshine(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Test flow with weather but no sunshine data."""
        raw_dir = tmp_path / "data" / "raw"
        site_dir = tmp_path / "site"
        raw_dir.mkdir(parents=True)
        monkeypatch.setattr(build, "RAW_DIR", raw_dir)
        monkeypatch.setattr(build, "SITE_DIR", site_dir)

        weather_data = {
            "fetched_at": "2026-02-04T12:00:00+00:00",
            "data": {
                "daily": {
                    "time": ["2026-02-04"],
                    "temperature_2m_max": [15.0],
                    "temperature_2m_min": [5.0],
                    "precipitation_sum": [0],
                    "weather_code": [0],
                }
            },
        }
        (raw_dir / "weather.json").write_text(json.dumps(weather_data))

        result = build.build_all()

        assert result["pages"] == 1
        assert "output" in result
        assert (site_dir / "index.html").exists()

    def test_build_all_with_all_data(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test flow with both weather and sunshine data."""
        raw_dir = tmp_path / "data" / "raw"
        site_dir = tmp_path / "site"
        raw_dir.mkdir(parents=True)
        monkeypatch.setattr(build, "RAW_DIR", raw_dir)
        monkeypatch.setattr(build, "SITE_DIR", site_dir)

        weather_data = {
            "fetched_at": "2026-02-04T12:00:00+00:00",
            "data": {
                "daily": {
                    "time": ["2026-02-04"],
                    "temperature_2m_max": [15.0],
                    "temperature_2m_min": [5.0],
                    "precipitation_sum": [0],
                    "weather_code": [1],
                }
            },
        }
        sunshine_data = {
            "fetched_at": "2026-02-04T12:00:00",
            "today_15min": {
                "minutely_15": {
                    "time": ["2026-02-04T12:00:00"],
                    "sunshine_duration": [900],
                    "is_day": [1],
                }
            },
            "daily_16day": {
                "daily": {
                    "time": ["2026-02-04"],
                    "sunshine_duration": [14400],
                    "daylight_duration": [36000],
                }
            },
        }
        (raw_dir / "weather.json").write_text(json.dumps(weather_data))
        (raw_dir / "sunshine.json").write_text(json.dumps(sunshine_data))

        result = build.build_all()

        assert result["pages"] == 1
        assert "output" in result

        # Verify HTML contains sunshine sections
        html_content = (site_dir / "index.html").read_text()
        assert "Today's Sun Breaks" in html_content
        assert "16-Day Sunshine Forecast" in html_content
