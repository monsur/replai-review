"""
Unit tests for stage_utils.py

Run with:
    python -m pytest test_stage_utils.py -v
    or
    python -m unittest test_stage_utils.py -v
"""

import unittest
from pathlib import Path
from datetime import datetime

from stage_utils import (
    get_week_directory,
    get_day_subdirectory,
    get_work_directory,
    get_games_file_path,
    get_newsletter_file_path,
    get_output_html_filename,
    parse_date,
    validate_type,
    format_game_date,
)


class TestWeekDirectory(unittest.TestCase):
    """Test get_week_directory function."""

    def test_week_directory_week_9(self):
        """Test directory path for Week 9."""
        result = get_week_directory(2025, 9)
        self.assertEqual(result, Path("tmp/2025-week09"))

    def test_week_directory_week_1(self):
        """Test directory path for Week 1."""
        result = get_week_directory(2025, 1)
        self.assertEqual(result, Path("tmp/2025-week01"))

    def test_week_directory_week_18(self):
        """Test directory path for Week 18 (last regular season)."""
        result = get_week_directory(2025, 18)
        self.assertEqual(result, Path("tmp/2025-week18"))

    def test_week_directory_different_year(self):
        """Test directory path with different year."""
        result = get_week_directory(2024, 5)
        self.assertEqual(result, Path("tmp/2024-week05"))


class TestDaySubdirectory(unittest.TestCase):
    """Test get_day_subdirectory function."""

    def test_day_subdirectory(self):
        """Test day subdirectory path."""
        result = get_day_subdirectory(2025, 9, "20251109")
        self.assertEqual(result, Path("tmp/2025-week09/20251109"))

    def test_day_subdirectory_week_1(self):
        """Test day subdirectory for Week 1."""
        result = get_day_subdirectory(2025, 1, "20250904")
        self.assertEqual(result, Path("tmp/2025-week01/20250904"))


class TestWorkDirectory(unittest.TestCase):
    """Test get_work_directory function."""

    def test_work_directory_day_mode(self):
        """Test work directory for day mode."""
        result = get_work_directory(2025, 9, "20251109", "day")
        self.assertEqual(result, Path("tmp/2025-week09/20251109"))

    def test_work_directory_week_mode(self):
        """Test work directory for week mode."""
        result = get_work_directory(2025, 9, "20251109", "week")
        self.assertEqual(result, Path("tmp/2025-week09"))

    def test_work_directory_different_dates(self):
        """Test multiple day mode directories in same week."""
        result1 = get_work_directory(2025, 9, "20251109", "day")
        result2 = get_work_directory(2025, 9, "20251110", "day")

        self.assertEqual(result1, Path("tmp/2025-week09/20251109"))
        self.assertEqual(result2, Path("tmp/2025-week09/20251110"))
        # Both should be in the same week directory
        self.assertEqual(result1.parent, result2.parent)


class TestGamesFilePath(unittest.TestCase):
    """Test get_games_file_path function."""

    def test_games_file_path_day_mode(self):
        """Test games.json path for day mode."""
        result = get_games_file_path(2025, 9, "20251109", "day")
        self.assertEqual(result, Path("tmp/2025-week09/20251109/games.json"))

    def test_games_file_path_week_mode(self):
        """Test games.json path for week mode."""
        result = get_games_file_path(2025, 9, "20251109", "week")
        self.assertEqual(result, Path("tmp/2025-week09/games.json"))

    def test_games_file_path_filename(self):
        """Test that filename is always 'games.json'."""
        result = get_games_file_path(2025, 1, "20250904", "day")
        self.assertEqual(result.name, "games.json")


class TestNewsletterFilePath(unittest.TestCase):
    """Test get_newsletter_file_path function."""

    def test_newsletter_file_path_day_mode(self):
        """Test newsletter.json path for day mode."""
        result = get_newsletter_file_path(2025, 9, "20251109", "day")
        self.assertEqual(result, Path("tmp/2025-week09/20251109/newsletter.json"))

    def test_newsletter_file_path_week_mode(self):
        """Test newsletter.json path for week mode."""
        result = get_newsletter_file_path(2025, 9, "20251109", "week")
        self.assertEqual(result, Path("tmp/2025-week09/newsletter.json"))

    def test_newsletter_file_path_filename(self):
        """Test that filename is always 'newsletter.json'."""
        result = get_newsletter_file_path(2025, 1, "20250904", "day")
        self.assertEqual(result.name, "newsletter.json")


