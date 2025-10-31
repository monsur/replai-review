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
    - Takes the season start date (first game of Week 1)
    - Calculates weeks since season start
    - If today is Mon/Tue/Wed, returns last week (games just finished)
    - Otherwise, returns current week
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
        current_week = (days_since_start // 7) + 1

        # If today is Monday, Tuesday, or Wednesday, we want the previous week
        # (games were played Thu-Mon of the previous week)
        day_of_week = reference_date.weekday()  # 0=Monday, 6=Sunday
        if day_of_week in [0, 1, 2]:  # Monday, Tuesday, Wednesday
            target_week = current_week - 1
        else:
            # Thursday through Sunday - current week's games
            target_week = current_week

        # Ensure week is at least 1
        target_week = max(1, target_week)

        return target_week


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
