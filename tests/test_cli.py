"""
Tests for CLI functionality.

These tests verify the command-line interface logic.
"""

from __future__ import annotations

import argparse
import unittest.mock
from io import StringIO
from typing import TYPE_CHECKING
from unittest.mock import patch

if TYPE_CHECKING:
    from pathlib import Path

import pytest

from butterfly_planner.cli import cmd_info, cmd_refresh, cmd_run, cmd_serve, create_parser, main
from butterfly_planner.schemas import Result


class TestCreateParser:
    """Tests for create_parser function."""

    def test_creates_parser(self) -> None:
        """Parser is created successfully."""
        parser = create_parser()
        assert isinstance(parser, argparse.ArgumentParser)
        assert parser.prog == "butterfly-planner"

    def test_parser_has_version(self) -> None:
        """Parser has version argument."""
        parser = create_parser()
        # Version is handled by argparse, just verify it exists
        with pytest.raises(SystemExit):
            parser.parse_args(["--version"])

    def test_parser_has_debug_flag(self) -> None:
        """Parser accepts --debug flag."""
        parser = create_parser()
        args = parser.parse_args(["--debug", "info"])
        assert args.debug is True

    def test_parser_run_command(self) -> None:
        """Parser accepts run command with --name."""
        parser = create_parser()
        args = parser.parse_args(["run", "--name", "test"])
        assert args.command == "run"
        assert args.name == "test"

    def test_parser_run_default_name(self) -> None:
        """Run command has default name."""
        parser = create_parser()
        args = parser.parse_args(["run"])
        assert args.name == "example"

    def test_parser_info_command(self) -> None:
        """Parser accepts info command."""
        parser = create_parser()
        args = parser.parse_args(["info"])
        assert args.command == "info"

    def test_parser_refresh_command(self) -> None:
        """Parser accepts refresh command."""
        parser = create_parser()
        args = parser.parse_args(["refresh"])
        assert args.command == "refresh"

    def test_parser_serve_command(self) -> None:
        """Parser accepts serve command with optional --port."""
        parser = create_parser()
        args = parser.parse_args(["serve"])
        assert args.command == "serve"
        assert args.port is None

    def test_parser_serve_with_port(self) -> None:
        """Parser accepts serve --port."""
        parser = create_parser()
        args = parser.parse_args(["serve", "--port", "3000"])
        assert args.port == 3000


class TestCmdRun:
    """Tests for cmd_run function."""

    def test_success_returns_zero(self) -> None:
        """Successful run returns exit code 0."""
        args = argparse.Namespace(name="test", debug=False)

        with patch("butterfly_planner.cli.process_example") as mock_process:
            mock_process.return_value = Result(
                success=True,
                message="Success message",
                data={"id": "123"},
            )

            exit_code = cmd_run(args)
            assert exit_code == 0
            mock_process.assert_called_once_with("test")

    def test_failure_returns_one(self) -> None:
        """Failed run returns exit code 1."""
        args = argparse.Namespace(name="test", debug=False)

        with patch("butterfly_planner.cli.process_example") as mock_process:
            mock_process.return_value = Result(
                success=False,
                message="",
                error="Something went wrong",
            )

            exit_code = cmd_run(args)
            assert exit_code == 1

    def test_debug_mode_prints_settings(self) -> None:
        """Debug mode prints settings."""
        args = argparse.Namespace(name="test", debug=True)

        with patch("butterfly_planner.cli.process_example") as mock_process:
            mock_process.return_value = Result(success=True, message="ok", data={})

            with patch("sys.stdout", new=StringIO()) as mock_stdout:
                cmd_run(args)
                output = mock_stdout.getvalue()
                assert "Settings" in output or "Debug" in output

    def test_passes_name_to_process(self) -> None:
        """Name argument is passed to process_example."""
        args = argparse.Namespace(name="custom-name", debug=False)

        with patch("butterfly_planner.cli.process_example") as mock_process:
            mock_process.return_value = Result(success=True, message="ok", data={})
            cmd_run(args)
            mock_process.assert_called_once_with("custom-name")


class TestCmdInfo:
    """Tests for cmd_info function."""

    def test_returns_zero(self) -> None:
        """Info command returns exit code 0."""
        args = argparse.Namespace()
        exit_code = cmd_info(args)
        assert exit_code == 0

    def test_prints_app_info(self) -> None:
        """Info command prints application information."""
        args = argparse.Namespace()

        with patch("sys.stdout", new=StringIO()) as mock_stdout:
            cmd_info(args)
            output = mock_stdout.getvalue()
            assert "Application" in output or "Version" in output or "Environment" in output


