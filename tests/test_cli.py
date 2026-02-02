"""
Tests for CLI functionality.

These tests verify the command-line interface logic.
"""

from __future__ import annotations

import argparse
from io import StringIO
from unittest.mock import patch

import pytest

from butterfly_planner.cli import cmd_info, cmd_run, create_parser, main
from butterfly_planner.models import Result


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
