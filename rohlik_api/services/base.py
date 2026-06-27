"""Base service class for Rohlik.cz API services."""

from __future__ import annotations

import logging
from typing import Any

from ..auth import AuthManager
from ..http_client import HTTP_ERRORS, HttpClient

_LOGGER = logging.getLogger(__name__)


class BaseService:
    """Base class for all Rohlik API services.

    Provides common functionality like HTTP client access and authentication.

    Error-handling convention:
        Read-only / optional fetches (most ``get_*`` and ``search`` methods, and
        anything using :meth:`_fetch_endpoint`) return ``None`` on a request
        failure, so an aggregate call such as :meth:`RohlikAPI.get_data` can
        degrade gracefully. Critical or mutating operations (login, logout,
        ``cart.get_content``, ``cart.delete_item``, ``account.get_shopping_list``)
        instead raise :class:`~rohlik_api.APIRequestFailedError`.

    Args:
        http_client: The HTTP client instance.
        auth_manager: The authentication manager instance.
    """

    def __init__(self, http_client: HttpClient, auth_manager: AuthManager) -> None:
        self._http = http_client
        self._auth = auth_manager

    async def _ensure_logged_in(self) -> None:
        """Ensure the client is logged in before making requests."""
        await self._auth.ensure_logged_in()

    async def _fetch_endpoint(
        self,
        endpoint: str,
        error_context: str,
    ) -> dict[str, Any] | None:
        """Fetch data from an endpoint with error handling.

        Args:
            endpoint: The API endpoint path.
            error_context: Context string for error logging.

        Returns:
            The parsed JSON response, or None if the request fails.
        """
        await self._ensure_logged_in()

        try:
            response = await self._http.get(endpoint)
            response.raise_for_status()
            data: dict[str, Any] = response.json()
            return data
        except HTTP_ERRORS as err:
            _LOGGER.warning("Error fetching %s: %s", error_context, err)
            return None
