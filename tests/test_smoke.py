"""
Smoke tests - verify the application actually runs.

These tests execute real code paths, not just unit test mocks.
If these fail, the application is broken regardless of unit test results.
"""

import subprocess
import sys
from pathlib import Path


class TestImports:
    """Verify all modules import without errors."""

    def test_package_imports(self) -> None:
        """Main package imports successfully."""
        from butterfly_planner import Example, Settings, __version__

        assert __version__
        assert Settings is not None
        assert Example is not None

    def test_all_modules_import(self) -> None:
        """All submodules import without errors."""
        from butterfly_planner import cli, config, core, schemas

        assert cli
        assert config
        assert core
        assert schemas


class TestCLI:
    """Verify CLI actually executes."""

    def test_cli_info_runs(self) -> None:
        """CLI info command executes and returns success."""
        result = subprocess.run(
            [sys.executable, "-m", "butterfly_planner.cli", "info"],
            capture_output=True,
            text=True,
            cwd=Path(__file__).parent.parent,
            env={**dict(__import__("os").environ), "PYTHONPATH": "src"},
            check=False,
        )
        assert result.returncode == 0, f"CLI failed: {result.stderr}"
        assert "butterfly-planner" in result.stdout.lower() or "version" in result.stdout.lower()

    def test_cli_run_executes(self) -> None:
        """CLI run command executes without error."""
        result = subprocess.run(
            [sys.executable, "-m", "butterfly_planner.cli", "run", "--name", "smoke-test"],
            capture_output=True,
            text=True,
            cwd=Path(__file__).parent.parent,
            env={**dict(__import__("os").environ), "PYTHONPATH": "src"},
            check=False,
        )
        assert result.returncode == 0, f"CLI failed: {result.stderr}"
        assert "success" in result.stdout.lower()

    def test_cli_help_works(self) -> None:
        """CLI --help works."""
        result = subprocess.run(
            [sys.executable, "-m", "butterfly_planner.cli", "--help"],
            capture_output=True,
            text=True,
            cwd=Path(__file__).parent.parent,
            env={**dict(__import__("os").environ), "PYTHONPATH": "src"},
            check=False,
        )
        assert result.returncode == 0
        assert "usage" in result.stdout.lower() or "help" in result.stdout.lower()


class TestCoreIntegration:
    """Verify core functionality works end-to-end."""

    def test_create_and_process(self) -> None:
        """Full workflow: create example, process it, verify result."""
        from butterfly_planner.core import create_example, process_example
        from butterfly_planner.schemas import Status

        # Create
        example = create_example("integration-test", metadata={"test": "true"})
        assert example.id
        assert example.status == Status.PENDING

        # Process
        result = process_example("integration-test")
        assert result.success is True
        assert result.data is not None
        assert "id" in result.data

    def test_config_loads(self) -> None:
        """Configuration loads from environment."""
        from butterfly_planner.config import get_settings

        get_settings.cache_clear()
        settings = get_settings()

        assert settings.app_name
        assert settings.app_env
