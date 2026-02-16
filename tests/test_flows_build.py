"""
Tests for the build flow module and renderer modules.
"""

from __future__ import annotations

import json
from typing import TYPE_CHECKING

import pytest

from butterfly_planner.flows import build
from butterfly_planner.renderers.sightings_map import (
    _build_weather_html,
    build_butterfly_map_html,
)
from butterfly_planner.renderers.sightings_table import build_butterfly_sightings_html
from butterfly_planner.renderers.sunshine import (
    build_sunshine_16day_html,
    build_sunshine_today_html,
)
from butterfly_planner.renderers.weather_utils import c_to_f, wmo_code_to_conditions
from butterfly_planner.store import DataStore

if TYPE_CHECKING:
    from pathlib import Path


def write_envelope(base_dir: Path, path: str, data: object, source: str = "test") -> None:
    """Write test data in the metadata envelope format."""
    full = base_dir / path
    full.parent.mkdir(parents=True, exist_ok=True)
    envelope = {
        "meta": {"source": source, "fetched_at": "2026-02-04T12:00:00+00:00"},
        "data": data,
    }
    full.write_text(json.dumps(envelope))


class TestCelsiusToFahrenheit:
    """Test temperature conversion."""

    @pytest.mark.parametrize(
        ("celsius", "fahrenheit"),
        [(0, 32.0), (100, 212.0), (-40, -40.0)],
    )
    def test_c_to_f(self, celsius: float, fahrenheit: float) -> None:
        """Test Celsius to Fahrenheit conversion."""
        assert c_to_f(celsius) == fahrenheit


