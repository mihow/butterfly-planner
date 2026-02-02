"""
Configuration management for the application.

Uses Pydantic Settings for environment-based configuration with validation.
"""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """
    Application settings loaded from environment variables.

    Environment variables can be set directly or via a .env file.
    All settings have sensible defaults for local development.
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # Application settings
    app_name: str = Field(default="my-project", description="Application name")
    app_env: str = Field(
        default="development", description="Environment (development/staging/production)"
    )
    debug: bool = Field(default=False, description="Enable debug mode")

    # Paths
    data_dir: Path = Field(default=Path("data"), description="Data directory path")
    log_dir: Path = Field(default=Path("logs"), description="Log directory path")

    # API settings (example)
    api_host: str = Field(default="0.0.0.0", description="API host")
    api_port: int = Field(default=8000, description="API port")

    def ensure_directories(self) -> None:
        """Create necessary directories if they don't exist."""
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.log_dir.mkdir(parents=True, exist_ok=True)


@lru_cache
def get_settings() -> Settings:
    """
    Get cached application settings.

    Returns:
        Settings instance (cached after first call)
    """
    return Settings()
