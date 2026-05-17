"""Tests for the serialization.daily_data module (v0.2 release candidate).

TDD: these tests were written before the implementation.
"""

from __future__ import annotations

import json
from datetime import date
from typing import Any

from butterfly_planner.serialization.daily_data import (
    SCHEMA_VERSION,
    WMO_DESCRIPTIONS,
    DailyData,
    DailyForecastDay,
    DailyLocation,
    build_daily_data,
)

# =============================================================================
# Fixtures shared across test classes
# =============================================================================


def _weather_envelope(dates: list[str] | None = None) -> dict[str, Any]:
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
                "sunshine_duration": [21600, 14400, 3600],
                "daylight_duration": [43200, 43200, 43200],
            }
        },
    }


def _inat_data() -> dict[str, Any]:
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
# Import: new location
# =============================================================================


class TestNewModuleLocation:
    """The contract module must live in serialization/, not renderers/."""

    def test_importable_from_serialization(self) -> None:
        assert callable(build_daily_data)

    def test_schema_version_is_0_2_rc(self) -> None:
        # v0.2 = release candidate; promotion to 1.0 deferred until a real
        # consumer validates the contract end to end.
        assert SCHEMA_VERSION == "0.2"


# =============================================================================
# Pydantic models
# =============================================================================


class TestPydanticModels:
    """Pydantic models must be importable and round-trip correctly."""

    def test_daily_data_model_importable(self) -> None:
        assert DailyData is not None

    def test_model_validates_full_output(self) -> None:
        raw = build_daily_data(
            weather_data=_weather_envelope(),
            sunshine_data=_sunshine_data(),
            inat_data=_inat_data(),
            gdd_data=_gdd_data(),
            target_date=date(2026, 3, 16),
        )
        model = DailyData.model_validate(raw)
        assert model.version == SCHEMA_VERSION

    def test_model_validates_empty_inputs(self) -> None:
        raw = build_daily_data(target_date=date(2026, 3, 16))
        model = DailyData.model_validate(raw)
        assert model.sunshine is None
        assert model.weather is None

    def test_json_schema_exportable(self) -> None:
        schema = DailyData.model_json_schema()
        assert "properties" in schema
        assert "version" in schema["properties"]


# =============================================================================
# Conditions field: no emoji, weather_code only
# =============================================================================


class TestConditionsFieldRemoved:
    """The `conditions` string (with emoji) must not appear in weather or forecast."""

    def test_weather_has_no_conditions_field(self) -> None:
        result = build_daily_data(
            weather_data=_weather_envelope(),
            target_date=date(2026, 3, 16),
        )
        assert "conditions" not in result["weather"]

    def test_weather_has_weather_code(self) -> None:
        result = build_daily_data(
            weather_data=_weather_envelope(),
            target_date=date(2026, 3, 16),
        )
        assert result["weather"]["weather_code"] == 1

    def test_forecast_entries_have_no_conditions_field(self) -> None:
        result = build_daily_data(
            weather_data=_weather_envelope(),
            target_date=date(2026, 3, 16),
        )
        for entry in result["forecast"]:
            assert "conditions" not in entry

    def test_no_emoji_in_serialized_json(self) -> None:
        result = build_daily_data(
            weather_data=_weather_envelope(),
            sunshine_data=_sunshine_data(),
            inat_data=_inat_data(),
            gdd_data=_gdd_data(),
            target_date=date(2026, 3, 16),
        )
        serialized = json.dumps(result, ensure_ascii=False)
        for char in serialized:
            code_point = ord(char)
            assert not (0x1F300 <= code_point <= 0x1F9FF), (
                f"Emoji U+{code_point:04X} found in output"
            )

    def test_wmo_description_map_exported(self) -> None:
        """A plain-text WMO code → description map must be available for consumers."""
        assert isinstance(WMO_DESCRIPTIONS, dict)
        assert WMO_DESCRIPTIONS[0] == "Clear"
        assert WMO_DESCRIPTIONS[1] == "Mostly Clear"
        assert WMO_DESCRIPTIONS[63] == "Rain"
        for v in WMO_DESCRIPTIONS.values():
            for char in v:
                code_point = ord(char)
                assert not (0x1F300 <= code_point <= 0x1F9FF)


# =============================================================================
# Sunshine semantics: window_start / window_end instead of sunrise / sunset
# =============================================================================


