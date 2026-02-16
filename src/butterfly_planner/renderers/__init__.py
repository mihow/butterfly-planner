"""Pure rendering functions: structured data -> HTML strings.

All renderers follow the same pattern:
  - Input: dict or dataclass (from analysis/ or store)
  - Output: str (HTML fragment)
  - No side effects, no I/O, no Prefect decorators

Used by flows/build.py which orchestrates the rendering pipeline.

Public API:
  - sunshine: build_sunshine_today_html, build_sunshine_16day_html
  - sightings_map: build_butterfly_map_html
  - sightings_table: build_butterfly_sightings_html
  - gdd: build_gdd_today_html, build_gdd_timeline_html
  - species_palette: SpeciesStyle, build_species_palette
  - weather_utils: c_to_f, wmo_code_to_conditions
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import jinja2

# Shared Jinja2 environment for all renderers
_TEMPLATE_DIR = Path(__file__).resolve().parent.parent / "templates"
_jinja_env = jinja2.Environment(
    loader=jinja2.FileSystemLoader(str(_TEMPLATE_DIR)),
    autoescape=False,  # We produce trusted HTML fragments
)


def render_template(template_name: str, **kwargs: Any) -> str:
    """Render a Jinja2 template by name."""
    return _jinja_env.get_template(template_name).render(**kwargs)
