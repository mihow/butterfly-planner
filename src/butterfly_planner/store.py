"""Tiered data store with freshness-aware caching.

Manages read/write of JSON data files organized into tiers by update frequency:
  - reference/: Static data, 90-day TTL (DEMs, species ranges, GeoTIFFs)
  - historical/: Slow-changing, 24h TTL for current periods (GDD normals, past observations)
  - live/: Ephemeral, 1-6h TTL (weather forecast, sunshine, current sightings)
  - derived/: Computed outputs, always recomputed (HTML site, species profiles)

Every JSON file is wrapped in a metadata envelope with ``valid_until`` so the
fetch flow can skip sources that are still fresh.

Binary files (shapefiles, DEMs/GeoTIFFs) use a sidecar ``.meta.json`` pattern
via ``write_file()`` — the data file stays in its native format and freshness
metadata lives alongside it.
"""

from __future__ import annotations

import json
import shutil
from datetime import UTC, datetime
from pathlib import Path  # noqa: TC003 — used at runtime, not just annotations
from typing import Any


class DataStore:
    """Manages read/write of cached data files with TTL."""

    def __init__(self, base_dir: Path) -> None:
        self.base = base_dir
        self.reference = base_dir / "reference"
        self.historical = base_dir / "historical"
        self.live = base_dir / "live"
        self.derived = base_dir / "derived"

    def read(self, path: Path) -> dict[str, Any] | None:
        """Read data payload from a metadata-enveloped JSON file.

        Returns the ``data`` field, or None if the file doesn't exist.
        """
        full = self._resolve(path)
        if not full.exists():
            return None
        with full.open() as f:
            envelope: dict[str, Any] = json.load(f)
        return envelope.get("data", envelope)

    def read_raw(self, path: Path) -> dict[str, Any] | None:
        """Read the full envelope (meta + data) from a JSON file."""
        full = self._resolve(path)
        if not full.exists():
            return None
        with full.open() as f:
            result: dict[str, Any] = json.load(f)
        return result

    def write(
        self,
        path: Path,
        data: Any,
        source: str,
        valid_until: datetime | None = None,
        **params: Any,
    ) -> Path:
        """Write data wrapped in a metadata envelope.

        Args:
            path: Relative path under base_dir (e.g. ``live/weather.json``).
            data: Payload to store under the ``data`` key.
            source: Data source identifier (e.g. ``"open-meteo.com"``).
            valid_until: Expiry timestamp. None means derived/no-cache.
            **params: Extra metadata fields (location, query params, etc.).

        Returns:
            Absolute path of the written file.
        """
        full = self._resolve(path)
        full.parent.mkdir(parents=True, exist_ok=True)

        meta: dict[str, Any] = {
            "source": source,
            "fetched_at": datetime.now(UTC).isoformat(),
        }
        if valid_until is not None:
            meta["valid_until"] = valid_until.isoformat()
        if params:
            meta.update(params)

        envelope = {"meta": meta, "data": data}
        with full.open("w") as f:
            json.dump(envelope, f, indent=2)

        return full

    def write_file(
        self,
        path: Path,
        src: Path,
        source: str,
        valid_until: datetime | None = None,
        **params: Any,
    ) -> Path:
        """Store a binary/non-JSON file with sidecar metadata.

        Copies ``src`` to the store location and writes a ``.meta.json``
        sidecar with freshness metadata. Use for shapefiles, GeoTIFFs, etc.

        Args:
            path: Relative destination path (e.g. ``reference/dem/portland.tif``).
            src: Source file to copy into the store.
            source: Data source identifier.
            valid_until: Expiry timestamp.
            **params: Extra metadata fields.

        Returns:
            Absolute path of the stored file.
        """
        full = self._resolve(path)
        full.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, full)

        meta: dict[str, Any] = {
            "source": source,
            "fetched_at": datetime.now(UTC).isoformat(),
        }
        if valid_until is not None:
            meta["valid_until"] = valid_until.isoformat()
        if params:
            meta.update(params)

        meta_path = full.with_suffix(full.suffix + ".meta.json")
        with meta_path.open("w") as f:
            json.dump({"meta": meta}, f, indent=2)

        return full

    def file_path(self, path: Path) -> Path | None:
        """Return the absolute path of a stored file, or None if missing."""
        full = self._resolve(path)
        return full if full.exists() else None

    def _resolve(self, path: Path) -> Path:
        full = self.base / path if not path.is_absolute() else path
        try:
            full.resolve().relative_to(self.base.resolve())
        except ValueError:
            msg = f"Path escapes store base directory: {path}"
            raise ValueError(msg) from None
        return full

    def _read_meta(self, full: Path) -> dict[str, Any]:
        """Read metadata from either a JSON envelope or a sidecar .meta.json."""
        sidecar = full.with_suffix(full.suffix + ".meta.json")
        if sidecar.exists():
            with sidecar.open() as f:
                result: dict[str, Any] = json.load(f)
            return result.get("meta", {})

        # Fall back to embedded metadata in JSON files
        if full.suffix == ".json" and full.exists():
            with full.open() as f:
                envelope: dict[str, Any] = json.load(f)
            return envelope.get("meta", {})

        return {}

    def is_fresh(self, path: Path) -> bool:
        """Check if a file exists and hasn't expired.

        Works with both JSON envelopes and sidecar .meta.json files.
        Returns False if the file is missing, has no ``valid_until``, or
        the expiry time has passed.
        """
        full = self._resolve(path)
        if not full.exists():
            return False

        meta = self._read_meta(full)
        valid_until = meta.get("valid_until")
        if valid_until is None:
            return False

        expiry = datetime.fromisoformat(valid_until)
        if expiry.tzinfo is None:
            expiry = expiry.replace(tzinfo=UTC)
        return datetime.now(UTC) < expiry
