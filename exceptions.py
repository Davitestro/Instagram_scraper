"""
Custom exceptions for Instagram scraper.
"""

class ScraperError(Exception):
    """Base exception for scraper errors."""
    pass


class BrowserConnectionError(ScraperError):
    """Raised when browser connection fails."""
    pass


class LoginError(ScraperError):
    """Raised when login fails."""
    pass


class MediaNotFoundError(ScraperError):
    """Raised when media is not found."""
    pass


class ProfileNotFoundError(ScraperError):
    """Raised when profile is not found."""
    pass


class ElementNotFoundError(ScraperError):
    """Raised when an element is not found."""
    pass


class RateLimitError(ScraperError):
    """Raised when rate limited."""
    pass