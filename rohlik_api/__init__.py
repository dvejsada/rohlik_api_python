"""Rohlik.cz API Python Client.

A Python package for interacting with the Rohlik.cz API using httpx with HTTP/2 support.
"""

from .client import RohlikAPI
from .helpers import mask_data
from .errors import RohlikAPIError, InvalidCredentialsError, APIRequestFailedError
from .http_client import HttpClient
from .auth import AuthManager
from .endpoints import Endpoints, BASE_URL

__version__ = "0.1.0"
__all__ = [
    # Main client (facade)
    "RohlikAPI",
    # Utilities
    "mask_data",
    # Errors
    "RohlikAPIError",
    "InvalidCredentialsError",
    "APIRequestFailedError",
    # Advanced: Low-level components
    "HttpClient",
    "AuthManager",
    "Endpoints",
    "BASE_URL",
]