class TestSunshineWindowSemantics:
    """Sunrise/sunset fields must be renamed to window_start/window_end."""

    def test_no_sunrise_field(self) -> None:
        result = build_daily_data(
            sunshine_data=_sunshine_data(),
            target_date=date(2026, 3, 16),
        )
        assert "sunrise" not in result["sunshine"]

    def test_no_sunset_field(self) -> None:
        result = build_daily_data(
            sunshine_data=_sunshine_data(),
            target_date=date(2026, 3, 16),
        )
        assert "sunset" not in result["sunshine"]

    def test_window_start_present(self) -> None:
        result = build_daily_data(
            sunshine_data=_sunshine_data(),
            target_date=date(2026, 3, 16),
        )
        assert "window_start" in result["sunshine"]
        assert result["sunshine"]["window_start"] == "08:00"

    def test_window_end_present(self) -> None:
        result = build_daily_data(
            sunshine_data=_sunshine_data(),
            target_date=date(2026, 3, 16),
        )
        assert "window_end" in result["sunshine"]
        assert result["sunshine"]["window_end"] == "09:45"


# =============================================================================
# Schema version bump
# =============================================================================


class TestSchemaVersion:
    def test_version_in_output(self) -> None:
        result = build_daily_data(target_date=date(2026, 3, 16))
        assert result["version"] == SCHEMA_VERSION


# =============================================================================
# Drift-guard: canonical schema keys
# =============================================================================

# This is the canonical schema key structure. If any key changes,
# this test will catch it and force an explicit decision.
CANONICAL_TOP_LEVEL_KEYS = {
    "version",
    "date",
    "location",
    "generated_at",
    "sunshine",
    "weather",
    "gdd",
    "butterflies",
    "forecast",
}
CANONICAL_SUNSHINE_KEYS = {
    "today_hours",
    "daylight_hours",
    "sunshine_pct",
    "is_good_day",
    "window_start",
    "window_end",
    "hourly",
}
CANONICAL_WEATHER_KEYS = {"high_c", "low_c", "precip_mm", "weather_code"}
CANONICAL_GDD_KEYS = {"accumulated", "daily", "base_temp_f", "year_comparison"}
CANONICAL_BUTTERFLIES_KEYS = {
    "observation_window",
    "species_count",
    "top_species",
    "recent_observations_count",
}
CANONICAL_FORECAST_DAY_KEYS = {
    "date",
    "high_c",
    "low_c",
    "precip_mm",
    "weather_code",
    "sunshine_hours",
    "daylight_hours",
    "sunshine_pct",
    "is_good_day",
}


class TestDriftGuard:
    """Guard against accidental schema drift.

    These tests fail immediately when keys are added, removed, or renamed.
    Any change requires an explicit update to the canonical set above.
    """

    def test_top_level_keys(self) -> None:
        result = build_daily_data(target_date=date(2026, 3, 16))
        assert set(result.keys()) == CANONICAL_TOP_LEVEL_KEYS

    def test_sunshine_keys(self) -> None:
        result = build_daily_data(
            sunshine_data=_sunshine_data(),
            target_date=date(2026, 3, 16),
        )
        assert set(result["sunshine"].keys()) == CANONICAL_SUNSHINE_KEYS

    def test_weather_keys(self) -> None:
        result = build_daily_data(
            weather_data=_weather_envelope(),
            target_date=date(2026, 3, 16),
        )
        assert set(result["weather"].keys()) == CANONICAL_WEATHER_KEYS

    def test_gdd_keys(self) -> None:
        result = build_daily_data(
            gdd_data=_gdd_data(),
            target_date=date(2026, 3, 16),
        )
        assert set(result["gdd"].keys()) == CANONICAL_GDD_KEYS

    def test_butterflies_keys(self) -> None:
        result = build_daily_data(
            inat_data=_inat_data(),
            target_date=date(2026, 3, 16),
        )
        assert set(result["butterflies"].keys()) == CANONICAL_BUTTERFLIES_KEYS

    def test_forecast_day_keys(self) -> None:
        result = build_daily_data(
            weather_data=_weather_envelope(),
            sunshine_data=_sunshine_data(),
            target_date=date(2026, 3, 16),
        )
        assert len(result["forecast"]) > 0
        assert set(result["forecast"][0].keys()) == CANONICAL_FORECAST_DAY_KEYS

    def test_doc_example_schema_matches_output(self) -> None:
        """Keys in docs/daily-data-format-options.md match actual output."""
        result = build_daily_data(
            weather_data=_weather_envelope(),
            sunshine_data=_sunshine_data(),
            inat_data=_inat_data(),
            gdd_data=_gdd_data(),
            target_date=date(2026, 3, 16),
        )
        # Top-level keys documented in the spec
        doc_top_keys = {
            "version",
            "date",
            "location",
            "generated_at",
            "sunshine",
            "weather",
            "gdd",
            "butterflies",
            "forecast",
        }
        assert doc_top_keys <= set(result.keys())

        # Sunshine section
        doc_sunshine_keys = {
            "today_hours",
            "daylight_hours",
            "sunshine_pct",
            "is_good_day",
            "hourly",
        }
        assert doc_sunshine_keys <= set(result["sunshine"].keys())

        # Weather section — conditions removed (kept stable through 1.0)
        doc_weather_keys = {"high_c", "low_c", "precip_mm", "weather_code"}
        assert doc_weather_keys <= set(result["weather"].keys())


