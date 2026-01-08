"""Custom exceptions for Rohlik.cz API client."""


class RohlikAPIError(Exception):
    """Base exception for Rohlik API errors."""
    pass


class InvalidCredentialsError(RohlikAPIError):
    """Raised when login credentials are invalid."""
    pass


class APIRequestFailedError(RohlikAPIError):
    """Raised when an API request fails."""
    pass

