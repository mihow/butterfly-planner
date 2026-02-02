"""
Command-line interface for the application.

This module provides the main entry point for the CLI.
"""

from __future__ import annotations

import argparse
import sys

from butterfly_planner import __version__
from butterfly_planner.config import get_settings
from butterfly_planner.core import process_example


def create_parser() -> argparse.ArgumentParser:
    """Create the argument parser for the CLI."""
    parser = argparse.ArgumentParser(
        prog="butterfly-planner",
        description="GIS layers for butterfly abundance and species diversity forecasting",
    )
    parser.add_argument(
        "-v",
        "--version",
        action="version",
        version=f"%(prog)s {__version__}",
    )
    parser.add_argument(
        "--debug",
        action="store_true",
        help="Enable debug mode",
    )

    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # Example: 'run' command
    run_parser = subparsers.add_parser("run", help="Run the main process")
    run_parser.add_argument(
        "--name",
        type=str,
        default="example",
        help="Name for the example (default: example)",
    )

    # Example: 'info' command
    subparsers.add_parser("info", help="Show application info")

    return parser


def cmd_run(args: argparse.Namespace) -> int:
    """Handle the 'run' command."""
    settings = get_settings()
    if args.debug:
        print(f"Debug mode enabled. Settings: {settings}")

    result = process_example(args.name)
    if result.success:
        print(f"Success: {result.message}")
        return 0
    else:
        print(f"Error: {result.error}", file=sys.stderr)
        return 1


def cmd_info(_args: argparse.Namespace) -> int:
    """Handle the 'info' command."""
    settings = get_settings()
    print(f"Application: {settings.app_name}")
    print(f"Version: {__version__}")
    print(f"Environment: {settings.app_env}")
    print(f"Debug: {settings.debug}")
    return 0


def main() -> int:
    """Main entry point for the CLI."""
    parser = create_parser()
    args = parser.parse_args()

    if args.command is None:
        parser.print_help()
        return 0

    commands = {
        "run": cmd_run,
        "info": cmd_info,
    }

    handler = commands.get(args.command)
    if handler:
        return handler(args)
    else:
        parser.print_help()
        return 1


if __name__ == "__main__":
    sys.exit(main())