# =============================================================================
# Pydantic round-trip validation (consumer simulation)
# =============================================================================


class TestPydanticRoundTrip:
    """Simulate a consumer loading the JSON via the Pydantic model."""

    def test_full_json_round_trip(self) -> None:
        raw = build_daily_data(
            weather_data=_weather_envelope(),
            sunshine_data=_sunshine_data(),
            inat_data=_inat_data(),
            gdd_data=_gdd_data(),
            target_date=date(2026, 3, 16),
        )
        # Serialize to JSON string (as a widget/consumer would receive it)
        json_str = json.dumps(raw)
        # Consumer loads it back
        parsed = json.loads(json_str)
        model = DailyData.model_validate(parsed)
        # Verify key fields accessible via model
        assert model.version == SCHEMA_VERSION
        assert model.date == "2026-03-16"
        assert model.location.name == "Portland, OR"
        assert model.location.lat == 45.5
        assert model.weather is not None
        assert model.weather.weather_code == 1
        assert model.sunshine is not None
        assert model.sunshine.today_hours == 1.6
        assert len(model.forecast) > 0
        assert isinstance(model.forecast[0], DailyForecastDay)

    def test_model_serializes_back_to_json(self) -> None:
        raw = build_daily_data(
            weather_data=_weather_envelope(),
            sunshine_data=_sunshine_data(),
            target_date=date(2026, 3, 16),
        )
        model = DailyData.model_validate(raw)
        # model_dump_json should not raise
        dumped = model.model_dump_json()
        reparsed = json.loads(dumped)
        assert reparsed["version"] == SCHEMA_VERSION


# =============================================================================
# Fully-typed nested models (DailyLocation, DailyForecastDay)
# =============================================================================


class TestTypedNestedModels:
    """location and forecast must be typed models, not list[dict]/dict."""

    def test_location_is_typed_model(self) -> None:
        result = build_daily_data(target_date=date(2026, 3, 16))
        model = DailyData.model_validate(result)
        # location is a DailyLocation, not a bare dict
        assert isinstance(model.location, DailyLocation)
        assert model.location.name == "Portland, OR"

    def test_location_rejects_missing_field(self) -> None:
        import pytest  # noqa: PLC0415
        from pydantic import ValidationError  # noqa: PLC0415

        with pytest.raises(ValidationError):
            DailyLocation.model_validate({"name": "X", "lat": 1.0})  # no lon

    def test_forecast_is_list_of_typed_models(self) -> None:
        result = build_daily_data(
            weather_data=_weather_envelope(),
            sunshine_data=_sunshine_data(),
            target_date=date(2026, 3, 16),
        )
        model = DailyData.model_validate(result)
        assert len(model.forecast) > 0
        assert all(isinstance(d, DailyForecastDay) for d in model.forecast)

    def test_forecast_day_all_keys_present_without_sunshine(self) -> None:
        """model_dump emits a stable forecast shape even with no sunshine data.

        Sunshine fields are null (not absent) when sunshine data is missing.
        """
        result = build_daily_data(
            weather_data=_weather_envelope(),
            target_date=date(2026, 3, 16),
        )
        day = result["forecast"][0]
        assert day["sunshine_hours"] is None
        assert day["daylight_hours"] is None
        assert day["sunshine_pct"] is None
        assert day["weather_code"] is not None

    def test_forecast_day_rejects_missing_required(self) -> None:
        import pytest  # noqa: PLC0415
        from pydantic import ValidationError  # noqa: PLC0415

        with pytest.raises(ValidationError):
            # date and is_good_day are required
            DailyForecastDay.model_validate({"high_c": 10.0})


# =============================================================================
# JSON Schema exported as a build artifact (#66 deliverable)
# =============================================================================


class TestSchemaBuildArtifact:
    """build.py must write daily-data.schema.json next to today.json."""

    def test_write_daily_schema_produces_valid_json(self, tmp_path: Any) -> None:
        from butterfly_planner.flows import build  # noqa: PLC0415

        # Point the store at a temp dir so we don't touch real data/
        monkey_store = build.DataStore(tmp_path)
        original = build.store
        build.store = monkey_store
        try:
            # Call the undecorated function to avoid the Prefect engine
            schema_path = build.write_daily_schema.fn()
        finally:
            build.store = original

        assert schema_path.exists()
        assert schema_path.name == "daily-data.schema.json"
        # Written next to where today.json lives (derived/daily/)
        assert schema_path.parent.name == "daily"

        # File is valid JSON and a usable JSON Schema
        loaded = json.loads(schema_path.read_text())
        assert "properties" in loaded
        assert "version" in loaded["properties"]
        assert loaded == DailyData.model_json_schema()
