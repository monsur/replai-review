"""
Shared utilities for the 3-stage pipeline.

This module provides helper functions used across all three stages:
- Path/directory helpers
- Filename generation
- Date parsing and validation
- Type validation
"""

from pathlib import Path
from datetime import datetime
from typing import Tuple
from zoneinfo import ZoneInfo


def get_week_directory(year: int, week: int) -> Path:
    """
    Get the week directory path.

    Args:
        year: NFL season year
        week: NFL week number (1-18)

    Returns:
        Path to week directory (e.g., tmp/2025-week09)
    """
    return Path(f"tmp/{year}-week{week:02d}")


def get_day_subdirectory(year: int, week: int, date: str) -> Path:
    """
    Get the day subdirectory path within a week directory.

    Args:
        year: NFL season year
        week: NFL week number (1-18)
        date: Date in YYYYMMDD format

    Returns:
        Path to day subdirectory (e.g., tmp/2025-week09/20251109)
    """
    week_dir = get_week_directory(year, week)
    return week_dir / date


def get_work_directory(year: int, week: int, date: str, type_str: str) -> Path:
    """
    Get working directory for a date/type combination.

    For day mode: tmp/2025-week09/20251109/
    For week mode: tmp/2025-week09/

    Args:
        year: NFL season year
        week: NFL week number
        date: Date in YYYYMMDD format
        type_str: 'day' or 'week'

    Returns:
        Path to working directory
    """
    if type_str == "day":
        return get_day_subdirectory(year, week, date)
    else:  # week mode
        return get_week_directory(year, week)


def get_games_file_path(year: int, week: int, date: str, type_str: str) -> Path:
    """
    Get path to games.json file.

    Args:
        year: NFL season year
        week: NFL week number
        date: Date in YYYYMMDD format
        type_str: 'day' or 'week'

    Returns:
        Path to games.json file
    """
    work_dir = get_work_directory(year, week, date, type_str)
    return work_dir / "games.json"


def get_newsletter_file_path(year: int, week: int, date: str, type_str: str) -> Path:
    """
    Get path to newsletter.json file.

    Args:
        year: NFL season year
        week: NFL week number
        date: Date in YYYYMMDD format
        type_str: 'day' or 'week'

    Returns:
        Path to newsletter.json file
    """
    work_dir = get_work_directory(year, week, date, type_str)
    return work_dir / "newsletter.json"


def get_output_html_filename(metadata: dict) -> str:
    """
    Generate output HTML filename from metadata.

    Args:
        metadata: Dict with 'date', 'type', 'week', 'year'

    Returns:
        Filename like:
        - '2025-week09-sun-251109.html' (day mode)
        - '2025-week09.html' (week mode)

    Raises:
        ValueError: If metadata is missing required fields
    """
    try:
        date = metadata["date"]
        type_val = metadata["type"]
        week = metadata["week"]
        year = metadata["year"]
    except KeyError as e:
        raise ValueError(f"Missing required metadata field: {e}")

    if type_val == "week":
        return f"{year}-week{week:02d}.html"
    else:  # day mode
        # Get day abbreviation from date
        dt = datetime.strptime(date, "%Y%m%d")
        day_abbr = dt.strftime("%a").lower()  # 'sun', 'mon', etc.
        short_date = date[2:]  # '20251109' -> '251109'
        return f"{year}-week{week:02d}-{day_abbr}-{short_date}.html"


def parse_date(date_str: str) -> Tuple[int, int, int]:
    """
    Parse YYYYMMDD string to year, month, day.

    Args:
        date_str: Date string in YYYYMMDD format

    Returns:
        Tuple of (year, month, day)

    Raises:
        ValueError: If date format is invalid or date is impossible
    """
    if len(date_str) != 8:
        raise ValueError(
            f"Invalid date format: {date_str} (expected YYYYMMDD, got {len(date_str)} chars)"
        )

    try:
        year = int(date_str[0:4])
        month = int(date_str[4:6])
        day = int(date_str[6:8])

        # Validate ranges
        if not (2020 <= year <= 2035):
            raise ValueError(f"Invalid year: {year} (expected 2020-2035)")
        if not (1 <= month <= 12):
            raise ValueError(f"Invalid month: {month} (expected 1-12)")
        if not (1 <= day <= 31):
            raise ValueError(f"Invalid day: {day} (expected 1-31)")

        # Try to create a datetime to validate the date exists
        try:
            datetime(year, month, day)
        except ValueError:
            raise ValueError(f"Invalid date: {year}-{month:02d}-{day:02d} (day doesn't exist)")

        return year, month, day

    except ValueError as e:
        # Re-raise with additional context
        raise ValueError(f"Invalid date format: {date_str}") from e


def validate_type(type_str: str) -> str:
    """
    Validate and normalize type parameter.

    Args:
        type_str: Type string ('day', 'week', 'DAY', 'WEEK', etc.)

    Returns:
        Normalized type: 'day' or 'week'

    Raises:
        ValueError: If type is invalid
    """
    normalized = type_str.lower().strip()
    if normalized not in ["day", "week"]:
        raise ValueError(
            f"Invalid type: {type_str} (expected 'day' or 'week')"
        )
    return normalized


def format_game_date(iso_date: str) -> str:
    """
    Convert ISO 8601 date to newsletter display format.

    Args:
        iso_date: ISO 8601 date string (e.g., "2025-10-30T20:15Z")

    Returns:
        Formatted date string (e.g., "Thu 10/30 8:15PM ET")

    Raises:
        ValueError: If date format is invalid
    """
    try:
        dt_utc = datetime.fromisoformat(iso_date.replace("Z", "+00:00"))

        # Try to use ZoneInfo, fall back to hardcoded offset if tzdata not available
        try:
            dt_et = dt_utc.astimezone(ZoneInfo("US/Eastern"))
        except Exception:
            # Fallback: US/Eastern is UTC-4 (EDT) during game season
            from datetime import timedelta, timezone
            eastern_offset = timedelta(hours=-4)
            dt_et = dt_utc.astimezone(timezone(eastern_offset))

        day_name = dt_et.strftime("%a")
        month_day = dt_et.strftime("%-m/%-d")
        time_part = dt_et.strftime("%-I:%M%p")

        return f"{day_name} {month_day} {time_part} ET"
    except (ValueError, KeyError) as e:
        raise ValueError(f"Invalid ISO date format: {iso_date}") from e
