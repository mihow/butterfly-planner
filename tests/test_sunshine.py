"""
Tests for the sunshine forecasting module.
"""

from __future__ import annotations

from datetime import date, datetime
from unittest.mock import Mock, patch

import pytest

from butterfly_planner.datasources import sunshine


class TestSunshineSlot:
    """Test SunshineSlot dataclass."""

    def test_duration_minutes(self) -> None:
        """Test conversion from seconds to minutes."""
        slot = sunshine.SunshineSlot(
            time=datetime(2026, 2, 4, 12, 0), duration_seconds=900, is_day=True
        )
        assert slot.duration_minutes == 15.0

        slot = sunshine.SunshineSlot(
            time=datetime(2026, 2, 4, 12, 0), duration_seconds=450, is_day=True
        )
        assert slot.duration_minutes == 7.5

    def test_percentage(self) -> None:
        """Test percentage calculation."""
        slot = sunshine.SunshineSlot(
            time=datetime(2026, 2, 4, 12, 0), duration_seconds=900, is_day=True
        )
        assert slot.percentage == 100.0

        slot = sunshine.SunshineSlot(
            time=datetime(2026, 2, 4, 12, 0), duration_seconds=450, is_day=True
        )
        assert slot.percentage == 50.0

        slot = sunshine.SunshineSlot(
            time=datetime(2026, 2, 4, 12, 0), duration_seconds=0, is_day=False
        )
        assert slot.percentage == 0.0


class TestDailySunshine:
    """Test DailySunshine dataclass."""

    def test_sunshine_hours(self) -> None:
        """Test conversion from seconds to hours."""
        daily = sunshine.DailySunshine(
            date=date(2026, 2, 4), sunshine_seconds=7200, daylight_seconds=36000
        )
        assert daily.sunshine_hours == 2.0

    def test_sunshine_percent(self) -> None:
        """Test percentage calculation."""
        daily = sunshine.DailySunshine(
            date=date(2026, 2, 4), sunshine_seconds=18000, daylight_seconds=36000
        )
        assert daily.sunshine_percent == 50.0

    def test_sunshine_percent_zero_daylight(self) -> None:
        """Test percentage when there's no daylight (edge case)."""
        daily = sunshine.DailySunshine(
            date=date(2026, 2, 4), sunshine_seconds=0, daylight_seconds=0
        )
        assert daily.sunshine_percent == 0.0

    def test_is_good_butterfly_weather_by_hours(self) -> None:
        """Test good weather detection by hours threshold."""
        # >3 hours of sun
        daily = sunshine.DailySunshine(
            date=date(2026, 2, 4), sunshine_seconds=12000, daylight_seconds=36000
        )
        assert daily.is_good_butterfly_weather is True

        # Exactly 3 hours - should be False (need >3)
        daily = sunshine.DailySunshine(
            date=date(2026, 2, 4), sunshine_seconds=10800, daylight_seconds=36000
        )
        assert daily.is_good_butterfly_weather is False

    def test_is_good_butterfly_weather_by_percent(self) -> None:
        """Test good weather detection by percentage threshold."""
        # >40% sunny
        daily = sunshine.DailySunshine(
            date=date(2026, 2, 4), sunshine_seconds=15000, daylight_seconds=36000
        )
        assert daily.sunshine_percent > 40.0
        assert daily.is_good_butterfly_weather is True

        # <40% but still good due to hours
        daily = sunshine.DailySunshine(
            date=date(2026, 2, 4), sunshine_seconds=11000, daylight_seconds=36000
        )
        assert daily.sunshine_percent < 40.0
        assert daily.is_good_butterfly_weather is True  # >3 hours

    def test_is_poor_butterfly_weather(self) -> None:
        """Test poor weather detection."""
        # <3 hours and <40%
        daily = sunshine.DailySunshine(
            date=date(2026, 2, 4), sunshine_seconds=7200, daylight_seconds=36000
        )
        assert daily.sunshine_hours == 2.0
        assert daily.sunshine_percent == 20.0
        assert daily.is_good_butterfly_weather is False


