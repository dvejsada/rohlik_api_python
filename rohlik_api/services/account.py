"""Account service for Rohlik.cz API."""

from __future__ import annotations

import logging
from typing import Any

from ..endpoints import Endpoints
from ..errors import APIRequestFailedError
from ..http_client import HTTP_ERRORS
from ..models import ShoppingList
from .base import BaseService

_LOGGER = logging.getLogger(__name__)


class AccountService(BaseService):
    """Service for account-related operations."""

    async def get_premium_profile(self) -> dict[str, Any] | None:
        """Get premium profile information.

        Returns:
            dict: Premium profile information or None if request fails
        """
        return await self._fetch_endpoint(Endpoints.PREMIUM_PROFILE, "premium profile")

    async def get_bags_info(self) -> dict[str, Any] | None:
        """Get reusable bags user information.

        Returns:
            dict: Bags information or None if request fails
        """
        return await self._fetch_endpoint(Endpoints.BAGS, "bags info")

    async def get_announcements(self) -> dict[str, Any] | None:
        """Get top announcements.

        Returns:
            dict: Announcements or None if request fails
        """
        return await self._fetch_endpoint(Endpoints.ANNOUNCEMENTS, "announcements")

    async def get_shopping_list(self, shopping_list_id: str) -> ShoppingList:
        """Retrieve a shopping list by its ID.

        Args:
            shopping_list_id: The ID of the shopping list to retrieve.

        Returns:
            A ShoppingList with its name and products.

        Raises:
            ValueError: If shopping_list_id is not provided.
            APIRequestFailedError: If the request fails.
        """
        if not shopping_list_id:
            raise ValueError("Missing argument - shopping list id")

        await self._ensure_logged_in()

        url = Endpoints.shopping_list(shopping_list_id)

        try:
            response = await self._http.get(url)
            response.raise_for_status()
            return ShoppingList.from_api(response.json())
        except HTTP_ERRORS as err:
            _LOGGER.error("Request failed: %s", err)
            raise APIRequestFailedError(f"Request failed: {err}") from err
