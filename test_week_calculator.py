"""
Unit tests for week_calculator.py

Run with:
    python -m pytest test_week_calculator.py -v
    or
    python -m unittest test_week_calculator.py -v
"""

import unittest
from datetime import datetime, timedelta

from week_calculator import (
    DateBasedWeekCalculator,
    ManualWeekCalculator,
    create_week_calculator
)


class TestDateBasedWeekCalculator(unittest.TestCase):
    """Test the DateBasedWeekCalculator class."""

    def setUp(self):
        """Set up test fixtures."""
        # 2024 NFL season started on Thursday, September 5, 2024
        self.calculator = DateBasedWeekCalculator("2024-09-05")

    def test_week_1_thursday(self):
        """Test Week 1 on Thursday (opening day)."""
        test_date = datetime(2024, 9, 5)  # Thursday
        week = self.calculator.get_week(test_date)
        self.assertEqual(week, 1)

    def test_week_1_sunday(self):
        """Test Week 1 on Sunday."""
        test_date = datetime(2024, 9, 8)  # Sunday
        week = self.calculator.get_week(test_date)
        self.assertEqual(week, 1)

    def test_week_1_monday(self):
        """Test Week 1 on Monday Night Football."""
        test_date = datetime(2024, 9, 9)  # Monday
        week = self.calculator.get_week(test_date)
        # Monday is still Week 1 (part of Thu-Wed cycle)
        self.assertEqual(week, 1)

    def test_week_1_tuesday(self):
        """Test Tuesday of Week 1."""
        test_date = datetime(2024, 9, 10)  # Tuesday
        week = self.calculator.get_week(test_date)
        # Still Week 1 (part of Thu-Wed cycle)
        self.assertEqual(week, 1)

    def test_week_1_wednesday(self):
        """Test Wednesday of Week 1 (last day of week)."""
        test_date = datetime(2024, 9, 11)  # Wednesday
        week = self.calculator.get_week(test_date)
        # Still Week 1 (last day of Thu-Wed cycle)
        self.assertEqual(week, 1)

    def test_week_2_thursday(self):
        """Test Week 2 Thursday (should return Week 2)."""
        test_date = datetime(2024, 9, 12)  # Thursday
        week = self.calculator.get_week(test_date)
        # Thursday starts new week
        self.assertEqual(week, 2)

    def test_week_8_thursday(self):
        """Test Week 8 Thursday."""
        test_date = datetime(2024, 10, 24)  # Thursday, Week 8
        week = self.calculator.get_week(test_date)
        self.assertEqual(week, 8)

    def test_week_8_sunday(self):
        """Test Week 8 Sunday."""
        test_date = datetime(2024, 10, 27)  # Sunday, Week 8
        week = self.calculator.get_week(test_date)
        self.assertEqual(week, 8)

    def test_week_8_tuesday_returns_week_8(self):
        """Test Tuesday of Week 8."""
        test_date = datetime(2024, 10, 29)  # Tuesday of Week 8
        week = self.calculator.get_week(test_date)
        # Tuesday is part of Week 8 (Thu-Wed cycle)
        self.assertEqual(week, 8)

    def test_week_calculation_mid_season(self):
        """Test week calculation in mid-season."""
        # Week 10 started Thursday, Nov 7
        test_date = datetime(2024, 11, 10)  # Sunday, Week 10
        week = self.calculator.get_week(test_date)
        self.assertEqual(week, 10)

    def test_week_calculation_late_season(self):
        """Test week calculation late in season."""
        # Week 17 starts around Dec 26
        test_date = datetime(2024, 12, 29)  # Sunday, Week 17
        week = self.calculator.get_week(test_date)
        self.assertEqual(week, 17)

    def test_week_never_below_1(self):
        """Test that week number never goes below 1."""
        # Test date before season starts
        test_date = datetime(2024, 9, 1)  # Before season
        week = self.calculator.get_week(test_date)
        self.assertGreaterEqual(week, 1)

    def test_default_reference_date(self):
        """Test that get_week works without explicit reference_date."""
        # Should not raise an exception
        week = self.calculator.get_week()
        self.assertIsInstance(week, int)
        self.assertGreaterEqual(week, 1)

    def test_all_days_of_week_pattern(self):
        """Test that all days Thu-Wed return the same week."""
        base_date = datetime(2024, 9, 12)  # Thursday, Week 2

        # All days Thursday through Wednesday should return Week 2
        for days_offset in range(7):  # Thu, Fri, Sat, Sun, Mon, Tue, Wed
            test_date = base_date + timedelta(days=days_offset)
            week = self.calculator.get_week(test_date)
            self.assertEqual(week, 2, f"Failed for {test_date.strftime('%A')}")


class TestManualWeekCalculator(unittest.TestCase):
    """Test the ManualWeekCalculator class."""

    def test_returns_specified_week(self):
        """Test that calculator returns the manually specified week."""
        calculator = ManualWeekCalculator(5)
        week = calculator.get_week()
        self.assertEqual(week, 5)

    def test_ignores_reference_date(self):
        """Test that manual calculator ignores reference_date parameter."""
        calculator = ManualWeekCalculator(12)
        any_date = datetime(2024, 10, 15)
        week = calculator.get_week(any_date)
        self.assertEqual(week, 12)

    def test_week_1(self):
        """Test with week 1."""
        calculator = ManualWeekCalculator(1)
        self.assertEqual(calculator.get_week(), 1)

    def test_week_18(self):
        """Test with week 18 (last regular season week)."""
        calculator = ManualWeekCalculator(18)
        self.assertEqual(calculator.get_week(), 18)


