"""Tests for the DataStore module."""

from __future__ import annotations

import json
from datetime import UTC, datetime, timedelta
from pathlib import Path

from butterfly_planner.store import DataStore


class TestDataStoreInit:
    """Test DataStore initialization."""

    def test_creates_tier_paths(self, tmp_path: Path) -> None:
        store = DataStore(tmp_path)
        assert store.base == tmp_path
        assert store.reference == tmp_path / "reference"
        assert store.historical == tmp_path / "historical"
        assert store.live == tmp_path / "live"
        assert store.derived == tmp_path / "derived"


class TestDataStoreWrite:
    """Test writing data with metadata envelopes."""

    def test_write_creates_file(self, tmp_path: Path) -> None:
        store = DataStore(tmp_path)
        path = store.write(Path("live/weather.json"), {"temp": 20}, source="test")
        assert path.exists()

    def test_write_envelope_format(self, tmp_path: Path) -> None:
        store = DataStore(tmp_path)
        valid = datetime(2026, 3, 1, tzinfo=UTC)
        store.write(Path("live/weather.json"), {"temp": 20}, source="open-meteo", valid_until=valid)

        data = json.loads((tmp_path / "live" / "weather.json").read_text())
        assert "meta" in data
        assert "data" in data
        assert data["meta"]["source"] == "open-meteo"
        assert "fetched_at" in data["meta"]
        assert data["meta"]["valid_until"] == valid.isoformat()
        assert data["data"] == {"temp": 20}

    def test_write_extra_params(self, tmp_path: Path) -> None:
        store = DataStore(tmp_path)
        store.write(
            Path("live/test.json"),
            {},
            source="test",
            location={"lat": 45.5, "lon": -122.6},
        )
        data = json.loads((tmp_path / "live" / "test.json").read_text())
        assert data["meta"]["location"] == {"lat": 45.5, "lon": -122.6}

    def test_write_creates_parent_dirs(self, tmp_path: Path) -> None:
        store = DataStore(tmp_path)
        store.write(Path("historical/gdd/deep/nested.json"), {}, source="test")
        assert (tmp_path / "historical" / "gdd" / "deep" / "nested.json").exists()

    def test_write_no_valid_until(self, tmp_path: Path) -> None:
        store = DataStore(tmp_path)
        store.write(Path("derived/output.json"), {}, source="test")
        data = json.loads((tmp_path / "derived" / "output.json").read_text())
        assert "valid_until" not in data["meta"]


class TestDataStoreRead:
    """Test reading data from the store."""

    def test_read_returns_data_payload(self, tmp_path: Path) -> None:
        store = DataStore(tmp_path)
        store.write(Path("live/test.json"), {"key": "value"}, source="test")
        result = store.read(Path("live/test.json"))
        assert result == {"key": "value"}

    def test_read_missing_file(self, tmp_path: Path) -> None:
        store = DataStore(tmp_path)
        assert store.read(Path("nonexistent.json")) is None

    def test_read_raw_returns_full_envelope(self, tmp_path: Path) -> None:
        store = DataStore(tmp_path)
        store.write(Path("live/test.json"), {"key": "value"}, source="test")
        result = store.read_raw(Path("live/test.json"))
        assert result is not None
        assert "meta" in result
        assert "data" in result
        assert result["data"] == {"key": "value"}

    def test_read_raw_missing_file(self, tmp_path: Path) -> None:
        store = DataStore(tmp_path)
        assert store.read_raw(Path("nonexistent.json")) is None


class TestDataStoreIsFresh:
    """Test freshness checking."""

    def test_missing_file_not_fresh(self, tmp_path: Path) -> None:
        store = DataStore(tmp_path)
        assert store.is_fresh(Path("nonexistent.json")) is False

    def test_expired_file_not_fresh(self, tmp_path: Path) -> None:
        store = DataStore(tmp_path)
        past = datetime.now(UTC) - timedelta(hours=1)
        store.write(Path("live/test.json"), {}, source="test", valid_until=past)
        assert store.is_fresh(Path("live/test.json")) is False

    def test_future_valid_until_is_fresh(self, tmp_path: Path) -> None:
        store = DataStore(tmp_path)
        future = datetime.now(UTC) + timedelta(hours=6)
        store.write(Path("live/test.json"), {}, source="test", valid_until=future)
        assert store.is_fresh(Path("live/test.json")) is True

    def test_no_valid_until_not_fresh(self, tmp_path: Path) -> None:
        store = DataStore(tmp_path)
        store.write(Path("derived/test.json"), {}, source="test")
        assert store.is_fresh(Path("derived/test.json")) is False


class TestDataStoreWriteFile:
    """Test binary file storage with sidecar metadata."""

    def test_write_file_copies_and_creates_sidecar(self, tmp_path: Path) -> None:
        store = DataStore(tmp_path)

        # Create a dummy source file
        src = tmp_path / "source" / "dem.tif"
        src.parent.mkdir(parents=True)
        src.write_bytes(b"fake geotiff data")

        valid = datetime(2026, 6, 1, tzinfo=UTC)
        result = store.write_file(
            Path("reference/dem/portland.tif"),
            src,
            source="usgs",
            valid_until=valid,
        )

        assert result.exists()
        assert result.read_bytes() == b"fake geotiff data"

        # Sidecar metadata
        sidecar = result.with_suffix(".tif.meta.json")
        assert sidecar.exists()
        meta = json.loads(sidecar.read_text())
        assert meta["meta"]["source"] == "usgs"
        assert meta["meta"]["valid_until"] == valid.isoformat()

    def test_write_file_is_fresh_via_sidecar(self, tmp_path: Path) -> None:
        store = DataStore(tmp_path)

        src = tmp_path / "source" / "data.shp"
        src.parent.mkdir(parents=True)
        src.write_bytes(b"fake shapefile")

        future = datetime.now(UTC) + timedelta(days=90)
        store.write_file(
            Path("reference/ranges/butterflies.shp"),
            src,
            source="gbif",
            valid_until=future,
        )

        assert store.is_fresh(Path("reference/ranges/butterflies.shp")) is True

    def test_write_file_expired_sidecar(self, tmp_path: Path) -> None:
        store = DataStore(tmp_path)

        src = tmp_path / "source" / "old.tif"
        src.parent.mkdir(parents=True)
        src.write_bytes(b"old data")

        past = datetime.now(UTC) - timedelta(days=1)
        store.write_file(
            Path("reference/dem/old.tif"),
            src,
            source="usgs",
            valid_until=past,
        )

        assert store.is_fresh(Path("reference/dem/old.tif")) is False

    def test_file_path_returns_path(self, tmp_path: Path) -> None:
        store = DataStore(tmp_path)
        src = tmp_path / "source" / "test.bin"
        src.parent.mkdir(parents=True)
        src.write_bytes(b"data")
        store.write_file(Path("reference/test.bin"), src, source="test")

        result = store.file_path(Path("reference/test.bin"))
        assert result is not None
        assert result.exists()

    def test_file_path_missing(self, tmp_path: Path) -> None:
        store = DataStore(tmp_path)
        assert store.file_path(Path("reference/missing.bin")) is None
