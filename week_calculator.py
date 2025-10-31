"""
NFL Week Calculator Module

This module provides an isolated, swappable system for determining which NFL week to process.
Currently implements date-based calculation, but can be easily extended with other strategies.
"""

from abc import ABC, abstractmethod
from datetime import datetime, timedelta
from typing import Optional


class WeekCalculator(ABC):
    """
    Abstract base class for NFL week calculation strategies.

    This allows different week determination methods to be swapped in/out easily.
    """

    @abstractmethod
    def get_week(self, reference_date: Optional[datetime] = None) -> int:
        """
        Calculate the NFL week number.

        Args:
            reference_date: Optional date to use for calculation. Defaults to today.

        Returns:
            The NFL week number (1-18 for regular season)
        """
        pass


class DateBasedWeekCalculator(WeekCalculator):
    """
    Calculates NFL week based on the current date and season start date.

    Logic:
    - Takes the season start date (first game of Week 1, typically a Thursday)
    - Calculates which week we're in based on Thursday-Wednesday cycles
    - Returns the current week number (1-18 for regular season)

    Examples:
    - If season starts Thursday Sept 5:
      - Thursday Sept 5 - Wednesday Sept 11: Week 1
      - Thursday Sept 12 - Wednesday Sept 18: Week 2
      - Tuesday Oct 29 (day 54): Week 8
    """

    def __init__(self, season_start_date: str):
        """
        Initialize the calculator with the season start date.

        Args:
            season_start_date: Date string in YYYY-MM-DD format (e.g., "2024-09-05")
        """
        self.season_start = datetime.strptime(season_start_date, "%Y-%m-%d")

    def get_week(self, reference_date: Optional[datetime] = None) -> int:
        """
        Calculate NFL week based on date.

        Args:
            reference_date: Optional date to use for calculation. Defaults to today.

        Returns:
            The NFL week number
        """
        if reference_date is None:
            reference_date = datetime.now()

        # Calculate days since season start
        days_since_start = (reference_date - self.season_start).days

        # Calculate current week (1-indexed)
        # NFL weeks run Thursday to Wednesday
        # Since season starts on a Thursday (day 0), this calculation
        # naturally aligns weeks to Thursday-Wednesday:
        # - Days 0-6: Week 1 (Thu-Wed)
        # - Days 7-13: Week 2 (Thu-Wed)
        # - Days 49-55: Week 8 (Thu-Wed)
        # etc.
        week = (days_since_start // 7) + 1

        # Ensure week is at least 1
        week = max(1, week)

        return week


class ManualWeekCalculator(WeekCalculator):
    """
    Simple calculator that returns a manually specified week.
    Useful for testing or when week is provided via command-line argument.
    """

    def __init__(self, week: int):
        """
        Initialize with a specific week number.

        Args:
            week: The NFL week number to return
        """
        self.week = week

    def get_week(self, reference_date: Optional[datetime] = None) -> int:
        """Return the manually specified week."""
        return self.week


# Factory function to create the appropriate calculator
def create_week_calculator(
    season_start_date: str,
    manual_week: Optional[int] = None
) -> WeekCalculator:
    """
    Factory function to create the appropriate week calculator.

    Args:
        season_start_date: Season start date in YYYY-MM-DD format
        manual_week: If provided, uses manual week; otherwise uses date-based calculation

    Returns:
        A WeekCalculator instance
    """
    if manual_week is not None:
        return ManualWeekCalculator(manual_week)
    else:
        return DateBasedWeekCalculator(season_start_date)


if __name__ == "__main__":
    # Example usage and testing
    calculator = DateBasedWeekCalculator("2024-09-05")

    # Test with different dates
    test_dates = [
        ("2024-10-28", "Tuesday, Week 8"),  # Should return Week 8
        ("2024-10-24", "Thursday, Week 8"),  # Should return Week 8
        ("2024-10-27", "Sunday, Week 8"),  # Should return Week 8
    ]

    print("Testing DateBasedWeekCalculator:")
    for date_str, description in test_dates:
        test_date = datetime.strptime(date_str, "%Y-%m-%d")
        week = calculator.get_week(test_date)
        print(f"  {description}: Week {week}")

    # Test manual calculator
    manual_calc = ManualWeekCalculator(5)
    print(f"\nManual calculator (week 5): Week {manual_calc.get_week()}")