class TestOutputHtmlFilename(unittest.TestCase):
    """Test get_output_html_filename function."""

    def test_day_mode_filename(self):
        """Test HTML filename for day mode (Sunday)."""
        metadata = {
            "date": "20251109",
            "type": "day",
            "week": 9,
            "year": 2025
        }
        result = get_output_html_filename(metadata)
        self.assertEqual(result, "2025-week09-sun-251109.html")

    def test_day_mode_thursday(self):
        """Test HTML filename for day mode (Thursday)."""
        metadata = {
            "date": "20251106",  # Thursday
            "type": "day",
            "week": 9,
            "year": 2025
        }
        result = get_output_html_filename(metadata)
        self.assertEqual(result, "2025-week09-thu-251106.html")

    def test_day_mode_monday(self):
        """Test HTML filename for day mode (Monday)."""
        metadata = {
            "date": "20251110",  # Monday
            "type": "day",
            "week": 9,
            "year": 2025
        }
        result = get_output_html_filename(metadata)
        self.assertEqual(result, "2025-week09-mon-251110.html")

    def test_week_mode_filename(self):
        """Test HTML filename for week mode."""
        metadata = {
            "date": "20251109",
            "type": "week",
            "week": 9,
            "year": 2025
        }
        result = get_output_html_filename(metadata)
        self.assertEqual(result, "2025-week09.html")

    def test_week_1_filename(self):
        """Test HTML filename for Week 1."""
        metadata = {
            "date": "20250904",
            "type": "week",
            "week": 1,
            "year": 2025
        }
        result = get_output_html_filename(metadata)
        self.assertEqual(result, "2025-week01.html")

    def test_week_18_day_mode(self):
        """Test HTML filename for Week 18 day mode."""
        metadata = {
            "date": "20260104",  # Week 18 date
            "type": "day",
            "week": 18,
            "year": 2026
        }
        result = get_output_html_filename(metadata)
        self.assertEqual(result, "2026-week18-sun-260104.html")

    def test_missing_metadata_field(self):
        """Test that missing metadata field raises ValueError."""
        metadata = {
            "date": "20251109",
            "type": "day",
            # Missing 'week' and 'year'
        }
        with self.assertRaises(ValueError):
            get_output_html_filename(metadata)

    def test_filename_format_day_mode(self):
        """Test that day mode filename has correct format."""
        metadata = {
            "date": "20251109",
            "type": "day",
            "week": 9,
            "year": 2025
        }
        result = get_output_html_filename(metadata)
        # Format: YYYY-weekWW-ddd-YYMMDD.html
        parts = result.split("-")
        self.assertEqual(parts[0], "2025")
        self.assertEqual(parts[1], "week09")
        self.assertEqual(len(parts[2]), 3)  # day abbreviation
        self.assertTrue(parts[3].endswith(".html"))


class TestParseDate(unittest.TestCase):
    """Test parse_date function."""

    def test_valid_date(self):
        """Test parsing valid date."""
        result = parse_date("20251109")
        self.assertEqual(result, (2025, 11, 9))

    def test_valid_date_jan_1(self):
        """Test parsing January 1st."""
        result = parse_date("20250101")
        self.assertEqual(result, (2025, 1, 1))

    def test_valid_date_dec_31(self):
        """Test parsing December 31st."""
        result = parse_date("20251231")
        self.assertEqual(result, (2025, 12, 31))

    def test_valid_date_leap_year(self):
        """Test parsing leap year February 29."""
        result = parse_date("20240229")
        self.assertEqual(result, (2024, 2, 29))

    def test_invalid_length(self):
        """Test that invalid length raises ValueError."""
        with self.assertRaises(ValueError):
            parse_date("2025111")  # 7 digits
        with self.assertRaises(ValueError):
            parse_date("202511099")  # 9 digits

    def test_invalid_month(self):
        """Test that invalid month raises ValueError."""
        with self.assertRaises(ValueError):
            parse_date("20251309")  # Month 13
        with self.assertRaises(ValueError):
            parse_date("20250009")  # Month 0

    def test_invalid_day(self):
        """Test that invalid day raises ValueError."""
        with self.assertRaises(ValueError):
            parse_date("20251132")  # Day 32
        with self.assertRaises(ValueError):
            parse_date("20251100")  # Day 0

    def test_invalid_year(self):
        """Test that invalid year raises ValueError."""
        with self.assertRaises(ValueError):
            parse_date("20191109")  # Year 2019 (before 2020)
        with self.assertRaises(ValueError):
            parse_date("20361109")  # Year 2036 (after 2035)

    def test_impossible_date(self):
        """Test that impossible dates raise ValueError."""
        with self.assertRaises(ValueError):
            parse_date("20250229")  # Feb 29 in non-leap year
        with self.assertRaises(ValueError):
            parse_date("20250431")  # April 31 (April has 30 days)

    def test_non_numeric(self):
        """Test that non-numeric input raises ValueError."""
        with self.assertRaises(ValueError):
            parse_date("abcdefgh")


