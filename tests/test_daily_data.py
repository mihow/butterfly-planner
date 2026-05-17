"""Tests for the structured daily data extraction module."""

from __future__ import annotations

from datetime import date
from typing import Any

from butterfly_planner.renderers.daily_data import (
    SCHEMA_VERSION,
    build_daily_data,
)

# =============================================================================
# Test fixtures
# =============================================================================


def _weather_envelope(dates: list[str] | None = None) -> dict[str, Any]:
    """Build a weather envelope matching build.py's format."""
    dates = dates or ["2026-03-16", "2026-03-17", "2026-03-18"]
    n = len(dates)
    return {
        "fetched_at": "2026-03-16T12:00:00+00:00",
        "source": "open-meteo.com",
        "data": {
            "daily": {
                "time": dates,
                "temperature_2m_max": [14.2] * n,
                "temperature_2m_min": [6.1] * n,
                "precipitation_sum": [0.0] * n,
                "weather_code": [1] * n,
            }
        },
    }


def _sunshine_data(today: str = "2026-03-16") -> dict[str, Any]:
    """Build sunshine data matching build.py's combined format."""
    return {
        "today_15min": {
            "minutely_15": {
                "time": [
                    f"{today}T08:00:00",
                    f"{today}T08:15:00",
                    f"{today}T08:30:00",
                    f"{today}T08:45:00",
                    f"{today}T09:00:00",
                    f"{today}T09:15:00",
                    f"{today}T09:30:00",
                    f"{today}T09:45:00",
                ],
                "sunshine_duration": [900, 900, 450, 0, 900, 900, 900, 900],
                "is_day": [1, 1, 1, 1, 1, 1, 1, 1],
            }
        },
        "daily_16day": {
            "daily": {
                "time": [today, "2026-03-17", "2026-03-18"],
                "sunshine_duration": [21600, 14400, 3600],  # 6h, 4h, 1h
                "daylight_duration": [43200, 43200, 43200],  # 12h each
            }
        },
    }


def _inat_data() -> dict[str, Any]:
    """Build iNaturalist data matching build.py's envelope format."""
    return {
        "fetched_at": "2026-03-16T12:00:00",
        "source": "inaturalist.org",
        "data": {
            "month": 3,
            "date_start": "2026-03-02",
            "date_end": "2026-03-23",
            "species": [
                {
                    "taxon_id": 48662,
                    "scientific_name": "Vanessa cardui",
                    "common_name": "Painted Lady",
                    "rank": "species",
                    "observation_count": 45,
                    "photo_url": "https://example.com/photo.jpg",
                    "taxon_url": "https://www.inaturalist.org/taxa/48662",
                },
                {
                    "taxon_id": 48548,
                    "scientific_name": "Pieris rapae",
                    "common_name": "Cabbage White",
                    "rank": "species",
                    "observation_count": 30,
                    "photo_url": None,
                    "taxon_url": "https://www.inaturalist.org/taxa/48548",
                },
            ],
            "observations": [
                {
                    "id": 1,
                    "species": "Vanessa cardui",
                    "common_name": "Painted Lady",
                    "observed_on": "2024-03-15",
                    "latitude": 45.52,
                    "longitude": -122.68,
                    "quality_grade": "research",
                    "url": "https://www.inaturalist.org/observations/1",
                    "photo_url": "https://example.com/obs1.jpg",
                },
            ],
        },
    }


def _gdd_data() -> dict[str, Any]:
    """Build GDD data matching build.py's envelope format."""
    return {
        "fetched_at": "2026-03-16T12:00:00",
        "source": "open-meteo.com (archive)",
        "data": {
            "base_temp_f": 50,
            "current_year": {
                "year": 2026,
                "total_gdd": 142.5,
                "daily": [
                    {"date": "2026-03-15", "daily_gdd": 7.0, "accumulated": 134.2},
                    {"date": "2026-03-16", "daily_gdd": 8.3, "accumulated": 142.5},
                ],
            },
            "previous_year": {
                "year": 2025,
                "total_gdd": 280.0,
                "daily": [
                    {"date": "2025-03-15", "daily_gdd": 5.0, "accumulated": 110.0},
                    {"date": "2025-03-16", "daily_gdd": 4.5, "accumulated": 114.5},
                ],
            },
        },
    }


# =============================================================================
# Tests
# =============================================================================


