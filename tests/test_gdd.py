"""Tests for the GDD (Growing Degree Days) module.

Covers:
- Core computation functions (pure math, no I/O)
- Data structure behavior
- Normals computation
- Species observation correlation
- Rendering functions (in renderers.gdd)
- JSON serialization helpers
"""

from __future__ import annotations

from datetime import date
from unittest.mock import MagicMock

import pytest

import butterfly_planner.renderers.gdd as gdd_renderer
from butterfly_planner.gdd import (
    DailyGDD,
    DayOfYearStats,
    SpeciesGDDProfile,
    YearGDD,
    compute_accumulated_gdd,
    compute_daily_gdd,
    compute_normals,
    correlate_observations_with_gdd,
    normals_to_dict,
    species_profiles_to_dict,
    year_gdd_to_dict,
)
from butterfly_planner.renderers.gdd import (
    _round_up_nice,
    build_gdd_timeline_html,
    build_gdd_today_html,
)

# =============================================================================
# compute_daily_gdd
# =============================================================================


class TestComputeDailyGDD:
    """Tests for the single-day GDD computation."""

    def test_basic_warm_day(self):
        """A warm day should produce positive GDD."""
        # (72 + 48) / 2 = 60; capped tmin to 50 → (72 + 50) / 2 = 61 → 61 - 50 = 11
        result = compute_daily_gdd(tmax_f=72.0, tmin_f=48.0)
        assert result == pytest.approx(11.0)

    def test_cold_day_zero_gdd(self):
        """A day where both temps are below the base should produce 0 GDD."""
        result = compute_daily_gdd(tmax_f=45.0, tmin_f=35.0)
        assert result == 0.0

    def test_upper_cutoff_applied(self):
        """Temps above the upper cutoff should be capped."""
        # Without cutoff: (95 + 60) / 2 - 50 = 27.5
        # With cutoff: tmax capped to 86, tmin raised to 50 → (86 + 60) / 2 - 50 = 23
        result = compute_daily_gdd(tmax_f=95.0, tmin_f=60.0)
        assert result == pytest.approx(23.0)

    def test_tmin_below_base_raised(self):
        """tmin below the base temp should be raised to the base."""
        # tmin 40 → raised to 50; (70 + 50) / 2 - 50 = 10
        result = compute_daily_gdd(tmax_f=70.0, tmin_f=40.0)
        assert result == pytest.approx(10.0)

    def test_both_thresholds_applied(self):
        """Both upper cutoff and lower base should be applied simultaneously."""
        # tmax 100 → capped to 86; tmin 30 → raised to 50
        # (86 + 50) / 2 - 50 = 18
        result = compute_daily_gdd(tmax_f=100.0, tmin_f=30.0)
        assert result == pytest.approx(18.0)

    def test_exact_base_temp(self):
        """Day at exactly the base temperature should produce 0 GDD."""
        result = compute_daily_gdd(tmax_f=50.0, tmin_f=50.0)
        assert result == 0.0

    def test_custom_base_and_cutoff(self):
        """Custom base/cutoff parameters should be respected."""
        # base=40, cutoff=80; (70 + 50) / 2 - 40 = 20
        result = compute_daily_gdd(tmax_f=70.0, tmin_f=50.0, base_temp_f=40.0, upper_cutoff_f=80.0)
        assert result == pytest.approx(20.0)

    def test_result_never_negative(self):
        """GDD should never be negative regardless of inputs."""
        result = compute_daily_gdd(tmax_f=-10.0, tmin_f=-20.0)
        assert result == 0.0


# =============================================================================
# compute_accumulated_gdd
# =============================================================================


class TestComputeAccumulatedGDD:
    """Tests for the accumulated GDD computation."""

    def test_empty_input(self):
        """Empty input should return empty list."""
        assert compute_accumulated_gdd([]) == []

    def test_single_day(self):
        """Single day should have accumulated == daily."""
        temps = [(date(2026, 1, 15), 70.0, 40.0)]
        result = compute_accumulated_gdd(temps)
        assert len(result) == 1
        assert result[0].gdd == result[0].accumulated

    def test_accumulation_is_monotonic(self):
        """Accumulated GDD should be monotonically non-decreasing."""
        temps = [
            (date(2026, 6, 1), 80.0, 55.0),
            (date(2026, 6, 2), 45.0, 35.0),  # cold day, 0 GDD
            (date(2026, 6, 3), 75.0, 60.0),
        ]
        result = compute_accumulated_gdd(temps)
        for i in range(1, len(result)):
            assert result[i].accumulated >= result[i - 1].accumulated

    def test_accumulated_sum_matches(self):
        """Total accumulated should equal sum of daily GDD values."""
        temps = [
            (date(2026, 1, 1), 60.0, 45.0),
            (date(2026, 1, 2), 70.0, 50.0),
            (date(2026, 1, 3), 55.0, 40.0),
        ]
        result = compute_accumulated_gdd(temps)
        total_daily = sum(r.gdd for r in result)
        assert result[-1].accumulated == pytest.approx(total_daily)

    def test_preserves_dates(self):
        """Output should preserve input dates in order."""
        temps = [
            (date(2026, 3, 1), 60.0, 45.0),
            (date(2026, 3, 2), 65.0, 50.0),
        ]
        result = compute_accumulated_gdd(temps)
        assert result[0].date == date(2026, 3, 1)
        assert result[1].date == date(2026, 3, 2)


