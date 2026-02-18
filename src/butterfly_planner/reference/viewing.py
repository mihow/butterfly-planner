"""Butterfly viewing condition thresholds."""

# Minimum sunshine for a "good butterfly day" in the 16-day forecast.
# A day is highlighted if EITHER threshold is met.
MIN_GOOD_SUNSHINE_HOURS: float = 3.0
MIN_GOOD_SUNSHINE_PCT: float = 40.0

# Observation date window relative to today.
# Show sightings from 14 days ago through 7 days from now.
OBS_WINDOW_DAYS_BACK: int = 14
OBS_WINDOW_DAYS_AHEAD: int = 7