class TestBuildDailyDataEnvelope:
    """Test the top-level structure of build_daily_data output."""

    def test_schema_version(self) -> None:
        result = build_daily_data(target_date=date(2026, 3, 16))
        assert result["version"] == SCHEMA_VERSION

    def test_date_field(self) -> None:
        result = build_daily_data(target_date=date(2026, 3, 16))
        assert result["date"] == "2026-03-16"

    def test_location(self) -> None:
        result = build_daily_data(
            target_date=date(2026, 3, 16),
            location_name="Portland, OR",
            lat=45.5,
            lon=-122.6,
        )
        assert result["location"]["name"] == "Portland, OR"
        assert result["location"]["lat"] == 45.5
        assert result["location"]["lon"] == -122.6

    def test_generated_at_is_iso(self) -> None:
        result = build_daily_data(target_date=date(2026, 3, 16))
        assert "T" in result["generated_at"]

    def test_all_sections_present(self) -> None:
        result = build_daily_data(target_date=date(2026, 3, 16))
        assert "sunshine" in result
        assert "weather" in result
        assert "gdd" in result
        assert "butterflies" in result
        assert "forecast" in result

    def test_empty_inputs_produce_none_sections(self) -> None:
        result = build_daily_data(target_date=date(2026, 3, 16))
        assert result["sunshine"] is None
        assert result["weather"] is None
        assert result["gdd"] is None
        assert result["butterflies"] is None
        assert result["forecast"] == []


class TestSunshineExtraction:
    """Test sunshine data extraction."""

    def test_sunshine_hours(self) -> None:
        result = build_daily_data(
            sunshine_data=_sunshine_data(),
            target_date=date(2026, 3, 16),
        )
        sun = result["sunshine"]
        assert sun is not None
        # 8 slots: 900+900+450+0+900+900+900+900 = 5850 sec = 1.625h
        assert sun["today_hours"] == 1.6

    def test_sunshine_daylight_from_daily(self) -> None:
        result = build_daily_data(
            sunshine_data=_sunshine_data(),
            target_date=date(2026, 3, 16),
        )
        sun = result["sunshine"]
        assert sun is not None
        assert sun["daylight_hours"] == 12.0

    def test_sunshine_pct(self) -> None:
        result = build_daily_data(
            sunshine_data=_sunshine_data(),
            target_date=date(2026, 3, 16),
        )
        sun = result["sunshine"]
        assert sun is not None
        # 21600 sun / 43200 daylight = 50%
        assert sun["sunshine_pct"] == 50.0

    def test_good_day_detection(self) -> None:
        result = build_daily_data(
            sunshine_data=_sunshine_data(),
            target_date=date(2026, 3, 16),
        )
        sun = result["sunshine"]
        assert sun is not None
        # 50% sunshine > 40% threshold → good day
        assert sun["is_good_day"] is True

    def test_sunrise_sunset(self) -> None:
        result = build_daily_data(
            sunshine_data=_sunshine_data(),
            target_date=date(2026, 3, 16),
        )
        sun = result["sunshine"]
        assert sun is not None
        assert sun["sunrise"] == "08:00"
        assert sun["sunset"] == "09:45"

    def test_hourly_breakdown(self) -> None:
        result = build_daily_data(
            sunshine_data=_sunshine_data(),
            target_date=date(2026, 3, 16),
        )
        sun = result["sunshine"]
        assert sun is not None
        assert len(sun["hourly"]) == 2  # hours 8 and 9
        assert sun["hourly"][0]["hour"] == 8
        assert sun["hourly"][1]["hour"] == 9

    def test_no_sunshine_data(self) -> None:
        result = build_daily_data(target_date=date(2026, 3, 16))
        assert result["sunshine"] is None


class TestWeatherExtraction:
    """Test weather data extraction."""

    def test_today_weather(self) -> None:
        result = build_daily_data(
            weather_data=_weather_envelope(),
            target_date=date(2026, 3, 16),
        )
        w = result["weather"]
        assert w is not None
        assert w["high_c"] == 14.2
        assert w["low_c"] == 6.1
        assert w["precip_mm"] == 0.0
        assert w["weather_code"] == 1
        assert "Mostly Clear" in w["conditions"]

    def test_no_matching_date(self) -> None:
        result = build_daily_data(
            weather_data=_weather_envelope(["2026-03-20"]),
            target_date=date(2026, 3, 16),
        )
        assert result["weather"] is None

    def test_no_weather_data(self) -> None:
        result = build_daily_data(target_date=date(2026, 3, 16))
        assert result["weather"] is None


class TestGDDExtraction:
    """Test GDD data extraction."""

    def test_accumulated_gdd(self) -> None:
        result = build_daily_data(
            gdd_data=_gdd_data(),
            target_date=date(2026, 3, 16),
        )
        g = result["gdd"]
        assert g is not None
        assert g["accumulated"] == 142.5

    def test_daily_gdd(self) -> None:
        result = build_daily_data(
            gdd_data=_gdd_data(),
            target_date=date(2026, 3, 16),
        )
        g = result["gdd"]
        assert g is not None
        assert g["daily"] == 8.3

    def test_year_comparison(self) -> None:
        result = build_daily_data(
            gdd_data=_gdd_data(),
            target_date=date(2026, 3, 16),
        )
        g = result["gdd"]
        assert g is not None
        # 142.5 vs 114.5 = +28, ratio 1.24 > 1.05 → ahead
        assert "ahead" in g["year_comparison"]

    def test_base_temp(self) -> None:
        result = build_daily_data(
            gdd_data=_gdd_data(),
            target_date=date(2026, 3, 16),
        )
        g = result["gdd"]
        assert g is not None
        assert g["base_temp_f"] == 50

    def test_no_gdd_data(self) -> None:
        result = build_daily_data(target_date=date(2026, 3, 16))
        assert result["gdd"] is None


