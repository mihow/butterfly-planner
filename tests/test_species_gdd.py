"""Tests for species-GDD correlation analysis."""

from __future__ import annotations

import statistics
from datetime import date

from butterfly_planner.analysis.species_gdd import correlate_observations_with_gdd
from butterfly_planner.datasources.gdd.models import DailyGDD, YearGDD


def _make_year_gdd(year: int, daily_gdd: list[float]) -> YearGDD:
    """Build a YearGDD with linearly accumulated GDD values."""
    acc = 0.0
    entries = []
    for doy, gdd in enumerate(daily_gdd, start=1):
        acc += gdd
        entries.append(
            DailyGDD(
                date=date.fromordinal(date(year, 1, 1).toordinal() + doy - 1),
                tmax_f=70.0,
                tmin_f=50.0,
                gdd=gdd,
                accumulated=acc,
            )
        )
    return YearGDD(year=year, daily=entries)


# Build 180 days of GDD (10 per day → accumulated 10, 20, ..., 1800)
YEAR_GDD = _make_year_gdd(2024, [10.0] * 180)
LOOKUP = {2024: YEAR_GDD}


class TestCorrelateObservationsWithGDD:
    """Test correlate_observations_with_gdd."""

    def test_basic_correlation(self) -> None:
        """Test that observations are matched to GDD values."""
        obs = [
            {
                "species": "Vanessa cardui",
                "common_name": "Painted Lady",
                "observed_on": "2024-03-01",
            },
            {
                "species": "Vanessa cardui",
                "common_name": "Painted Lady",
                "observed_on": "2024-04-01",
            },
            {
                "species": "Vanessa cardui",
                "common_name": "Painted Lady",
                "observed_on": "2024-05-01",
            },
        ]
        profiles = correlate_observations_with_gdd(obs, LOOKUP)

        assert "Vanessa cardui" in profiles
        p = profiles["Vanessa cardui"]
        assert p.common_name == "Painted Lady"
        assert p.observation_count == 3
        assert p.gdd_min < p.gdd_median < p.gdd_max

    def test_percentile_correctness(self) -> None:
        """Test that p10/p90 use statistics.quantiles, not index math."""
        # 10 observations on days 10, 20, ..., 100 → GDD 100, 200, ..., 1000
        obs = [
            {
                "species": "Sp A",
                "common_name": "Sp A",
                "observed_on": f"2024-{1 + (i * 10) // 30:02d}-{1 + (i * 10) % 30:02d}",
            }
            for i in range(10)
        ]
        # Use explicit dates to avoid month-boundary issues
        obs = [
            {
                "species": "Sp A",
                "common_name": "Sp A",
                "observed_on": date.fromordinal(
                    date(2024, 1, 1).toordinal() + i * 10 - 1
                ).isoformat(),
            }
            for i in range(1, 11)
        ]
        profiles = correlate_observations_with_gdd(obs, LOOKUP)
        p = profiles["Sp A"]

        # Verify against statistics.quantiles directly
        gdd_vals = sorted(YEAR_GDD.accumulated_through_doy(i * 10) for i in range(1, 11))
        expected_deciles = statistics.quantiles(gdd_vals, n=10, method="inclusive")
        assert p.gdd_p10 == expected_deciles[0]
        assert p.gdd_p90 == expected_deciles[8]

    def test_fewer_than_3_observations_skipped(self) -> None:
        """Test that species with <3 observations are excluded."""
        obs = [
            {"species": "Sp B", "common_name": "Sp B", "observed_on": "2024-02-01"},
            {"species": "Sp B", "common_name": "Sp B", "observed_on": "2024-03-01"},
        ]
        profiles = correlate_observations_with_gdd(obs, LOOKUP)
        assert "Sp B" not in profiles

    def test_missing_year_data(self) -> None:
        """Test that observations without matching year GDD are skipped."""
        obs = [
            {"species": "Sp C", "common_name": "Sp C", "observed_on": "2023-06-01"},
            {"species": "Sp C", "common_name": "Sp C", "observed_on": "2023-06-15"},
            {"species": "Sp C", "common_name": "Sp C", "observed_on": "2023-07-01"},
        ]
        # LOOKUP only has 2024
        profiles = correlate_observations_with_gdd(obs, LOOKUP)
        assert "Sp C" not in profiles

    def test_invalid_date_skipped(self) -> None:
        """Test that observations with invalid dates are silently skipped."""
        obs = [
            {"species": "Sp D", "common_name": "Sp D", "observed_on": "not-a-date"},
            {"species": "Sp D", "common_name": "Sp D", "observed_on": "2024-03-01"},
            {"species": "Sp D", "common_name": "Sp D", "observed_on": "2024-04-01"},
            {"species": "Sp D", "common_name": "Sp D", "observed_on": "2024-05-01"},
        ]
        profiles = correlate_observations_with_gdd(obs, LOOKUP)
        assert profiles["Sp D"].observation_count == 3

    def test_common_name_fallback(self) -> None:
        """Test that scientific name is used when common_name is missing."""
        obs = [
            {"species": "Papilio zelicaon", "observed_on": "2024-03-01"},
            {"species": "Papilio zelicaon", "observed_on": "2024-04-01"},
            {"species": "Papilio zelicaon", "observed_on": "2024-05-01"},
        ]
        profiles = correlate_observations_with_gdd(obs, LOOKUP)
        assert profiles["Papilio zelicaon"].common_name == "Papilio zelicaon"