class TestEnsembleSunshine:
    """Test EnsembleSunshine dataclass."""

    def test_statistics(self) -> None:
        """Test statistical calculations."""
        ensemble = sunshine.EnsembleSunshine(
            time=datetime(2026, 2, 4, 12, 0), member_values=[1800, 2100, 1500, 2400, 1800]
        )

        assert ensemble.mean == 1920.0
        assert ensemble.min == 1500
        assert ensemble.max == 2400
        assert ensemble.std > 0  # Should have some variation

    def test_percentiles(self) -> None:
        """Test percentile calculations."""
        # Use 11 values to get clean percentiles
        values = list(range(0, 3600, 360))  # 0, 360, 720, ..., 3240, 3600
        ensemble = sunshine.EnsembleSunshine(time=datetime(2026, 2, 4, 12, 0), member_values=values)

        assert ensemble.p10 < ensemble.p50
        assert ensemble.p50 < ensemble.p90

    def test_confidence_width(self) -> None:
        """Test confidence interval width."""
        # Narrow spread = high confidence
        ensemble = sunshine.EnsembleSunshine(
            time=datetime(2026, 2, 4, 12, 0), member_values=[1800] * 10
        )
        assert ensemble.confidence_width == 0.0

        # Wide spread = low confidence
        ensemble = sunshine.EnsembleSunshine(
            time=datetime(2026, 2, 4, 12, 0), member_values=list(range(0, 3600, 360))
        )
        assert ensemble.confidence_width > 0

    def test_p10_single_element(self) -> None:
        """Test p10 with single element list."""
        ensemble = sunshine.EnsembleSunshine(time=datetime(2026, 2, 4, 12, 0), member_values=[1800])
        assert ensemble.p10 == 1800.0

    def test_p90_single_element(self) -> None:
        """Test p90 with single element list."""
        ensemble = sunshine.EnsembleSunshine(time=datetime(2026, 2, 4, 12, 0), member_values=[1800])
        assert ensemble.p90 == 1800.0

    def test_p10_empty_list(self) -> None:
        """Test p10 with empty list."""
        ensemble = sunshine.EnsembleSunshine(time=datetime(2026, 2, 4, 12, 0), member_values=[])
        assert ensemble.p10 == 0.0

    def test_p90_empty_list(self) -> None:
        """Test p90 with empty list."""
        ensemble = sunshine.EnsembleSunshine(time=datetime(2026, 2, 4, 12, 0), member_values=[])
        assert ensemble.p90 == 0.0


class TestFetchFunctions:
    """Test API fetching functions."""

    @patch("butterfly_planner.datasources.sunshine.today.session.get")
    def test_fetch_today_15min_sunshine(self, mock_get: Mock) -> None:
        """Test fetching 15-minute sunshine data."""
        mock_response = Mock()
        mock_response.json.return_value = {
            "minutely_15": {
                "time": ["2026-02-04T08:00", "2026-02-04T08:15", "2026-02-04T08:30"],
                "sunshine_duration": [0, 450, 900],
                "is_day": [1, 1, 1],
            }
        }
        mock_response.raise_for_status = Mock()
        mock_get.return_value = mock_response

        slots = sunshine.fetch_today_15min_sunshine(lat=45.5, lon=-122.6)

        assert len(slots) == 3
        assert slots[0].duration_seconds == 0
        assert slots[1].duration_seconds == 450
        assert slots[2].duration_seconds == 900
        assert all(s.is_day for s in slots)

        # Verify API call
        mock_get.assert_called_once()
        call_args = mock_get.call_args
        assert call_args.kwargs["params"]["latitude"] == 45.5
        assert call_args.kwargs["params"]["longitude"] == -122.6
        assert call_args.kwargs["params"]["forecast_days"] == 1

    @patch("butterfly_planner.datasources.sunshine.daily.session.get")
    def test_fetch_16day_sunshine(self, mock_get: Mock) -> None:
        """Test fetching 16-day sunshine data."""
        mock_response = Mock()
        mock_response.json.return_value = {
            "daily": {
                "time": ["2026-02-04", "2026-02-05"],
                "sunshine_duration": [18000, 14400],
                "daylight_duration": [36000, 36000],
            }
        }
        mock_response.raise_for_status = Mock()
        mock_get.return_value = mock_response

        forecasts = sunshine.fetch_16day_sunshine(lat=45.5, lon=-122.6)

        assert len(forecasts) == 2
        assert forecasts[0].sunshine_hours == 5.0
        assert forecasts[1].sunshine_hours == 4.0

        # Verify API call
        mock_get.assert_called_once()
        call_args = mock_get.call_args
        assert call_args.kwargs["params"]["forecast_days"] == 16

    @patch("butterfly_planner.datasources.sunshine.ensemble.session.get")
    def test_fetch_ensemble_sunshine(self, mock_get: Mock) -> None:
        """Test fetching ensemble sunshine data."""
        mock_response = Mock()
        mock_response.json.return_value = {
            "hourly": {
                "time": ["2026-02-04T12:00", "2026-02-04T13:00"],
                "sunshine_duration_member00": [1800, 2100],
                "sunshine_duration_member01": [1500, 2400],
                "sunshine_duration_member02": [2100, 1800],
            }
        }
        mock_response.raise_for_status = Mock()
        mock_get.return_value = mock_response

        forecasts = sunshine.fetch_ensemble_sunshine(lat=45.5, lon=-122.6, forecast_days=7)

        assert len(forecasts) == 2
        assert len(forecasts[0].member_values) == 3
        assert forecasts[0].member_values == [1800, 1500, 2100]
        assert forecasts[1].member_values == [2100, 2400, 1800]

        # Verify API call
        mock_get.assert_called_once()
        call_args = mock_get.call_args
        assert "ensemble" in call_args.args[0]
        assert call_args.kwargs["params"]["forecast_days"] == 7