# =============================================================================
# YearGDD
# =============================================================================


class TestYearGDD:
    """Tests for the YearGDD data structure."""

    def test_total_empty(self):
        """Empty YearGDD should have 0 total."""
        yg = YearGDD(year=2026)
        assert yg.total == 0.0

    def test_total_from_last_entry(self):
        """Total should come from the last daily entry's accumulated value."""
        yg = YearGDD(
            year=2026,
            daily=[
                DailyGDD(date=date(2026, 1, 1), tmax_f=60, tmin_f=45, gdd=5, accumulated=5),
                DailyGDD(date=date(2026, 1, 2), tmax_f=70, tmin_f=50, gdd=10, accumulated=15),
            ],
        )
        assert yg.total == 15.0

    def test_accumulated_through_doy(self):
        """Should return accumulated GDD for a specific day-of-year."""
        yg = YearGDD(
            year=2026,
            daily=[
                DailyGDD(date=date(2026, 1, 1), tmax_f=60, tmin_f=45, gdd=5, accumulated=5),
                DailyGDD(date=date(2026, 1, 2), tmax_f=70, tmin_f=50, gdd=10, accumulated=15),
            ],
        )
        assert yg.accumulated_through_doy(1) == 5.0
        assert yg.accumulated_through_doy(2) == 15.0

    def test_accumulated_through_doy_missing(self):
        """Should return 0.0 for a day-of-year not in the data."""
        yg = YearGDD(year=2026, daily=[])
        assert yg.accumulated_through_doy(100) == 0.0


# =============================================================================
# compute_normals
# =============================================================================


class TestComputeNormals:
    """Tests for GDD normals computation across multiple years."""

    def test_single_year(self):
        """Single year should produce normals with 0 stddev."""
        yg = YearGDD(
            year=2025,
            daily=[
                DailyGDD(date=date(2025, 1, 1), tmax_f=60, tmin_f=45, gdd=5, accumulated=5),
                DailyGDD(date=date(2025, 1, 2), tmax_f=70, tmin_f=50, gdd=10, accumulated=15),
            ],
        )
        stats = compute_normals([yg])
        assert len(stats) == 2
        assert stats[0].doy == 1
        assert stats[0].mean_accumulated == 5.0
        assert stats[0].stddev == 0.0

    def test_multiple_years_mean(self):
        """Mean should average accumulated values across years for same DOY."""
        yg1 = YearGDD(
            year=2024,
            daily=[DailyGDD(date=date(2024, 1, 1), tmax_f=60, tmin_f=45, gdd=5, accumulated=5)],
        )
        yg2 = YearGDD(
            year=2025,
            daily=[DailyGDD(date=date(2025, 1, 1), tmax_f=70, tmin_f=50, gdd=10, accumulated=10)],
        )
        stats = compute_normals([yg1, yg2])
        assert stats[0].mean_accumulated == pytest.approx(7.5)
        assert stats[0].stddev > 0

    def test_empty_input(self):
        """No data should return empty normals."""
        assert compute_normals([]) == []


# =============================================================================
# correlate_observations_with_gdd
# =============================================================================