class TestButterflyExtraction:
    """Test butterfly data extraction."""

    def test_species_count(self) -> None:
        result = build_daily_data(
            inat_data=_inat_data(),
            target_date=date(2026, 3, 16),
        )
        b = result["butterflies"]
        assert b is not None
        assert b["species_count"] == 2

    def test_top_species(self) -> None:
        result = build_daily_data(
            inat_data=_inat_data(),
            target_date=date(2026, 3, 16),
        )
        b = result["butterflies"]
        assert b is not None
        assert len(b["top_species"]) == 2
        # Sorted by count descending
        assert b["top_species"][0]["common_name"] == "Painted Lady"
        assert b["top_species"][0]["observation_count"] == 45

    def test_observation_window(self) -> None:
        result = build_daily_data(
            inat_data=_inat_data(),
            target_date=date(2026, 3, 16),
        )
        b = result["butterflies"]
        assert b is not None
        assert b["observation_window"]["start"] == "2026-03-02"
        assert b["observation_window"]["end"] == "2026-03-23"

    def test_observation_count(self) -> None:
        result = build_daily_data(
            inat_data=_inat_data(),
            target_date=date(2026, 3, 16),
        )
        b = result["butterflies"]
        assert b is not None
        assert b["recent_observations_count"] == 1

    def test_no_inat_data(self) -> None:
        result = build_daily_data(target_date=date(2026, 3, 16))
        assert result["butterflies"] is None

    def test_empty_species(self) -> None:
        empty = {"data": {"species": [], "observations": []}}
        result = build_daily_data(
            inat_data=empty,
            target_date=date(2026, 3, 16),
        )
        assert result["butterflies"] is None


class TestForecastExtraction:
    """Test forecast array extraction."""

    def test_excludes_today(self) -> None:
        result = build_daily_data(
            weather_data=_weather_envelope(),
            target_date=date(2026, 3, 16),
        )
        forecast = result["forecast"]
        dates = [f["date"] for f in forecast]
        assert "2026-03-16" not in dates

    def test_includes_future_days(self) -> None:
        result = build_daily_data(
            weather_data=_weather_envelope(),
            target_date=date(2026, 3, 16),
        )
        forecast = result["forecast"]
        assert len(forecast) == 2  # 03-17 and 03-18
        assert forecast[0]["date"] == "2026-03-17"

    def test_forecast_has_weather_fields(self) -> None:
        result = build_daily_data(
            weather_data=_weather_envelope(),
            target_date=date(2026, 3, 16),
        )
        forecast = result["forecast"]
        assert len(forecast) > 0
        day = forecast[0]
        assert "high_c" in day
        assert "low_c" in day
        assert "precip_mm" in day
        assert "conditions" in day
        assert "is_good_day" in day

    def test_forecast_with_sunshine(self) -> None:
        result = build_daily_data(
            weather_data=_weather_envelope(),
            sunshine_data=_sunshine_data(),
            target_date=date(2026, 3, 16),
        )
        forecast = result["forecast"]
        assert len(forecast) > 0
        day = forecast[0]
        assert "sunshine_hours" in day
        assert "daylight_hours" in day
        assert "sunshine_pct" in day

    def test_forecast_max_7_days(self) -> None:
        dates = [f"2026-03-{d:02d}" for d in range(16, 30)]
        result = build_daily_data(
            weather_data=_weather_envelope(dates),
            target_date=date(2026, 3, 16),
        )
        assert len(result["forecast"]) == 7

    def test_empty_forecast_without_weather(self) -> None:
        result = build_daily_data(target_date=date(2026, 3, 16))
        assert result["forecast"] == []


class TestFullIntegration:
    """Test with all data sources combined."""

    def test_all_sources(self) -> None:
        result = build_daily_data(
            weather_data=_weather_envelope(),
            sunshine_data=_sunshine_data(),
            inat_data=_inat_data(),
            gdd_data=_gdd_data(),
            target_date=date(2026, 3, 16),
        )
        assert result["version"] == SCHEMA_VERSION
        assert result["sunshine"] is not None
        assert result["weather"] is not None
        assert result["gdd"] is not None
        assert result["butterflies"] is not None
        assert len(result["forecast"]) > 0

    def test_json_serializable(self) -> None:
        """Verify the output can be serialized to JSON."""
        import json  # noqa: PLC0415

        result = build_daily_data(
            weather_data=_weather_envelope(),
            sunshine_data=_sunshine_data(),
            inat_data=_inat_data(),
            gdd_data=_gdd_data(),
            target_date=date(2026, 3, 16),
        )
        # Should not raise
        serialized = json.dumps(result)
        assert len(serialized) > 100
        # Round-trip
        parsed = json.loads(serialized)
        assert parsed["version"] == SCHEMA_VERSION
