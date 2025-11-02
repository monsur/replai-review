"""
Custom Exceptions

This module defines custom exception types for better error handling
and debugging throughout the newsletter generation system.
"""

from typing import List, Optional


class NewsletterException(Exception):
    """Base exception for all newsletter-related errors."""
    pass


class ScraperException(NewsletterException):
    """
    Exception raised when web scraping fails.

    This can occur when:
    - ESPN's HTML structure changes
    - Network connection fails
    - Page content is not as expected
    """
    pass


class ValidationException(NewsletterException):
    """
    Exception raised when data validation fails.

    Attributes:
        message: Error description
        errors: List of validation error details
    """

    def __init__(self, message: str, errors: Optional[List] = None):
        super().__init__(message)
        self.errors = errors or []

    def __str__(self):
        base_msg = super().__str__()
        if self.errors:
            error_details = "\n".join(f"  - {error}" for error in self.errors)
            return f"{base_msg}\nValidation errors:\n{error_details}"
        return base_msg


class AIProviderException(NewsletterException):
    """
    Exception raised when AI provider operations fail.

    This can occur when:
    - API key is invalid or missing
    - API rate limit is exceeded
    - AI service is unavailable
    - Response format is unexpected
    """
    pass


class ConfigurationException(NewsletterException):
    """
    Exception raised when configuration is invalid.

    This can occur when:
    - Required config fields are missing
    - Config values are out of valid range
    - Config file format is incorrect
    """
    pass


class WeekCalculationException(NewsletterException):
    """
    Exception raised when week calculation fails.

    This can occur when:
    - Season start date is invalid
    - Current date is before season start
    - Week number is out of valid range
    """
    pass
