"""Custom exceptions for the Rohlik.cz API client."""


class RohlikAPIError(Exception):
    """Base exception for all Rohlik API errors."""


class InvalidCredentialsError(RohlikAPIError):
    """Raised when login credentials are invalid."""


class APIRequestFailedError(RohlikAPIError):
    """Raised when an API request fails (network or HTTP error)."""
