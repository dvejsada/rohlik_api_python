"""Rohlik.cz API Python Client.

A Python package for interacting with the Rohlik.cz API using httpx with HTTP/2 support.
"""

from .client import RohlikAPI, mask_data
from .errors import RohlikAPIError, InvalidCredentialsError, APIRequestFailedError

__version__ = "0.1.0"
__all__ = [
    "RohlikAPI",
    "mask_data",
    "RohlikAPIError",
    "InvalidCredentialsError",
    "APIRequestFailedError",
]
