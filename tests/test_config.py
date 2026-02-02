"""
Tests for configuration management.

These tests verify settings loading and environment handling.
"""

from pathlib import Path

import pytest

from butterfly_planner.config import Settings, get_settings


class TestSettings:
    """Tests for Settings class."""

    def test_default_values(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Settings have sensible defaults."""
        # Clear any env vars that might interfere
        monkeypatch.delenv("APP_NAME", raising=False)
        monkeypatch.delenv("APP_ENV", raising=False)
        monkeypatch.delenv("DEBUG", raising=False)

        settings = Settings()

        assert settings.app_name == "butterfly-planner"
        assert settings.app_env == "development"
        assert settings.debug is False

    def test_env_override(
        self,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """Environment variables override defaults."""
        monkeypatch.setenv("APP_NAME", "custom-app")
        monkeypatch.setenv("APP_ENV", "production")
        monkeypatch.setenv("DEBUG", "true")

        settings = Settings()

        assert settings.app_name == "custom-app"
        assert settings.app_env == "production"
        assert settings.debug is True

    def test_path_settings(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        """Path settings can be configured."""
        data_dir = tmp_path / "custom_data"
        log_dir = tmp_path / "custom_logs"

        monkeypatch.setenv("DATA_DIR", str(data_dir))
        monkeypatch.setenv("LOG_DIR", str(log_dir))

        settings = Settings()

        assert settings.data_dir == data_dir
        assert settings.log_dir == log_dir

    def test_ensure_directories(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        """ensure_directories creates necessary folders."""
        data_dir = tmp_path / "data"
        log_dir = tmp_path / "logs"

        monkeypatch.setenv("DATA_DIR", str(data_dir))
        monkeypatch.setenv("LOG_DIR", str(log_dir))

        settings = Settings()
        settings.ensure_directories()

        assert data_dir.exists()
        assert log_dir.exists()


class TestGetSettings:
    """Tests for get_settings function."""

    def test_returns_settings(self, clean_environment: None) -> None:
        """get_settings returns a Settings instance."""
        settings = get_settings()
        assert isinstance(settings, Settings)

    def test_caching(self, clean_environment: None) -> None:
        """get_settings returns cached instance."""
        settings1 = get_settings()
        settings2 = get_settings()

        assert settings1 is settings2

    def test_cache_clear(
        self,
        monkeypatch: pytest.MonkeyPatch,
        clean_environment: None,
    ) -> None:
        """Cache can be cleared to reload settings."""
        settings1 = get_settings()

        get_settings.cache_clear()
        monkeypatch.setenv("APP_NAME", "new-name")

        settings2 = get_settings()

        assert settings1 is not settings2
        assert settings2.app_name == "new-name"
