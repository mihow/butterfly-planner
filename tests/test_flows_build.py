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
        """Test building HTML with 15-minute sunshine data."""
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
        assert "sunshine-grid" in result

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


class TestBuildSunshine16DayHtml:
    """Test building 16-day sunshine HTML."""

    def test_build_sunshine_16day_html_with_data(self) -> None:
        """Test building HTML with 16-day sunshine data."""
        sunshine_data = {
            "daily_16day": {
                "daily": {
                    "time": ["2026-02-04", "2026-02-05"],
                    "sunshine_duration": [14400, 3600],  # 4h and 1h
                    "daylight_duration": [36000, 36000],  # 10h each
                }
            }
        }

        result = build.build_sunshine_16day_html(sunshine_data)

        assert "16-Day Sunshine Forecast" in result
        assert "2026-02-04" in result
        assert "4.0h" in result
        assert "Good" in result  # Should have at least one good day

    def test_build_sunshine_16day_html_no_data(self) -> None:
        """Test with empty data."""
        sunshine_data = {
            "daily_16day": {
                "daily": {
                    "time": [],
                    "sunshine_duration": [],
                    "daylight_duration": [],
                }
            }
        }

        result = build.build_sunshine_16day_html(sunshine_data)
        assert "No 16-day sunshine data available" in result

    def test_build_sunshine_16day_html_zero_daylight(self) -> None:
        """Test with zero daylight (edge case)."""
        sunshine_data = {
            "daily_16day": {
                "daily": {
                    "time": ["2026-02-04"],
                    "sunshine_duration": [0],
                    "daylight_duration": [0],
                }
            }
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
        assert "15.0°C" in result
        assert "Today's Sun Breaks" in result
        assert "16-Day Sunshine Forecast" in result

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
                }
            },
        }

        result = build.build_html(weather_data, None)

        assert "<!DOCTYPE html>" in result
        assert "Butterfly Planner" in result
        # Should not have sunshine sections
        assert "Today's Sun Breaks" not in result


SAMPLE_INAT_DATA: dict = {
    "fetched_at": "2026-02-04T12:00:00",
    "source": "inaturalist.org",
    "data": {
        "month": 6,
        "species": [
            {
                "taxon_id": 48662,
                "scientific_name": "Vanessa cardui",
                "common_name": "Painted Lady",
                "rank": "species",
                "observation_count": 542,
                "photo_url": "https://inaturalist-open-data.s3.amazonaws.com/photos/123/medium.jpg",
                "taxon_url": "https://www.inaturalist.org/taxa/48662",
            },
            {
                "taxon_id": 48548,
                "scientific_name": "Pieris rapae",
                "common_name": "Cabbage White",
                "rank": "species",
                "observation_count": 318,
                "photo_url": None,
                "taxon_url": "https://www.inaturalist.org/taxa/48548",
            },
        ],
    },
}


class TestLoadInaturalist:
    """Test loading iNaturalist data from file."""

    def test_load_inaturalist_exists(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test loading iNaturalist data when file exists."""
        raw_dir = tmp_path / "data" / "raw"
        raw_dir.mkdir(parents=True)
        inat_file = raw_dir / "inaturalist.json"
        inat_file.write_text(json.dumps(SAMPLE_INAT_DATA))

        monkeypatch.setattr(build, "RAW_DIR", raw_dir)

        result = build.load_inaturalist()
        assert result == SAMPLE_INAT_DATA

    def test_load_inaturalist_not_exists(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Test loading iNaturalist data when file doesn't exist."""
        raw_dir = tmp_path / "data" / "raw"
        raw_dir.mkdir(parents=True)
        monkeypatch.setattr(build, "RAW_DIR", raw_dir)

        result = build.load_inaturalist()
        assert result is None


class TestBuildButterflySightingsHtml:
    """Test building butterfly sightings HTML section."""

    def test_with_species_data(self) -> None:
        """Test building HTML with species data."""
        result = build.build_butterfly_sightings_html(SAMPLE_INAT_DATA)

        assert "Butterfly Sightings - June" in result
        assert "Painted Lady" in result
        assert "Vanessa cardui" in result
        assert "542 research-grade observations" in result
        assert "Cabbage White" in result
        assert "species-card" in result
        assert "inaturalist.org/taxa/48662" in result

    def test_with_photo(self) -> None:
        """Test that photo URL renders as img tag."""
        result = build.build_butterfly_sightings_html(SAMPLE_INAT_DATA)

        assert 'class="species-photo"' in result
        assert "photos/123/medium.jpg" in result

    def test_without_photo(self) -> None:
        """Test placeholder when no photo URL."""
        result = build.build_butterfly_sightings_html(SAMPLE_INAT_DATA)

        assert "species-photo-placeholder" in result

    def test_empty_species(self) -> None:
        """Test with no species data."""
        empty_data: dict = {"data": {"month": 1, "species": []}}
        result = build.build_butterfly_sightings_html(empty_data)

        assert "No butterfly sightings data available" in result

    def test_observation_bar_scaling(self) -> None:
        """Test that observation bars scale relative to max count."""
        result = build.build_butterfly_sightings_html(SAMPLE_INAT_DATA)

        # First species (542) should have full-width bar (200px)
        assert 'style="width: 200px;"' in result
        # Second species (318) should have proportional bar
        assert 'style="width: 117px;"' in result


class TestBuildHtmlWithInaturalist:
    """Test build_html with iNaturalist data."""

    def test_build_html_with_inat(self) -> None:
        """Test that iNaturalist data is included in final HTML."""
        weather_data = {
            "fetched_at": "2026-02-04T12:00:00+00:00",
            "data": {
                "daily": {
                    "time": ["2026-02-04"],
                    "temperature_2m_max": [15.0],
                    "temperature_2m_min": [5.0],
                    "precipitation_sum": [0],
                }
            },
        }

        result = build.build_html(weather_data, None, SAMPLE_INAT_DATA)

        assert "Butterfly Sightings - June" in result
        assert "Painted Lady" in result
        assert "iNaturalist" in result

    def test_build_html_without_inat(self) -> None:
        """Test that HTML builds correctly without iNaturalist data."""
        weather_data = {
            "fetched_at": "2026-02-04T12:00:00+00:00",
            "data": {
                "daily": {
                    "time": ["2026-02-04"],
                    "temperature_2m_max": [15.0],
                    "temperature_2m_min": [5.0],
                    "precipitation_sum": [0],
                }
            },
        }

        result = build.build_html(weather_data, None, None)

        assert "<!DOCTYPE html>" in result
        assert "Butterfly Sightings" not in result


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
                }
            },
        }
        (raw_dir / "weather.json").write_text(json.dumps(weather_data))

        result = build.build_all()

        assert result["pages"] == 1
        assert "output" in result
        assert (site_dir / "index.html").exists()

    def test_build_all_with_all_data(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test flow with weather, sunshine, and iNaturalist data."""
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
        (raw_dir / "inaturalist.json").write_text(json.dumps(SAMPLE_INAT_DATA))

        result = build.build_all()

        assert result["pages"] == 1
        assert "output" in result

        # Verify HTML contains all sections
        html_content = (site_dir / "index.html").read_text()
        assert "Today's Sun Breaks" in html_content
        assert "16-Day Sunshine Forecast" in html_content
        assert "Butterfly Sightings" in html_content
        assert "Painted Lady" in html_content
