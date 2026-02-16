"""Sunshine data models."""

from __future__ import annotations

import statistics
from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from datetime import date, datetime


@dataclass
class SunshineSlot:
    """A single 15-minute sunshine measurement."""

    time: datetime
    duration_seconds: int
    is_day: bool

    @property
    def duration_minutes(self) -> float:
        """Duration in minutes (0-15)."""
        return self.duration_seconds / 60

    @property
    def percentage(self) -> float:
        """Percentage of the 15-min slot that was sunny (0-100)."""
        return (self.duration_seconds / 900) * 100  # 900 sec = 15 min


@dataclass
class DailySunshine:
    """Daily sunshine summary."""

    date: date
    sunshine_seconds: int
    daylight_seconds: int

    @property
    def sunshine_hours(self) -> float:
        """Total sunshine in hours."""
        return self.sunshine_seconds / 3600

    @property
    def sunshine_percent(self) -> float:
        """Percentage of daylight that was sunny (0-100)."""
        if self.daylight_seconds == 0:
            return 0.0
        return (self.sunshine_seconds / self.daylight_seconds) * 100

    @property
    def is_good_butterfly_weather(self) -> bool:
        """
        Whether this day has good butterfly viewing conditions.

        Good = >3 hours of sun OR >40% of daylight is sunny.
        """
        return self.sunshine_hours > 3.0 or self.sunshine_percent > 40.0


@dataclass
class EnsembleSunshine:
    """Sunshine forecast with ensemble member statistics."""

    time: datetime
    member_values: list[int]  # sunshine_duration seconds from each ensemble member

    @property
    def mean(self) -> float:
        """Mean sunshine duration across all members (seconds)."""
        return statistics.mean(self.member_values)

    @property
    def std(self) -> float:
        """Standard deviation (seconds)."""
        return statistics.stdev(self.member_values) if len(self.member_values) > 1 else 0.0

    @property
    def min(self) -> int:
        """Minimum value across members."""
        return min(self.member_values)

    @property
    def max(self) -> int:
        """Maximum value across members."""
        return max(self.member_values)

    @property
    def p10(self) -> float:
        """10th percentile (low estimate)."""
        if len(self.member_values) < 2:
            return float(self.member_values[0]) if self.member_values else 0.0
        return statistics.quantiles(self.member_values, n=10)[0]

    @property
    def p50(self) -> float:
        """50th percentile (median)."""
        return statistics.median(self.member_values)

    @property
    def p90(self) -> float:
        """90th percentile (high estimate)."""
        if len(self.member_values) < 2:
            return float(self.member_values[0]) if self.member_values else 0.0
        return statistics.quantiles(self.member_values, n=10)[8]

    @property
    def confidence_width(self) -> float:
        """
        Width of 80% confidence interval (p90 - p10).

        Smaller values indicate higher forecast confidence.
        """
        return self.p90 - self.p10
