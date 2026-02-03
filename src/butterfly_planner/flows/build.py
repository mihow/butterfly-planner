"""
Prefect flow for building static site from raw data.

Transforms raw data into HTML pages for GitHub Pages.

Run locally:
    python -m butterfly_planner.flows.build
"""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path

# Directories
DATA_DIR = Path("data")
RAW_DIR = DATA_DIR / "raw"
SITE_DIR = Path("site")

HTML_TEMPLATE = """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Butterfly Planner - Weather</title>
    <style>
        body {{ font-family: system-ui, sans-serif; max-width: 800px; margin: 2rem auto; padding: 0 1rem; }}
        h1 {{ color: #2d5016; }}
        table {{ border-collapse: collapse; width: 100%; }}
        th, td {{ border: 1px solid #ddd; padding: 8px; text-align: left; }}
        th {{ background: #f5f5f5; }}
        .meta {{ color: #666; font-size: 0.9rem; }}
        .temp-high {{ color: #c00; }}
        .temp-low {{ color: #00c; }}
    </style>
</head>
<body>
    <h1>🦋 Butterfly Planner</h1>
    <p class="meta">Weather forecast for Portland, OR | Last updated: {updated}</p>

    <h2>7-Day Forecast</h2>
    <table>
        <tr>
            <th>Date</th>
            <th>High</th>
            <th>Low</th>
            <th>Precip</th>
        </tr>
        {rows}
    </table>

    <h2>About</h2>
    <p>This is a demo of the data pipeline. The full app will show:</p>
    <ul>
        <li>Butterfly hotspots by week</li>
        <li>Species diversity maps</li>
        <li>Drive-time isochrones</li>
        <li>Nearby campgrounds</li>
    </ul>

    <p class="meta">Data from <a href="https://open-meteo.com">Open-Meteo</a></p>
</body>
</html>
"""


def load_weather() -> dict | None:
    """Load raw weather data."""
    path = RAW_DIR / "weather.json"
    if not path.exists():
        return None
    with open(path) as f:
        return json.load(f)


def build_html(weather_data: dict) -> str:
    """Build HTML page from weather data."""
    data = weather_data["data"]["daily"]
    updated = weather_data["fetched_at"][:16].replace("T", " ")

    rows = []
    for i, date in enumerate(data["time"]):
        high = data["temperature_2m_max"][i]
        low = data["temperature_2m_min"][i]
        precip = data["precipitation_sum"][i]
        rows.append(
            f"<tr><td>{date}</td>"
            f'<td class="temp-high">{high}°C</td>'
            f'<td class="temp-low">{low}°C</td>'
            f"<td>{precip}mm</td></tr>"
        )

    return HTML_TEMPLATE.format(updated=updated, rows="\n        ".join(rows))


def run() -> dict:
    """Main entry point - build static site."""
    SITE_DIR.mkdir(parents=True, exist_ok=True)

    weather = load_weather()
    if not weather:
        print("No weather data found. Run fetch first.")
        return {"error": "no data"}

    print("Building static site...")
    html = build_html(weather)

    output_path = SITE_DIR / "index.html"
    with open(output_path, "w") as f:
        f.write(html)

    print(f"Built {output_path}")
    return {"pages": 1, "output": str(output_path)}


if __name__ == "__main__":
    result = run()
    print(f"Build complete: {result}")