class TestCmdRefresh:
    """Tests for cmd_refresh function."""

    def test_returns_zero(self) -> None:
        """Refresh command returns exit code 0."""
        args = argparse.Namespace()

        with (
            patch("butterfly_planner.cli.fetch_all") as mock_fetch,
            patch("butterfly_planner.cli.build_all") as mock_build,
        ):
            mock_fetch.return_value = {"weather_days": 7, "output": "data/raw/weather.json"}
            mock_build.return_value = {"pages": 1, "output": "site/index.html"}

            exit_code = cmd_refresh(args)
            assert exit_code == 0

    def test_calls_fetch_then_build(self) -> None:
        """Refresh calls fetch_all before build_all."""
        args = argparse.Namespace()
        call_order: list[str] = []

        def mock_fetch(**_kwargs: object) -> dict[str, object]:
            call_order.append("fetch")
            return {}

        def mock_build() -> dict[str, object]:
            call_order.append("build")
            return {}

        with (
            patch("butterfly_planner.cli.fetch_all", side_effect=mock_fetch),
            patch("butterfly_planner.cli.build_all", side_effect=mock_build),
        ):
            cmd_refresh(args)
            assert call_order == ["fetch", "build"]

    def test_passes_lat_lon_from_settings(self) -> None:
        """Refresh passes lat/lon from settings to fetch_all."""
        args = argparse.Namespace()

        with (
            patch("butterfly_planner.cli.fetch_all") as mock_fetch,
            patch("butterfly_planner.cli.build_all"),
            patch("butterfly_planner.cli.get_settings") as mock_settings,
        ):
            mock_settings.return_value.lat = 44.0
            mock_settings.return_value.lon = -123.0
            mock_fetch.return_value = {}

            cmd_refresh(args)
            mock_fetch.assert_called_once_with(lat=44.0, lon=-123.0)


class TestCmdServe:
    """Tests for cmd_serve function."""

    def test_missing_site_dir_returns_one(self, tmp_path: Path) -> None:
        """Serve returns 1 when site/ doesn't exist."""
        args = argparse.Namespace(port=8080)

        with patch("butterfly_planner.cli.Path", return_value=tmp_path / "no-such-dir"):
            exit_code = cmd_serve(args)
            assert exit_code == 1

    def test_uses_port_from_args(self, tmp_path: Path) -> None:
        """Serve uses --port when provided."""
        (tmp_path / "site").mkdir()
        args = argparse.Namespace(port=9999)

        mock_server = unittest.mock.MagicMock()
        mock_server.__enter__ = unittest.mock.Mock(return_value=mock_server)
        mock_server.__exit__ = unittest.mock.Mock(return_value=False)
        mock_server.serve_forever = unittest.mock.Mock(side_effect=KeyboardInterrupt)

        with (
            patch("butterfly_planner.cli.Path", side_effect=lambda s: tmp_path / s),
            patch(
                "butterfly_planner.cli.http.server.HTTPServer", return_value=mock_server
            ) as mock_ctor,
        ):
            cmd_serve(args)
            mock_ctor.assert_called_once()
            assert mock_ctor.call_args[0][0] == ("", 9999)

    def test_uses_port_from_settings_when_none(self, tmp_path: Path) -> None:
        """Serve falls back to api_port from settings."""
        (tmp_path / "site").mkdir()
        args = argparse.Namespace(port=None)

        mock_server = unittest.mock.MagicMock()
        mock_server.__enter__ = unittest.mock.Mock(return_value=mock_server)
        mock_server.__exit__ = unittest.mock.Mock(return_value=False)
        mock_server.serve_forever = unittest.mock.Mock(side_effect=KeyboardInterrupt)

        with (
            patch("butterfly_planner.cli.Path", side_effect=lambda s: tmp_path / s),
            patch(
                "butterfly_planner.cli.http.server.HTTPServer", return_value=mock_server
            ) as mock_ctor,
            patch("butterfly_planner.cli.get_settings") as mock_settings,
        ):
            mock_settings.return_value.api_port = 5555
            cmd_serve(args)
            assert mock_ctor.call_args[0][0] == ("", 5555)


class TestMain:
    """Tests for main function."""

    def test_no_command_shows_help(self) -> None:
        """No command shows help and exits 0."""
        with patch("sys.argv", ["butterfly-planner"]):
            exit_code = main()
            assert exit_code == 0

    def test_run_command_executes(self) -> None:
        """Run command executes successfully."""
        with (
            patch("sys.argv", ["butterfly-planner", "run", "--name", "test"]),
            patch("butterfly_planner.cli.cmd_run") as mock_cmd,
        ):
            mock_cmd.return_value = 0
            exit_code = main()
            assert exit_code == 0
            mock_cmd.assert_called_once()

    def test_info_command_executes(self) -> None:
        """Info command executes successfully."""
        with (
            patch("sys.argv", ["butterfly-planner", "info"]),
            patch("butterfly_planner.cli.cmd_info") as mock_cmd,
        ):
            mock_cmd.return_value = 0
            exit_code = main()
            assert exit_code == 0
            mock_cmd.assert_called_once()

    def test_refresh_command_executes(self) -> None:
        """Refresh command executes successfully."""
        with (
            patch("sys.argv", ["butterfly-planner", "refresh"]),
            patch("butterfly_planner.cli.cmd_refresh") as mock_cmd,
        ):
            mock_cmd.return_value = 0
            exit_code = main()
            assert exit_code == 0
            mock_cmd.assert_called_once()

    def test_serve_command_executes(self) -> None:
        """Serve command executes successfully."""
        with (
            patch("sys.argv", ["butterfly-planner", "serve"]),
            patch("butterfly_planner.cli.cmd_serve") as mock_cmd,
        ):
            mock_cmd.return_value = 0
            exit_code = main()
            assert exit_code == 0
            mock_cmd.assert_called_once()

    def test_unknown_command_shows_help(self) -> None:
        """Unknown command shows help and returns 1."""
        # This tests the defensive code path, though argparse
        # would normally catch unknown commands
        with (
            patch("sys.argv", ["butterfly-planner", "run"]),
            patch("butterfly_planner.cli.create_parser") as mock_parser,
        ):
            mock_parser.return_value.parse_args.return_value = argparse.Namespace(command="unknown")
            exit_code = main()
            assert exit_code == 1