class TestCorrelateObservationsWithGDD:
    """Tests for cross-referencing observations with GDD values."""

    def _make_year_gdd(self) -> dict[int, YearGDD]:
        """Build a simple year lookup for testing."""
        return {
            2025: YearGDD(
                year=2025,
                daily=[
                    DailyGDD(
                        date=date(2025, 6, 1),
                        tmax_f=80,
                        tmin_f=55,
                        gdd=15,
                        accumulated=500,
                    ),
                    DailyGDD(
                        date=date(2025, 7, 1),
                        tmax_f=85,
                        tmin_f=60,
                        gdd=18,
                        accumulated=800,
                    ),
                ],
            ),
        }

    def test_basic_correlation(self):
        """Observations should be correlated with the GDD on their date."""
        observations = [
            {"species": "Danaus plexippus", "common_name": "Monarch", "observed_on": "2025-06-01"},
            {"species": "Danaus plexippus", "common_name": "Monarch", "observed_on": "2025-07-01"},
            {"species": "Danaus plexippus", "common_name": "Monarch", "observed_on": "2025-06-01"},
        ]
        profiles = correlate_observations_with_gdd(observations, self._make_year_gdd())
        assert "Danaus plexippus" in profiles
        p = profiles["Danaus plexippus"]
        assert p.observation_count == 3
        assert p.gdd_min == 500.0
        assert p.gdd_max == 800.0

    def test_insufficient_observations_skipped(self):
        """Species with fewer than 3 observations should be skipped."""
        observations = [
            {"species": "Rare species", "common_name": "Rare", "observed_on": "2025-06-01"},
            {"species": "Rare species", "common_name": "Rare", "observed_on": "2025-07-01"},
        ]
        profiles = correlate_observations_with_gdd(observations, self._make_year_gdd())
        assert "Rare species" not in profiles

    def test_missing_year_skipped(self):
        """Observations from years not in the lookup should be skipped."""
        observations = [
            {"species": "Sp", "common_name": "Sp", "observed_on": "2020-06-01"},
            {"species": "Sp", "common_name": "Sp", "observed_on": "2020-06-02"},
            {"species": "Sp", "common_name": "Sp", "observed_on": "2020-06-03"},
        ]
        profiles = correlate_observations_with_gdd(observations, self._make_year_gdd())
        assert len(profiles) == 0

    def test_empty_observations(self):
        """Empty observations should return empty profiles."""
        profiles = correlate_observations_with_gdd([], self._make_year_gdd())
        assert profiles == {}


# =============================================================================
# JSON serialization
# =============================================================================


class TestSerialization:
    """Tests for JSON serialization helpers."""

    def test_year_gdd_to_dict(self):
        """Should serialize YearGDD with rounded values."""
        yg = YearGDD(
            year=2026,
            daily=[
                DailyGDD(
                    date=date(2026, 1, 1),
                    tmax_f=60.123,
                    tmin_f=45.456,
                    gdd=5.789,
                    accumulated=5.789,
                ),
            ],
        )
        d = year_gdd_to_dict(yg)
        assert d["year"] == 2026
        assert d["total_gdd"] == 5.8
        assert d["daily"][0]["tmax"] == 60.1
        assert d["daily"][0]["date"] == "2026-01-01"

    def test_normals_to_dict(self):
        """Should serialize normals with year range."""
        stats = [DayOfYearStats(doy=1, mean_accumulated=5.123, stddev=1.456)]
        d = normals_to_dict(stats, "1996-2025")
        assert d["year_range"] == "1996-2025"
        assert d["by_doy"][0]["doy"] == 1
        assert d["by_doy"][0]["mean_accumulated"] == 5.1

    def test_species_profiles_to_dict(self):
        """Should serialize profiles sorted by median GDD."""
        profiles = {
            "Late": SpeciesGDDProfile(
                scientific_name="Late",
                common_name="Late Sp",
                observation_count=10,
                gdd_min=500,
                gdd_p10=550,
                gdd_median=700,
                gdd_p90=850,
                gdd_max=900,
            ),
            "Early": SpeciesGDDProfile(
                scientific_name="Early",
                common_name="Early Sp",
                observation_count=20,
                gdd_min=100,
                gdd_p10=150,
                gdd_median=300,
                gdd_p90=450,
                gdd_max=500,
            ),
        }
        result = species_profiles_to_dict(profiles)
        assert len(result) == 2
        assert result[0]["scientific_name"] == "Early"  # Lower median first
        assert result[1]["scientific_name"] == "Late"


# =============================================================================
# Rendering
# =============================================================================


