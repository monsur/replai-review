"""
Shared Utility Functions

This module contains common functionality used across multiple scripts
to avoid code duplication and ensure consistency.
"""

import sys
import traceback
import argparse
from pathlib import Path
from typing import Optional, Tuple

import yaml
from pydantic import ValidationError

from week_calculator import WeekCalculator, create_week_calculator
from models import Config
from exceptions import ConfigurationException


def load_config(config_path: str = "config.yaml") -> Config:
    """
    Load and validate configuration from YAML file.

    Args:
        config_path: Path to the configuration file

    Returns:
        Validated Config model instance

    Raises:
        FileNotFoundError: If config file doesn't exist
        yaml.YAMLError: If config file is invalid YAML
        ConfigurationException: If config validation fails
    """
    try:
        with open(config_path, 'r') as f:
            config_dict = yaml.safe_load(f)

        # Validate using Pydantic
        config = Config.from_yaml_dict(config_dict)

        return config

    except FileNotFoundError:
        handle_fatal_error(
            f"Configuration file not found: {config_path}",
            FileNotFoundError(f"File '{config_path}' does not exist")
        )
    except yaml.YAMLError as e:
        handle_fatal_error(
            f"Invalid YAML in configuration file: {config_path}",
            e
        )
    except ValidationError as e:
        # Format validation errors nicely
        error_messages = []
        for error in e.errors():
            field = ' -> '.join(str(x) for x in error['loc'])
            message = error['msg']
            error_messages.append(f"{field}: {message}")

        formatted_errors = '\n  '.join(error_messages)
        handle_fatal_error(
            f"Invalid configuration in {config_path}:\n  {formatted_errors}",
            ConfigurationException(f"Config validation failed: {formatted_errors}")
        )


def get_week_directory_path(config: Config, year: int, week: int) -> Path:
    """
    Get the path to a week's directory in the tmp folder.

    Args:
        config: Validated configuration model
        year: NFL season year
        week: NFL week number

    Returns:
        Path object pointing to the week directory (e.g., tmp/2025-week08)
    """
    tmp_dir = config.storage.tmp_dir
    return Path(tmp_dir) / f"{year}-week{week:02d}"


def setup_week_calculator(
    config: Config,
    manual_week: Optional[int] = None
) -> Tuple[int, int, WeekCalculator]:
    """
    Create week calculator and determine target week and year.

    Args:
        config: Validated configuration model
        manual_week: Optional manual week override

    Returns:
        Tuple of (week, year, week_calculator)
    """
    week_calculator = create_week_calculator(
        season_start_date=config.nfl_season.season_start_date,
        manual_week=manual_week
    )
    week = week_calculator.get_week()
    year = config.nfl_season.year
    return week, year, week_calculator


def create_base_parser(description: str) -> argparse.ArgumentParser:
    """
    Create argument parser with common arguments.

    All scripts share --week and --config arguments. This function
    creates a parser with these common arguments pre-configured.

    Args:
        description: Description for the ArgumentParser

    Returns:
        ArgumentParser with common arguments added

    Example:
        parser = create_base_parser('Fetch NFL game recaps')
        parser.add_argument('--custom', help='Script-specific argument')
        args = parser.parse_args()
    """
    parser = argparse.ArgumentParser(description=description)
    parser.add_argument(
        '--week',
        type=int,
        help='Specific week number to process (overrides auto-calculation)'
    )
    parser.add_argument(
        '--config',
        default='config.yaml',
        help='Path to config file (default: config.yaml)'
    )
    return parser


def handle_fatal_error(message: str, exception: Exception) -> None:
    """
    Handle a fatal error that should terminate the program.

    Prints error message and exits with status code 1.

    Args:
        message: Human-readable error message
        exception: The exception that caused the error

    Note:
        This function does not return - it exits the program.
    """
    print(f"❌ FATAL ERROR: {message}")
    print(f"   Details: {exception}")
    sys.exit(1)


def handle_recoverable_error(
    message: str,
    exception: Exception,
    verbose: bool = False
) -> None:
    """
    Handle a recoverable error that allows the program to continue.

    Prints warning message and optionally shows full traceback.

    Args:
        message: Human-readable error message
        exception: The exception that caused the error
        verbose: If True, print full traceback
    """
    print(f"⚠️  WARNING: {message}")
    print(f"   Details: {exception}")
    if verbose:
        traceback.print_exc()


def print_success(message: str) -> None:
    """
    Print a success message with consistent formatting.

    Args:
        message: Success message to print
    """
    print(f"✅ {message}")


def print_info(message: str) -> None:
    """
    Print an info message with consistent formatting.

    Args:
        message: Info message to print
    """
    print(f"ℹ️  {message}")
