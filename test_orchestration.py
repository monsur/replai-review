"""
Integration tests for run_all_v2.sh orchestration script

Tests the shell script's argument parsing, validation, and error handling.

Run with:
    python -m unittest test_orchestration.py -v
"""

import unittest
import subprocess
import json
import tempfile
from pathlib import Path
from datetime import datetime
from unittest.mock import patch, MagicMock


class TestOrchestrationScript(unittest.TestCase):
    """Test run_all_v2.sh orchestration script."""

    def setUp(self):
        """Set up test fixtures."""
        self.script_path = Path("run_all_v2.sh")
        self.script_dir = Path.cwd()

    def test_script_exists(self):
        """Test that run_all_v2.sh exists."""
        self.assertTrue(
            self.script_path.exists(),
            f"Script not found: {self.script_path}"
        )

    def test_script_is_executable(self):
        """Test that script is executable."""
        self.assertTrue(
            self.script_path.stat().st_mode & 0o111,
            "Script is not executable"
        )

    def test_help_flag(self):
        """Test that --help flag works."""
        result = subprocess.run(
            ["bash", str(self.script_path), "--help"],
            capture_output=True,
            text=True
        )

        self.assertEqual(result.returncode, 0, "Help flag failed")
        self.assertIn("Usage:", result.stdout)
        self.assertIn("--date", result.stdout)
        self.assertIn("--type", result.stdout)

    def test_missing_required_date_argument(self):
        """Test that script fails without --date argument."""
        result = subprocess.run(
            ["bash", str(self.script_path), "--type", "day"],
            capture_output=True,
            text=True
        )

        self.assertEqual(result.returncode, 3, "Should fail with exit code 3")
        self.assertIn("Missing required argument", result.stderr)

    def test_invalid_date_format(self):
        """Test that script rejects invalid date format."""
        result = subprocess.run(
            ["bash", str(self.script_path), "--date", "not-a-date", "--type", "day"],
            capture_output=True,
            text=True
        )

        self.assertEqual(result.returncode, 3)
        self.assertIn("Invalid date format", result.stderr)

    def test_invalid_date_month(self):
        """Test that script rejects invalid month."""
        result = subprocess.run(
            ["bash", str(self.script_path), "--date", "20251309", "--type", "day"],
            capture_output=True,
            text=True
        )

        self.assertEqual(result.returncode, 3)
        self.assertIn("Invalid month", result.stderr)

    def test_invalid_date_day(self):
        """Test that script rejects invalid day."""
        result = subprocess.run(
            ["bash", str(self.script_path), "--date", "20251132", "--type", "day"],
            capture_output=True,
            text=True
        )

        self.assertEqual(result.returncode, 3)
        self.assertIn("Invalid day", result.stderr)

    def test_invalid_type_argument(self):
        """Test that script rejects invalid type."""
        result = subprocess.run(
            ["bash", str(self.script_path), "--date", "20251109", "--type", "invalid"],
            capture_output=True,
            text=True
        )

        self.assertEqual(result.returncode, 3)
        self.assertIn("Invalid type", result.stderr)

    def test_invalid_provider_argument(self):
        """Test that script rejects invalid provider."""
        result = subprocess.run(
            ["bash", str(self.script_path), "--date", "20251109", "--type", "day",
             "--provider", "invalid"],
            capture_output=True,
            text=True
        )

        self.assertEqual(result.returncode, 3)
        self.assertIn("Invalid provider", result.stderr)

    def test_valid_provider_claude(self):
        """Test that claude is accepted as valid provider."""
        # This should fail due to missing games, not invalid provider
        result = subprocess.run(
            ["bash", str(self.script_path), "--date", "20251109", "--type", "day",
             "--provider", "claude"],
            capture_output=True,
            text=True,
            timeout=30
        )

        # Should fail due to missing games, not provider validation
        self.assertNotIn("Invalid provider", result.stderr)

    def test_valid_provider_openai(self):
        """Test that openai is accepted as valid provider."""
        # This should fail due to missing games, not invalid provider
        result = subprocess.run(
            ["bash", str(self.script_path), "--date", "20251109", "--type", "day",
             "--provider", "openai"],
            capture_output=True,
            text=True,
            timeout=30
        )

        # Should fail due to missing games, not provider validation
        self.assertNotIn("Invalid provider", result.stderr)

    def test_valid_provider_gemini(self):
        """Test that gemini is accepted as valid provider."""
        # This should fail due to missing games, not invalid provider
        result = subprocess.run(
            ["bash", str(self.script_path), "--date", "20251109", "--type", "day",
             "--provider", "gemini"],
            capture_output=True,
            text=True,
            timeout=30
        )

        # Should fail due to missing games, not provider validation
        self.assertNotIn("Invalid provider", result.stderr)

    def test_valid_type_day(self):
        """Test that 'day' is accepted as valid type."""
        # This should fail due to missing games, not type validation
        result = subprocess.run(
            ["bash", str(self.script_path), "--date", "20251109", "--type", "day"],
            capture_output=True,
            text=True,
            timeout=30
        )

        # Should fail due to missing games, not type validation
        self.assertNotIn("Invalid type", result.stderr)

    def test_valid_type_week(self):
        """Test that 'week' is accepted as valid type."""
        # This should fail due to missing games, not type validation
        result = subprocess.run(
            ["bash", str(self.script_path), "--date", "20251109", "--type", "week"],
            capture_output=True,
            text=True,
            timeout=30
        )

        # Should fail due to missing games, not type validation
        self.assertNotIn("Invalid type", result.stderr)

    def test_missing_config_file(self):
        """Test that script fails when config file is missing."""
        result = subprocess.run(
            ["bash", str(self.script_path),
             "--date", "20251109",
             "--type", "day",
             "--config", "/nonexistent/config.yaml"],
            capture_output=True,
            text=True,
            timeout=30
        )

        self.assertEqual(result.returncode, 2)
        self.assertIn("Config file not found", result.stderr)

    def test_unknown_option(self):
        """Test that script rejects unknown options."""
        result = subprocess.run(
            ["bash", str(self.script_path), "--unknown-option", "value"],
            capture_output=True,
            text=True
        )

        self.assertEqual(result.returncode, 3)
        self.assertIn("Unknown option", result.stderr)

    def test_date_format_8_digits(self):
        """Test that date must be exactly 8 digits."""
        # Too short
        result = subprocess.run(
            ["bash", str(self.script_path), "--date", "2025110", "--type", "day"],
            capture_output=True,
            text=True
        )
        self.assertEqual(result.returncode, 3)

        # Too long
        result = subprocess.run(
            ["bash", str(self.script_path), "--date", "202511099", "--type", "day"],
            capture_output=True,
            text=True
        )
        self.assertEqual(result.returncode, 3)

    def test_valid_date_formats(self):
        """Test various valid date formats."""
        valid_dates = [
            "20250101",  # January 1
            "20251231",  # December 31
            "20251109",  # November 9
        ]

        for date in valid_dates:
            result = subprocess.run(
                ["bash", str(self.script_path), "--date", date, "--type", "day"],
                capture_output=True,
                text=True,
                timeout=30
            )

            # Should not fail due to date validation
            self.assertNotIn("Invalid date format", result.stderr,
                           f"Valid date {date} was rejected")


