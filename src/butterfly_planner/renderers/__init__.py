"""Pure rendering functions: structured data -> HTML strings.

All renderers follow the same pattern:
  - Input: dict or dataclass (from analysis/ or store)
  - Output: str (HTML fragment, not a full page)
  - No side effects, no I/O, no Prefect decorators

Used by flows/build.py which orchestrates the rendering pipeline.

Public API:
  - sunshine: build_sunshine_today_html, build_sunshine_16day_html
  - sightings_map: build_butterfly_map_html
  - sightings_table: build_butterfly_sightings_html
  - gdd: build_gdd_today_html, build_gdd_timeline_html
  - species_palette: SpeciesStyle, build_species_palette
  - weather_utils: c_to_f, wmo_code_to_conditions

Adding a renderer (UI module)
-----------------------------
1. Create ``renderers/{name}.py`` with a build function::

       from butterfly_planner.renderers import render_template

       def build_mywidget_html(data: dict[str, Any]) -> str:
           # Extract and transform data for display
           rows = [...]
           return render_template("mywidget.html.j2", rows=rows)

2. Create a Jinja2 template in ``templates/{name}.html.j2``.
   Templates produce HTML fragments (no <html>/<body> tags).
   CSS goes in ``templates/base.html.j2`` within the <style> block.

3. Wire into ``flows/build.py``:
   - Import your build function.
   - Call it in ``build_html()`` and pass the result to
     ``render_template("base.html.j2", ..., mywidget_html=result)``.
   - Add the ``{{ mywidget_html }}`` placeholder in ``base.html.j2``.

4. Add tests: call your build function with sample data and assert
   the returned HTML contains expected content.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import jinja2

# Shared Jinja2 environment for all renderers
_TEMPLATE_DIR = Path(__file__).resolve().parent.parent / "templates"
_jinja_env = jinja2.Environment(
    loader=jinja2.FileSystemLoader(str(_TEMPLATE_DIR)),
    autoescape=True,
)


def render_template(template_name: str, **kwargs: Any) -> str:
    """Render a Jinja2 template by name."""
    return _jinja_env.get_template(template_name).render(**kwargs)