class TestRendering:
    """Tests for GDD HTML rendering functions."""

    @pytest.fixture
    def sample_gdd_data(self) -> dict:
        """Sample GDD data structure as saved to gdd.json."""
        return {
            "fetched_at": "2026-02-13T10:00:00",
            "source": "open-meteo.com (archive)",
            "data": {
                "location": {"lat": 45.5, "lon": -122.6},
                "base_temp_f": 50.0,
                "upper_cutoff_f": 86.0,
                "current_year": {
                    "year": 2026,
                    "total_gdd": 42.5,
                    "daily": [
                        {
                            "date": "2026-01-01",
                            "tmax": 48.0,
                            "tmin": 35.0,
                            "gdd": 0.0,
                            "accumulated": 0.0,
                        },
                        {
                            "date": "2026-01-15",
                            "tmax": 55.0,
                            "tmin": 42.0,
                            "gdd": 2.5,
                            "accumulated": 10.0,
                        },
                        {
                            "date": "2026-02-12",
                            "tmax": 58.0,
                            "tmin": 45.0,
                            "gdd": 4.0,
                            "accumulated": 42.5,
                        },
                    ],
                },
                "previous_year": {
                    "year": 2025,
                    "total_gdd": 1200.0,
                    "daily": [
                        {
                            "date": "2025-01-01",
                            "tmax": 45.0,
                            "tmin": 33.0,
                            "gdd": 0.0,
                            "accumulated": 0.0,
                        },
                        {
                            "date": "2025-02-12",
                            "tmax": 52.0,
                            "tmin": 40.0,
                            "gdd": 1.0,
                            "accumulated": 35.0,
                        },
                        {
                            "date": "2025-12-31",
                            "tmax": 42.0,
                            "tmin": 30.0,
                            "gdd": 0.0,
                            "accumulated": 1200.0,
                        },
                    ],
                },
            },
        }

    @pytest.fixture
    def mock_render(self, monkeypatch: pytest.MonkeyPatch) -> MagicMock:
        """Mock render_template in renderers.gdd module."""

        def _render(template_name: str, **kwargs):
            return f"<rendered:{template_name}>"

        mock = MagicMock(side_effect=_render)
        monkeypatch.setattr(gdd_renderer, "render_template", mock)
        return mock

    def test_build_gdd_today_html_calls_template(self, sample_gdd_data, mock_render):
        """Should call the render function with the correct template."""
        result = build_gdd_today_html(sample_gdd_data)
        mock_render.assert_called_once()
        args = mock_render.call_args
        assert args[0][0] == "gdd_today.html.j2"
        assert "rendered" in result

    def test_build_gdd_today_html_passes_values(self, sample_gdd_data, mock_render):
        """Should pass correct GDD values to the template."""
        build_gdd_today_html(sample_gdd_data)
        kwargs = mock_render.call_args[1]
        assert kwargs["base_temp"] == 50
        assert kwargs["current_gdd"] == "42"
        assert kwargs["previous_year"] == 2025

    def test_build_gdd_today_html_status_comparison(self, sample_gdd_data, mock_render):
        """Should produce a status comparison against last year."""
        build_gdd_today_html(sample_gdd_data)
        kwargs = mock_render.call_args[1]
        # Status text should contain a comparison (ahead/behind/tracking)
        assert any(
            word in kwargs["status_text"].lower() for word in ("ahead", "behind", "tracking")
        )

    def test_build_gdd_timeline_html_calls_template(self, sample_gdd_data, mock_render):
        """Should call the render function with the timeline template."""
        result = build_gdd_timeline_html(sample_gdd_data)
        mock_render.assert_called_once()
        args = mock_render.call_args
        assert args[0][0] == "gdd_timeline.html.j2"
        assert "rendered" in result

    def test_build_gdd_timeline_html_has_polylines(self, sample_gdd_data, mock_render):
        """Should generate polyline point strings for current and previous year."""
        build_gdd_timeline_html(sample_gdd_data)
        kwargs = mock_render.call_args[1]
        assert len(kwargs["current_year_points"]) > 0
        assert len(kwargs["previous_year_points"]) > 0

    def test_build_gdd_timeline_html_with_normals(self, sample_gdd_data, mock_render):
        """Should include normal band when normals are provided."""
        normals = [
            DayOfYearStats(doy=1, mean_accumulated=0.0, stddev=0.0),
            DayOfYearStats(doy=43, mean_accumulated=30.0, stddev=10.0),
        ]
        build_gdd_timeline_html(
            sample_gdd_data,
            normals=normals,
            normal_year_range="1996-2025",
        )
        kwargs = mock_render.call_args[1]
        assert len(kwargs["normal_band_points"]) > 0
        assert kwargs["normal_range"] == "1996-2025"

    def test_build_gdd_today_no_data(self, mock_render):
        """Should handle missing data gracefully."""
        empty_data = {"data": {}}
        build_gdd_today_html(empty_data)
        mock_render.assert_called_once()
        kwargs = mock_render.call_args[1]
        assert kwargs["current_gdd"] == "0"


# =============================================================================
# Utility
# =============================================================================


class TestRoundUpNice:
    """Tests for the axis-rounding utility."""

    def test_small_values(self):
        assert _round_up_nice(50) == 100
        assert _round_up_nice(100) == 100
        assert _round_up_nice(150) == 200

    def test_medium_values(self):
        assert _round_up_nice(450) == 500
        assert _round_up_nice(800) == 1000

    def test_large_values(self):
        assert _round_up_nice(1800) == 2000
        assert _round_up_nice(4500) == 5000

    def test_zero_or_negative(self):
        assert _round_up_nice(0) == 100
        assert _round_up_nice(-50) == 100

    def test_beyond_range(self):
        result = _round_up_nice(6000)
        assert result >= 6000
