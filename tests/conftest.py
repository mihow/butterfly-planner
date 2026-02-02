"""
Pytest configuration and shared fixtures.

This file is automatically loaded by pytest and provides fixtures
available to all test files.
"""

import asyncio
from pathlib import Path

import pytest

from butterfly_planner.config import Settings, get_settings
from butterfly_planner.models import Example, Status

# =============================================================================
# Environment Fixtures
# =============================================================================


@pytest.fixture(autouse=True)
def clean_environment(monkeypatch: pytest.MonkeyPatch) -> None:
    """
    Ensure clean environment for each test.

    This fixture runs automatically for all tests to prevent
    environment variable leakage between tests.
    """
    # Clear any cached settings
    get_settings.cache_clear()


@pytest.fixture
def temp_dir(tmp_path: Path) -> Path:
    """Provide a temporary directory for test files."""
    return tmp_path


@pytest.fixture
def test_settings(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Settings:
    """
    Create test settings with temporary directories.

    Use this fixture when you need settings that don't affect
    the real filesystem.
    """
    monkeypatch.setenv("APP_ENV", "test")
    monkeypatch.setenv("DEBUG", "true")
    monkeypatch.setenv("DATA_DIR", str(tmp_path / "data"))
    monkeypatch.setenv("LOG_DIR", str(tmp_path / "logs"))

    get_settings.cache_clear()
    settings = get_settings()
    settings.ensure_directories()
    return settings


# =============================================================================
# Model Fixtures
# =============================================================================


@pytest.fixture
def sample_example() -> Example:
    """Create a sample Example instance for testing."""
    return Example(
        id="test-123",
        name="Test Example",
        status=Status.PENDING,
        metadata={"key": "value"},
    )


@pytest.fixture
def example_factory():
    """
    Factory fixture for creating Example instances.

    Usage:
        def test_something(example_factory):
            ex1 = example_factory(name="First")
            ex2 = example_factory(name="Second", status=Status.COMPLETED)
    """

    def _factory(
        id: str = "test-id",
        name: str = "Test",
        status: Status = Status.PENDING,
        **kwargs: object,
    ) -> Example:
        return Example(id=id, name=name, status=status, **kwargs)

    return _factory


# =============================================================================
# Async Fixtures (if needed)
# =============================================================================


@pytest.fixture
def event_loop_policy():
    """Use default event loop policy for async tests."""
    return asyncio.DefaultEventLoopPolicy()


# =============================================================================
# Marker Configurations
# =============================================================================


def pytest_configure(config: pytest.Config) -> None:
    """Configure custom pytest markers."""
    config.addinivalue_line("markers", "slow: marks tests as slow running")
    config.addinivalue_line("markers", "integration: marks integration tests")
    config.addinivalue_line("markers", "unit: marks unit tests")