class TestLoadWeather:
    """Test loading weather data from file."""

    def test_load_weather_exists(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test loading weather data when file exists."""
        ds = DataStore(tmp_path)
        monkeypatch.setattr(build, "store", ds)

        weather_payload = {"daily": {}}
        write_envelope(tmp_path, "live/weather.json", weather_payload, source="open-meteo.com")

        result = build.load_weather()
        assert result == weather_payload

    def test_load_weather_not_exists(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test loading weather data when file doesn't exist."""
        ds = DataStore(tmp_path)
        monkeypatch.setattr(build, "store", ds)

        result = build.load_weather()
        assert result is None


class TestLoadSunshine:
    """Test loading sunshine data from file."""

    def test_load_sunshine_exists(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test loading sunshine data when file exists."""
        ds = DataStore(tmp_path)
        monkeypatch.setattr(build, "store", ds)

        data_15min = {"minutely_15": {"time": [], "sunshine_duration": [], "is_day": []}}
        data_16day = {"daily": {"time": [], "sunshine_duration": [], "daylight_duration": []}}
        write_envelope(tmp_path, "live/sunshine_15min.json", data_15min, source="open-meteo.com")
        write_envelope(tmp_path, "live/sunshine_16day.json", data_16day, source="open-meteo.com")

        result = build.load_sunshine()
        assert result is not None
        assert result["fetched_at"] == "2026-02-04T12:00:00+00:00"
        assert result["source"] == "open-meteo.com"
        assert result["today_15min"] == data_15min
        assert result["daily_16day"] == data_16day

    def test_load_sunshine_not_exists(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Test loading sunshine data when file doesn't exist."""
        ds = DataStore(tmp_path)
        monkeypatch.setattr(build, "store", ds)

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

        result = build_sunshine_today_html(sunshine_data)

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

        result = build_sunshine_today_html(sunshine_data)

        assert "February 04" in result
        # 2 slots x 900 sec = 1800 sec = 0.5 hours (only day 1)
        assert "0.5 hours" in result

    def test_build_sunshine_today_html_no_times(self) -> None:
        """Test with empty time array."""
        sunshine_data = {
            "today_15min": {"minutely_15": {"time": [], "sunshine_duration": [], "is_day": []}}
        }

        result = build_sunshine_today_html(sunshine_data)
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

        result = build_sunshine_today_html(sunshine_data)
        assert "No daylight hours" in result


class TestWmoCodeToConditions:
    """Test WMO weather code mapping."""

    def test_known_codes(self) -> None:
        """Test known WMO codes return correct conditions with emojis."""
        result_clear = wmo_code_to_conditions(0)
        assert "Clear" in result_clear
        assert "\u2600" in result_clear  # sun emoji

        result_overcast = wmo_code_to_conditions(3)
        assert "Overcast" in result_overcast
        assert "\u2601" in result_overcast  # cloud emoji

        result_rain = wmo_code_to_conditions(61)
        assert "Light Rain" in result_rain

        result_thunder = wmo_code_to_conditions(95)
        assert "Thunderstorm" in result_thunder

    def test_unknown_code(self) -> None:
        """Test unknown WMO code returns fallback string."""
        assert wmo_code_to_conditions(999) == "Unknown (999)"


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

        result = build_sunshine_16day_html(sunshine_data, weather_data)

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

        result = build_sunshine_16day_html(sunshine_data)

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

        result = build_sunshine_16day_html(sunshine_data)

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

        result = build_sunshine_16day_html(sunshine_data)
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

        result = build_sunshine_16day_html(sunshine_data)
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


SAMPLE_INAT_DATA_WITH_OBS: dict = {
    "fetched_at": "2026-02-04T12:00:00",
    "source": "inaturalist.org",
    "data": {
        "month": 6,
        "weeks": [23, 24, 25],
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
        ],
        "observations": [
            {
                "id": 100001,
                "species": "Vanessa cardui",
                "common_name": "Painted Lady",
                "observed_on": "2024-06-15",
                "latitude": 45.52,
                "longitude": -122.68,
                "quality_grade": "research",
                "url": "https://www.inaturalist.org/observations/100001",
                "photo_url": "https://inaturalist-open-data.s3.amazonaws.com/photos/456/medium.jpg",
            },
            {
                "id": 100002,
                "species": "Vanessa cardui",
                "common_name": "Painted Lady",
                "observed_on": "2023-06-10",
                "latitude": 45.55,
                "longitude": -122.70,
                "quality_grade": "research",
                "url": "https://www.inaturalist.org/observations/100002",
                "photo_url": None,
            },
        ],
    },
}


class TestLoadInaturalist:
    """Test loading iNaturalist data from file."""

    def test_load_inaturalist_exists(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test loading iNaturalist data when file exists."""
        ds = DataStore(tmp_path)
        monkeypatch.setattr(build, "store", ds)

        # The envelope data payload is what was under SAMPLE_INAT_DATA["data"]
        inat_payload = SAMPLE_INAT_DATA["data"]
        write_envelope(tmp_path, "live/inaturalist.json", inat_payload, source="inaturalist.org")

        result = build.load_inaturalist()
        assert result is not None
        assert result["fetched_at"] == "2026-02-04T12:00:00+00:00"
        assert result["source"] == "inaturalist.org"
        assert result["data"] == inat_payload

    def test_load_inaturalist_not_exists(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Test loading iNaturalist data when file doesn't exist."""
        ds = DataStore(tmp_path)
        monkeypatch.setattr(build, "store", ds)

        result = build.load_inaturalist()
        assert result is None


class TestLoadHistoricalWeather:
    """Test loading historical weather cache."""

    def test_load_exists(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test loading historical weather when file exists."""
        ds = DataStore(tmp_path)
        monkeypatch.setattr(build, "store", ds)

        hw_payload = {
            "by_date": {
                "2024-06-15": {
                    "high_c": 22.0,
                    "low_c": 10.0,
                    "precip_mm": 0.0,
                    "weather_code": 0,
                },
            },
        }
        write_envelope(
            tmp_path,
            "historical/weather/historical_weather.json",
            hw_payload,
            source="open-meteo.com (archive)",
        )

        result = build.load_historical_weather()
        assert result is not None
        assert "2024-06-15" in result
        assert result["2024-06-15"]["high_c"] == 22.0

    def test_load_not_exists(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test loading historical weather when file doesn't exist."""
        ds = DataStore(tmp_path)
        monkeypatch.setattr(build, "store", ds)

        result = build.load_historical_weather()
        assert result is None


class TestBuildWeatherHtml:
    """Test the _build_weather_html helper."""

    def test_full_weather(self) -> None:
        """Test weather HTML with all fields."""
        w = {"weather_code": 0, "high_c": 22.0, "low_c": 10.0, "precip_mm": 0.0}
        result = _build_weather_html(w)
        assert "Clear" in result
        assert "22/10" in result
        # No precip when 0
        assert "mm" not in result

    def test_with_precipitation(self) -> None:
        """Test weather HTML includes precipitation when > 0."""
        w = {"weather_code": 61, "high_c": 12.0, "low_c": 5.0, "precip_mm": 3.2}
        result = _build_weather_html(w)
        assert "Light Rain" in result
        assert "3.2mm" in result

    def test_partial_weather(self) -> None:
        """Test weather HTML with missing fields."""
        w = {"weather_code": 3, "high_c": None, "low_c": None, "precip_mm": None}
        result = _build_weather_html(w)
        assert "Overcast" in result
        assert "\u00b0C" not in result


class TestBuildButterflyMapHtml:
    """Test building butterfly map with enriched popups."""

    def test_map_with_photo_and_weather(self) -> None:
        """Test map markers include photo URL and weather data."""
        hw = {
            "2024-06-15": {"high_c": 22.0, "low_c": 10.0, "precip_mm": 0.0, "weather_code": 0},
        }
        map_div, map_script = build_butterfly_map_html(
            SAMPLE_INAT_DATA_WITH_OBS, historical_weather=hw
        )

        assert "Butterfly Sightings Map" in map_div
        # Photo URL should be in marker data
        assert "photos/456/medium.jpg" in map_script
        # Weather should appear for the matching date
        assert "Clear" in map_script
        assert "22/10" in map_script
        # Object-based markers (not array)
        assert "lat:" in map_script
        assert "name:" in map_script
        assert "weather:" in map_script

    def test_map_without_historical_weather(self) -> None:
        """Test map works without historical weather data."""
        map_div, map_script = build_butterfly_map_html(SAMPLE_INAT_DATA_WITH_OBS)

        assert "Butterfly Sightings Map" in map_div
        assert "Painted Lady" in map_script
        assert "buildPopup" in map_script

    def test_map_no_observations(self) -> None:
        """Test map with no observations returns fallback."""
        no_obs: dict = {"data": {"observations": [], "weeks": [5, 6, 7]}}
        map_div, map_script = build_butterfly_map_html(no_obs)

        assert "No observation data" in map_div
        assert map_script == ""

    def test_map_popup_structure(self) -> None:
        """Test that the JS template builds popups with obs-popup class."""
        _, map_script = build_butterfly_map_html(SAMPLE_INAT_DATA_WITH_OBS)

        assert "obs-popup" in map_script
        assert "obs-popup-img" in map_script
        assert "obs-popup-body" in map_script
        assert "obs-popup-weather" in map_script


class TestBuildButterflySightingsHtml:
    """Test building butterfly sightings HTML section."""

    def test_with_species_data(self) -> None:
        """Test building HTML with species data."""
        result = build_butterfly_sightings_html(SAMPLE_INAT_DATA)

        assert "Butterfly Sightings" in result
        assert "June" in result
        assert "Painted Lady" in result
        assert "Vanessa cardui" in result
        assert ">542<" in result
        assert "Cabbage White" in result
        assert "inaturalist.org/taxa/48662" in result
        assert "<table>" in result
        assert "<thead>" in result

    def test_with_photo(self) -> None:
        """Test that photo URL renders as img tag."""
        result = build_butterfly_sightings_html(SAMPLE_INAT_DATA)

        assert 'class="species-photo"' in result
        assert "photos/123/medium.jpg" in result

    def test_without_photo(self) -> None:
        """Test placeholder when no photo URL."""
        result = build_butterfly_sightings_html(SAMPLE_INAT_DATA)

        assert "species-photo-placeholder" in result

    def test_deep_links(self) -> None:
        """Test that observation counts link to iNaturalist search."""
        result = build_butterfly_sightings_html(SAMPLE_INAT_DATA)

        # Observation count should link to filtered search
        assert "taxon_id=48662&month=6" in result
        assert "quality_grade=research" in result
        # "Browse on iNaturalist" link for all butterflies in region
        # URL is autoescaped in the href attribute
        assert "taxon_id=47224&amp;month=6" in result
        # Photo should link to taxon page
        assert 'href="https://www.inaturalist.org/taxa/48662"' in result

    def test_empty_species(self) -> None:
        """Test with no species data."""
        empty_data: dict = {"data": {"month": 1, "species": []}}
        result = build_butterfly_sightings_html(empty_data)

        assert "No butterfly sightings data available" in result

    def test_observation_bar_scaling(self) -> None:
        """Test that observation bars scale relative to max count."""
        result = build_butterfly_sightings_html(SAMPLE_INAT_DATA)

        # First species (542) should have full-width bar (200px)
        assert "width: 200px;" in result
        # Second species (318) should have proportional bar
        assert "width: 117px;" in result


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

        result = build.build_html(weather_data, None, SAMPLE_INAT_DATA, historical_weather=None)

        assert "Butterfly Sightings" in result
        assert "June" in result
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
        ds = DataStore(tmp_path)
        monkeypatch.setattr(build, "store", ds)

        result = build.build_all()
        assert result == {"error": "no data"}

    def test_build_all_with_weather_no_sunshine(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Test flow with weather but no sunshine data."""
        ds = DataStore(tmp_path)
        site_dir = ds.derived / "site"
        monkeypatch.setattr(build, "store", ds)
        monkeypatch.setattr(build, "SITE_DIR", site_dir)

        weather_payload = {
            "daily": {
                "time": ["2026-02-04"],
                "temperature_2m_max": [15.0],
                "temperature_2m_min": [5.0],
                "precipitation_sum": [0],
                "weather_code": [0],
            }
        }
        write_envelope(tmp_path, "live/weather.json", weather_payload, source="open-meteo.com")

        result = build.build_all()

        assert result["pages"] == 1
        assert "output" in result
        assert (site_dir / "index.html").exists()

    def test_build_all_with_all_data(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test flow with weather, sunshine, and iNaturalist data."""
        ds = DataStore(tmp_path)
        site_dir = ds.derived / "site"
        monkeypatch.setattr(build, "store", ds)
        monkeypatch.setattr(build, "SITE_DIR", site_dir)

        weather_payload = {
            "daily": {
                "time": ["2026-02-04"],
                "temperature_2m_max": [15.0],
                "temperature_2m_min": [5.0],
                "precipitation_sum": [0],
                "weather_code": [1],
            }
        }
        write_envelope(tmp_path, "live/weather.json", weather_payload, source="open-meteo.com")

        sunshine_15min_payload = {
            "minutely_15": {
                "time": ["2026-02-04T12:00:00"],
                "sunshine_duration": [900],
                "is_day": [1],
            }
        }
        sunshine_16day_payload = {
            "daily": {
                "time": ["2026-02-04"],
                "sunshine_duration": [14400],
                "daylight_duration": [36000],
            }
        }
        write_envelope(
            tmp_path, "live/sunshine_15min.json", sunshine_15min_payload, source="open-meteo.com"
        )
        write_envelope(
            tmp_path, "live/sunshine_16day.json", sunshine_16day_payload, source="open-meteo.com"
        )

        inat_payload = SAMPLE_INAT_DATA["data"]
        write_envelope(tmp_path, "live/inaturalist.json", inat_payload, source="inaturalist.org")

        result = build.build_all()

        assert result["pages"] == 1
        assert "output" in result

        # Verify HTML contains all sections
        html_content = (site_dir / "index.html").read_text()
        assert "Today's Sun Breaks" in html_content
        assert "16-Day Sunshine Forecast" in html_content
        assert "Butterfly Sightings" in html_content
        assert "Painted Lady" in html_content