class TestCreateWeekCalculator(unittest.TestCase):
    """Test the create_week_calculator factory function."""

    def test_creates_date_based_calculator(self):
        """Test factory creates DateBasedWeekCalculator when no manual week."""
        calculator = create_week_calculator("2024-09-05")
        self.assertIsInstance(calculator, DateBasedWeekCalculator)

    def test_creates_manual_calculator(self):
        """Test factory creates ManualWeekCalculator when manual_week provided."""
        calculator = create_week_calculator("2024-09-05", manual_week=8)
        self.assertIsInstance(calculator, ManualWeekCalculator)

    def test_manual_week_overrides_date_based(self):
        """Test that manual_week parameter takes precedence."""
        calculator = create_week_calculator("2024-09-05", manual_week=10)
        week = calculator.get_week()
        self.assertEqual(week, 10)

    def test_factory_with_none_manual_week(self):
        """Test factory with explicit None for manual_week."""
        calculator = create_week_calculator("2024-09-05", manual_week=None)
        self.assertIsInstance(calculator, DateBasedWeekCalculator)


class TestEdgeCases(unittest.TestCase):
    """Test edge cases and boundary conditions."""

    def test_season_start_is_week_1(self):
        """Test that season start date is always Week 1."""
        calculator = DateBasedWeekCalculator("2024-09-05")
        season_start = datetime(2024, 9, 5)
        week = calculator.get_week(season_start)
        self.assertEqual(week, 1)

    def test_day_before_season_start(self):
        """Test day before season starts."""
        calculator = DateBasedWeekCalculator("2024-09-05")
        day_before = datetime(2024, 9, 4)
        week = calculator.get_week(day_before)
        # Should return at least 1 (clamped)
        self.assertGreaterEqual(week, 1)

    def test_far_future_date(self):
        """Test with a date far in the future."""
        calculator = DateBasedWeekCalculator("2024-09-05")
        far_future = datetime(2025, 12, 31)
        week = calculator.get_week(far_future)
        # Should return some large week number
        self.assertGreater(week, 50)

    def test_different_season_start_date(self):
        """Test with a different season start date."""
        # 2023 season started Thursday, September 7, 2023
        calculator = DateBasedWeekCalculator("2023-09-07")
        test_date = datetime(2023, 9, 10)  # Sunday of Week 1
        week = calculator.get_week(test_date)
        self.assertEqual(week, 1)

    def test_manual_week_zero(self):
        """Test manual calculator with week 0 (edge case)."""
        calculator = ManualWeekCalculator(0)
        self.assertEqual(calculator.get_week(), 0)

    def test_manual_week_negative(self):
        """Test manual calculator with negative week (edge case)."""
        calculator = ManualWeekCalculator(-1)
        self.assertEqual(calculator.get_week(), -1)


class TestRealWorldScenarios(unittest.TestCase):
    """Test real-world usage scenarios."""

    def test_newsletter_generation_tuesday(self):
        """Test typical newsletter generation on Tuesday morning."""
        # Newsletter typically generated Tuesday after Monday Night Football
        calculator = DateBasedWeekCalculator("2024-09-05")

        # Tuesday, October 29, 2024 - Week 8 (games from Thu Oct 24 - Mon Oct 28)
        # Tuesday is still part of Week 8's Thu-Wed cycle
        tuesday_morning = datetime(2024, 10, 29)
        week = calculator.get_week(tuesday_morning)
        self.assertEqual(week, 8)

    def test_newsletter_generation_wednesday(self):
        """Test newsletter generation on Wednesday (last day of week)."""
        calculator = DateBasedWeekCalculator("2024-09-05")

        # Wednesday Oct 30 is the last day of Week 8's Thu-Wed cycle
        wednesday = datetime(2024, 10, 30)
        week = calculator.get_week(wednesday)
        self.assertEqual(week, 8)

    def test_manual_override_for_past_week(self):
        """Test generating newsletter for a past week."""
        # User wants to generate newsletter for Week 5 specifically
        calculator = create_week_calculator("2024-09-05", manual_week=5)
        week = calculator.get_week()
        self.assertEqual(week, 5)

    def test_full_season_progression(self):
        """Test week progression throughout entire season."""
        calculator = DateBasedWeekCalculator("2024-09-05")

        # Test a Thursday from each week
        expected_weeks = [
            (datetime(2024, 9, 5), 1),   # Week 1 Thursday
            (datetime(2024, 9, 12), 2),  # Week 2 Thursday
            (datetime(2024, 9, 19), 3),  # Week 3 Thursday
            (datetime(2024, 9, 26), 4),  # Week 4 Thursday
            (datetime(2024, 10, 3), 5),  # Week 5 Thursday
            (datetime(2024, 10, 10), 6), # Week 6 Thursday
            (datetime(2024, 10, 17), 7), # Week 7 Thursday
            (datetime(2024, 10, 24), 8), # Week 8 Thursday
        ]

        for test_date, expected_week in expected_weeks:
            with self.subTest(date=test_date):
                week = calculator.get_week(test_date)
                self.assertEqual(week, expected_week)


if __name__ == '__main__':
    unittest.main()
