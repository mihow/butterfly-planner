"""Weather utility functions for renderers.

Pure conversion functions with no external dependencies.
"""

from __future__ import annotations

# WMO Weather Interpretation Codes (https://open-meteo.com/en/docs)
WMO_CONDITIONS: dict[int, str] = {
    0: "\u2600\ufe0f Clear",
    1: "\U0001f324\ufe0f Mostly Clear",
    2: "\u26c5 Partly Cloudy",
    3: "\u2601\ufe0f Overcast",
    45: "\U0001f32b\ufe0f Fog",
    48: "\U0001f32b\ufe0f Freezing Fog",
    51: "\U0001f326\ufe0f Light Drizzle",
    53: "\U0001f326\ufe0f Drizzle",
    55: "\U0001f326\ufe0f Heavy Drizzle",
    56: "\U0001f9ca Light Freezing Drizzle",
    57: "\U0001f9ca Freezing Drizzle",
    61: "\U0001f327\ufe0f Light Rain",
    63: "\U0001f327\ufe0f Rain",
    65: "\U0001f327\ufe0f Heavy Rain",
    66: "\U0001f9ca Light Freezing Rain",
    67: "\U0001f9ca Freezing Rain",
    71: "\U0001f328\ufe0f Light Snow",
    73: "\U0001f328\ufe0f Snow",
    75: "\U0001f328\ufe0f Heavy Snow",
    77: "\U0001f328\ufe0f Snow Grains",
    80: "\U0001f326\ufe0f Light Showers",
    81: "\U0001f327\ufe0f Showers",
    82: "\U0001f327\ufe0f Heavy Showers",
    85: "\U0001f328\ufe0f Light Snow Showers",
    86: "\U0001f328\ufe0f Snow Showers",
    95: "\u26c8\ufe0f Thunderstorm",
    96: "\u26c8\ufe0f Thunderstorm w/ Hail",
    99: "\u26c8\ufe0f Heavy Thunderstorm",
}


def c_to_f(celsius: float) -> float:
    """Convert Celsius to Fahrenheit."""
    return celsius * 9 / 5 + 32


def wmo_code_to_conditions(code: int) -> str:
    """Convert a WMO weather code to a human-readable condition string."""
    return WMO_CONDITIONS.get(code, f"Unknown ({code})")
