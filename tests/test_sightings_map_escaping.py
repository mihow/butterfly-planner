"""
Tests for safe JS/JSON embedding in sightings_map renderer.

Adversarial test suite: verifies that user/data-derived strings injected into
the <script> block cannot break the JS context or enable XSS.

Covers #31 (manual string escaping -> json.dumps) and associated CVEs for:
  - </script> tag injection
  - Embedded newlines (raw newlines break a JS string literal)
  - U+2028 / U+2029 (line/paragraph separators; invalid unescaped in JS)
  - Single/double quotes
  - Backslash injection
"""

from __future__ import annotations

import json
import re

import pytest

from butterfly_planner.renderers.sightings_map import build_butterfly_map_html

# U+2028 LINE SEPARATOR and U+2029 PARAGRAPH SEPARATOR as string constants so
# ruff RUF001 does not flag ambiguous literal characters in the source.
_LS = chr(0x2028)
_PS = chr(0x2029)


def _make_inat(common_name: str, species: str = "Vanessa cardui") -> dict:
    """Build a minimal iNat payload with a single observation using the given name."""
    return {
        "data": {
            "date_start": "2026-06-01",
            "date_end": "2026-06-15",
            "species": [
                {
                    "taxon_id": 1,
                    "scientific_name": species,
                    "common_name": common_name,
                    "observation_count": 1,
                }
            ],
            "observations": [
                {
                    "id": 1,
                    "species": species,
                    "common_name": common_name,
                    "observed_on": "2026-06-10",
                    "latitude": 45.52,
                    "longitude": -122.68,
                    "quality_grade": "research",
                    "url": "https://www.inaturalist.org/observations/1",
                    "photo_url": None,
                }
            ],
        }
    }


def _extract_markers_json(map_script: str) -> list[dict]:
    """
    Extract the JSON array from ``var obs = <array>;`` in the rendered script.

    Raises ValueError if the pattern is not found or the JSON is invalid.
    """
    match = re.search(r"var obs\s*=\s*(\[.*?\]);", map_script, re.DOTALL)
    if not match:
        raise ValueError(f"Could not find 'var obs = [...]' in script:\n{map_script[:500]}")
    return json.loads(match.group(1))


class TestScriptTagInjection:
    """Ensure </script> in data does not close the enclosing script block."""

    @pytest.mark.parametrize(
        "name",
        [
            "</script>",
            "</script><script>alert(1)</script>",
            "</SCRIPT>",
            "</ script>",
            "</script\n>",
        ],
    )
    def test_no_premature_script_close(self, name: str) -> None:
        """The rendered HTML must not contain a bare </script> that closes the block."""
        _, map_script = build_butterfly_map_html(_make_inat(name))
        # The only valid </script> should be the one closing the template block
        # itself. The injected name must NOT produce an unescaped </script>
        # inside the JSON.
        script_close_count = map_script.lower().count("</script>")
        assert script_close_count <= 1, (
            f"Found {script_close_count} </script> occurrences with name={name!r}"
        )
        # Also assert the injected value appears escaped in the JSON
        markers = _extract_markers_json(map_script)
        assert markers[0]["name"] == name, "Round-trip through JSON must preserve the name"

    def test_script_tag_value_survives_roundtrip(self) -> None:
        """The raw </script> value must parse back correctly from the JSON."""
        name = "</script>"
        _, map_script = build_butterfly_map_html(_make_inat(name))
        markers = _extract_markers_json(map_script)
        assert markers[0]["name"] == name


class TestNewlineEmbedding:
    """Embedded newlines must not break the JS string literal."""

    @pytest.mark.parametrize(
        "name",
        [
            "Painted\nLady",
            "Painted\rLady",
            "Painted\r\nLady",
        ],
    )
    def test_newline_in_name(self, name: str) -> None:
        """Newlines in the name must be escaped so the JSON is valid."""
        _, map_script = build_butterfly_map_html(_make_inat(name))
        markers = _extract_markers_json(map_script)
        assert markers[0]["name"] == name, "Newline chars must survive round-trip"


class TestUnicodeSeparators:
    """U+2028 and U+2029 are line/paragraph separators, illegal unescaped in JS."""

    @pytest.mark.parametrize(
        "name",
        [
            f"Painted{_LS}Lady",  # LINE SEPARATOR
            f"Painted{_PS}Lady",  # PARAGRAPH SEPARATOR
            f"{_LS}{_PS}Both",
        ],
    )
    def test_unicode_separators_escaped(self, name: str) -> None:
        """U+2028/U+2029 must appear as \\u2028/\\u2029 in the rendered script."""
        _, map_script = build_butterfly_map_html(_make_inat(name))
        # The raw characters must NOT appear in the script source
        assert _LS not in map_script, "Raw U+2028 found in script -- must be escaped"
        assert _PS not in map_script, "Raw U+2029 found in script -- must be escaped"
        # But the value must round-trip correctly
        markers = _extract_markers_json(map_script)
        assert markers[0]["name"] == name


class TestQuoteAndBackslashEscaping:
    """Single/double quotes and backslashes must not break the JSON string."""

    @pytest.mark.parametrize(
        "name",
        [
            'Say "hello"',
            "It's alive",
            "Both ' and \"",
            "Back\\slash",
            'Back\\slash and "quotes"',
            "\\'\\\"",  # already-escaped characters
        ],
    )
    def test_quotes_and_backslash(self, name: str) -> None:
        """Quotes and backslashes must survive round-trip without breaking JSON."""
        _, map_script = build_butterfly_map_html(_make_inat(name))
        markers = _extract_markers_json(map_script)
        assert markers[0]["name"] == name


class TestCombinedAdversarialInput:
    """Combined adversarial string with multiple attack vectors."""

    def test_combined_attack_string(self) -> None:
        """A name combining all attack vectors must render safely."""
        name = f"</script><script>alert(1)</script>\n\r{_LS}{_PS}\"'\\xss"
        _, map_script = build_butterfly_map_html(_make_inat(name))

        # No bare </script> break (only the template's own closing tag allowed)
        assert map_script.lower().count("</script>") <= 1

        # No raw U+2028/U+2029
        assert _LS not in map_script
        assert _PS not in map_script

        # Round-trip
        markers = _extract_markers_json(map_script)
        assert markers[0]["name"] == name

    def test_adversarial_weather_html(self) -> None:
        """Weather HTML (another injected string) must also be escaped properly."""
        name = "Normal Butterfly"
        weather = {
            "high_c": 22.0,
            "low_c": 10.0,
            "precip_mm": 0.0,
            "weather_code": 0,
        }
        inat_data = _make_inat(name)
        # Inject weather via obs enrichment
        inat_data["data"]["observations"][0]["weather"] = weather
        _, map_script = build_butterfly_map_html(inat_data)
        # Weather appears in the JSON under "weather" key
        markers = _extract_markers_json(map_script)
        assert isinstance(markers[0].get("weather"), str)
        # Script must remain parseable (no premature close)
        assert map_script.lower().count("</script>") <= 1
