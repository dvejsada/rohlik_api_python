"""Base service class for Rohlik.cz API services."""

import logging
from typing import Optional, Dict, Any

import httpx

from ..http_client import HttpClient
from ..auth import AuthManager

_LOGGER = logging.getLogger(__name__)


class BaseService:
    """Base class for all Rohlik API services.

    Provides common functionality like HTTP client access and authentication.

    Args:
        http_client: The HTTP client instance
        auth_manager: The authentication manager instance
    """

    def __init__(self, http_client: HttpClient, auth_manager: AuthManager):
        self._http = http_client
        self._auth = auth_manager

    async def _ensure_logged_in(self) -> None:
        """Ensure the client is logged in before making requests."""
        await self._auth.ensure_logged_in()

    async def _fetch_endpoint(
        self,
        endpoint: str,
        error_context: str
    ) -> Optional[Dict[str, Any]]:
        """Fetch data from an endpoint with error handling.

        Args:
            endpoint: The API endpoint path
            error_context: Context string for error logging

        Returns:
            dict: Response data or None if request fails
        """
        await self._ensure_logged_in()

        try:
            response = await self._http.get(endpoint)
            response.raise_for_status()
            return response.json()
        except httpx.HTTPError as err:
            _LOGGER.error(f"Error fetching {error_context}: {err}")
            return None