class TestAnalysisFunctions:
    """Test analysis and summary functions."""

    def test_get_daylight_slots(self) -> None:
        """Test filtering to daylight hours."""
        slots = [
            sunshine.SunshineSlot(
                time=datetime(2026, 2, 4, 6, 0), duration_seconds=0, is_day=False
            ),
            sunshine.SunshineSlot(
                time=datetime(2026, 2, 4, 8, 0), duration_seconds=900, is_day=True
            ),
            sunshine.SunshineSlot(
                time=datetime(2026, 2, 4, 12, 0), duration_seconds=900, is_day=True
            ),
            sunshine.SunshineSlot(
                time=datetime(2026, 2, 4, 20, 0), duration_seconds=0, is_day=False
            ),
        ]

        daylight = sunshine.get_daylight_slots(slots)
        assert len(daylight) == 2
        assert all(s.is_day for s in daylight)

    def test_get_total_sunshine_minutes(self) -> None:
        """Test total sunshine calculation."""
        slots = [
            sunshine.SunshineSlot(
                time=datetime(2026, 2, 4, 8, 0), duration_seconds=900, is_day=True
            ),
            sunshine.SunshineSlot(
                time=datetime(2026, 2, 4, 8, 15), duration_seconds=450, is_day=True
            ),
            sunshine.SunshineSlot(
                time=datetime(2026, 2, 4, 8, 30), duration_seconds=900, is_day=True
            ),
        ]

        total = sunshine.get_total_sunshine_minutes(slots)
        assert total == 37.5  # 15 + 7.5 + 15

    def test_get_peak_sunshine_window(self) -> None:
        """Test finding peak sunshine window."""
        # Create hourly slots (4 per hour at 15 min each)
        slots = []
        for hour in range(8, 16):  # 8am to 4pm
            for minute in [0, 15, 30, 45]:
                # Peak at noon
                duration = 900 if 11 <= hour < 14 else 450
                slots.append(
                    sunshine.SunshineSlot(
                        time=datetime(2026, 2, 4, hour, minute),
                        duration_seconds=duration,
                        is_day=True,
                    )
                )

        start_time, total_minutes = sunshine.get_peak_sunshine_window(slots, window_hours=1)

        # Should find the 1-hour window with most sun (around noon)
        assert total_minutes == 60.0  # 4 slots x 15 min each
        assert start_time.hour in [11, 12, 13]  # Peak window

    def test_get_peak_sunshine_window_empty(self) -> None:
        """Test peak window with empty list."""
        with pytest.raises(ValueError, match="Empty slots list"):
            sunshine.get_peak_sunshine_window([], window_hours=1)

    def test_get_peak_sunshine_window_larger_than_slots(self) -> None:
        """Test peak window when window is larger than available slots."""
        # Only 2 slots (30 min total), but requesting 1 hour window
        slots = [
            sunshine.SunshineSlot(
                time=datetime(2026, 2, 4, 12, 0), duration_seconds=900, is_day=True
            ),
            sunshine.SunshineSlot(
                time=datetime(2026, 2, 4, 12, 15), duration_seconds=450, is_day=True
            ),
        ]

        start_time, total_minutes = sunshine.get_peak_sunshine_window(slots, window_hours=1)

        # Should return sum of all available slots
        assert start_time == slots[0].time
        assert total_minutes == 22.5  # 15 + 7.5 minutes

    def test_summarize_weekly_sunshine(self) -> None:
        """Test weekly summary statistics."""
        # Create 16 days of forecasts
        forecasts = []
        for i in range(16):
            # Alternate good and bad days
            sunshine_sec = 14400 if i % 2 == 0 else 7200  # 4h or 2h
            forecasts.append(
                sunshine.DailySunshine(
                    date=date(2026, 2, 4 + i), sunshine_seconds=sunshine_sec, daylight_seconds=36000
                )
            )

        summary = sunshine.summarize_weekly_sunshine(forecasts)

        assert summary["total_days"] == 16
        assert "this_week" in summary
        assert "next_week" in summary

        # This week (0-6): 4 good days (indices 0, 2, 4, 6)
        assert summary["this_week"]["good_days"] == 4
        assert summary["this_week"]["total_days"] == 7

        # Next week (7-13): 3 good days (indices 8, 10, 12)
        assert summary["next_week"]["good_days"] == 3
        assert summary["next_week"]["total_days"] == 7

    def test_summarize_weekly_sunshine_short_list(self) -> None:
        """Test weekly summary with fewer than 14 days."""
        forecasts = []
        for i in range(10):
            forecasts.append(
                sunshine.DailySunshine(
                    date=date(2026, 2, 4 + i), sunshine_seconds=14400, daylight_seconds=36000
                )
            )

        summary = sunshine.summarize_weekly_sunshine(forecasts)

        assert summary["total_days"] == 10
        assert summary["this_week"]["total_days"] == 7
        # Next week only has 3 days (indices 7-9)
        if summary["next_week"]:  # Only check if dict is not empty
            assert summary["next_week"]["total_days"] == 3