class TestArgumentParsing(unittest.TestCase):
    """Test argument parsing logic."""

    def test_date_type_combination(self):
        """Test that both --date and --type are parsed correctly."""
        result = subprocess.run(
            ["bash", "run_all_v2.sh", "--date", "20251109", "--type", "day"],
            capture_output=True,
            text=True,
            timeout=30
        )

        # Should not fail due to argument parsing
        self.assertNotIn("Missing required argument", result.stderr)

    def test_argument_order_independence(self):
        """Test that argument order doesn't matter."""
        # Test different orders
        orders = [
            ["--date", "20251109", "--type", "day"],
            ["--type", "day", "--date", "20251109"],
        ]

        for args in orders:
            result = subprocess.run(
                ["bash", "run_all_v2.sh"] + args,
                capture_output=True,
                text=True,
                timeout=30
            )

            # Should not fail due to argument parsing
            self.assertNotIn("Missing required argument", result.stderr)


class TestOutputFormatting(unittest.TestCase):
    """Test output formatting and messaging."""

    def test_help_output_format(self):
        """Test that help output is properly formatted."""
        result = subprocess.run(
            ["bash", "run_all_v2.sh", "--help"],
            capture_output=True,
            text=True
        )

        self.assertIn("Usage:", result.stdout)
        self.assertIn("Required arguments:", result.stdout)
        self.assertIn("Optional arguments:", result.stdout)
        self.assertIn("Examples:", result.stdout)

    def test_error_goes_to_stderr(self):
        """Test that errors are written to stderr."""
        result = subprocess.run(
            ["bash", "run_all_v2.sh", "--date", "invalid", "--type", "day"],
            capture_output=True,
            text=True
        )

        # Error messages should go to stderr
        self.assertTrue(len(result.stderr) > 0)
        self.assertIn("❌", result.stderr)

    def test_help_goes_to_stdout(self):
        """Test that help text goes to stdout."""
        result = subprocess.run(
            ["bash", "run_all_v2.sh", "--help"],
            capture_output=True,
            text=True
        )

        self.assertTrue(len(result.stdout) > 0)


class TestValidationFunctions(unittest.TestCase):
    """Test individual validation functions embedded in script."""

    def test_date_validation_comprehensive(self):
        """Test comprehensive date validation."""
        test_cases = [
            # (date, should_pass)
            ("20251109", True),   # Valid
            ("20250101", True),   # Valid
            ("20251231", True),   # Valid
            ("20240229", True),   # Valid (2024 is leap year)
            ("20250229", False),  # Invalid (2025 not leap year)
            ("20250230", False),  # Invalid (no Feb 30)
            ("20251301", False),  # Invalid month
            ("20250001", False),  # Invalid month
            ("20250132", False),  # Invalid day
            ("20250100", False),  # Invalid day
            ("202511", False),    # Too short
            ("202511099", False), # Too long
            ("not-a-date", False),# Non-numeric
            ("2025-11-09", False),# Wrong format
        ]

        for date, should_pass in test_cases:
            result = subprocess.run(
                ["bash", "run_all_v2.sh", "--date", date, "--type", "day"],
                capture_output=True,
                text=True,
                timeout=10
            )

            if should_pass:
                self.assertNotIn("Invalid", result.stderr,
                               f"Valid date {date} was rejected: {result.stderr}")
            else:
                self.assertIn("Invalid", result.stderr,
                            f"Invalid date {date} was not rejected: {result.stderr}")


if __name__ == '__main__':
    unittest.main()