class TestValidateType(unittest.TestCase):
    """Test validate_type function."""

    def test_day_lowercase(self):
        """Test 'day' in lowercase."""
        result = validate_type("day")
        self.assertEqual(result, "day")

    def test_week_lowercase(self):
        """Test 'week' in lowercase."""
        result = validate_type("week")
        self.assertEqual(result, "week")

    def test_day_uppercase(self):
        """Test 'DAY' in uppercase."""
        result = validate_type("DAY")
        self.assertEqual(result, "day")

    def test_week_uppercase(self):
        """Test 'WEEK' in uppercase."""
        result = validate_type("WEEK")
        self.assertEqual(result, "week")

    def test_day_mixed_case(self):
        """Test 'Day' in mixed case."""
        result = validate_type("Day")
        self.assertEqual(result, "day")

    def test_with_whitespace(self):
        """Test with leading/trailing whitespace."""
        result = validate_type("  day  ")
        self.assertEqual(result, "day")

    def test_invalid_type(self):
        """Test that invalid type raises ValueError."""
        with self.assertRaises(ValueError):
            validate_type("daily")
        with self.assertRaises(ValueError):
            validate_type("weekly")
        with self.assertRaises(ValueError):
            validate_type("invalid")

    def test_empty_string(self):
        """Test that empty string raises ValueError."""
        with self.assertRaises(ValueError):
            validate_type("")


class TestFormatGameDate(unittest.TestCase):
    """Test format_game_date function."""

    def test_basic_iso_date(self):
        """Test formatting basic ISO date."""
        # 2025-10-30T20:15Z should be Thu 10/30 3:15PM ET (UTC-5)
        result = format_game_date("2025-10-30T20:15Z")
        self.assertIn("10/30", result)
        self.assertIn("ET", result)

    def test_includes_day_name(self):
        """Test that result includes day name abbreviation."""
        result = format_game_date("2025-11-09T13:00Z")  # Sunday
        self.assertIn("Sun", result)

    def test_includes_time(self):
        """Test that result includes time."""
        result = format_game_date("2025-11-09T20:00Z")
        self.assertIn("ET", result)
        # Should have time format like "3:00PM"
        self.assertRegex(result, r"\d{1,2}:\d{2}(AM|PM)")

    def test_eastern_time_conversion(self):
        """Test that UTC is correctly converted to Eastern Time."""
        # 2025-09-04T21:00Z (9PM UTC) = 5PM ET (UTC-4 in September)
        result = format_game_date("2025-09-04T21:00Z")
        self.assertIn("9/4", result)

    def test_midnight_conversion(self):
        """Test midnight time."""
        result = format_game_date("2025-10-30T04:00Z")
        self.assertIn("ET", result)

    def test_invalid_iso_format(self):
        """Test that invalid ISO format raises ValueError."""
        with self.assertRaises(ValueError):
            format_game_date("not-a-date")
        with self.assertRaises(ValueError):
            format_game_date("invalid")


class TestIntegration(unittest.TestCase):
    """Integration tests combining multiple functions."""

    def test_day_mode_full_path(self):
        """Test full path construction for day mode."""
        year, week, date, type_str = 2025, 9, "20251109", "day"

        # Get all paths
        games_path = get_games_file_path(year, week, date, type_str)
        newsletter_path = get_newsletter_file_path(year, week, date, type_str)
        html_filename = get_output_html_filename({
            "date": date,
            "type": type_str,
            "week": week,
            "year": year
        })

        # Verify they're in the correct locations
        self.assertEqual(
            games_path.parent,
            get_work_directory(year, week, date, type_str)
        )
        self.assertEqual(
            newsletter_path.parent,
            get_work_directory(year, week, date, type_str)
        )
        self.assertEqual(html_filename, "2025-week09-sun-251109.html")

    def test_week_mode_full_path(self):
        """Test full path construction for week mode."""
        year, week, date, type_str = 2025, 9, "20251109", "week"

        # Get all paths
        games_path = get_games_file_path(year, week, date, type_str)
        newsletter_path = get_newsletter_file_path(year, week, date, type_str)
        html_filename = get_output_html_filename({
            "date": date,
            "type": type_str,
            "week": week,
            "year": year
        })

        # Verify they're in the correct locations
        self.assertEqual(
            games_path.parent,
            get_week_directory(year, week)
        )
        self.assertEqual(
            newsletter_path.parent,
            get_week_directory(year, week)
        )
        self.assertEqual(html_filename, "2025-week09.html")

    def test_multiple_days_same_week(self):
        """Test handling multiple daily runs in same week."""
        year, week, type_str = 2025, 9, "day"

        # Multiple days in same week
        dates = ["20251106", "20251109", "20251110"]

        games_paths = [get_games_file_path(year, week, d, type_str) for d in dates]
        filenames = [get_output_html_filename({
            "date": d,
            "type": type_str,
            "week": week,
            "year": year
        }) for d in dates]

        # Verify all in same week directory
        for path in games_paths:
            self.assertEqual(path.parent.parent, Path("tmp/2025-week09"))

        # Verify different day abbreviations
        expected_abbrs = ["thu", "sun", "mon"]
        for filename, expected_abbr in zip(filenames, expected_abbrs):
            self.assertIn(f"-{expected_abbr}-", filename)


if __name__ == '__main__':
    unittest.main()
