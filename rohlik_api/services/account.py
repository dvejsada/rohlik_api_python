"""Account service for Rohlik.cz API."""

import logging
from typing import Dict, Any, Optional

import httpx

from .base import BaseService
from ..endpoints import Endpoints
from ..errors import APIRequestFailedError

_LOGGER = logging.getLogger(__name__)


class AccountService(BaseService):
    """Service for account-related operations."""

    async def get_premium_profile(self) -> Optional[Dict[str, Any]]:
        """Get premium profile information.

        Returns:
            dict: Premium profile information or None if request fails
        """
        return await self._fetch_endpoint(Endpoints.PREMIUM_PROFILE, "premium profile")

    async def get_bags_info(self) -> Optional[Dict[str, Any]]:
        """Get reusable bags user information.

        Returns:
            dict: Bags information or None if request fails
        """
        return await self._fetch_endpoint(Endpoints.BAGS, "bags info")

    async def get_announcements(self) -> Optional[Dict[str, Any]]:
        """Get top announcements.

        Returns:
            dict: Announcements or None if request fails
        """
        return await self._fetch_endpoint(Endpoints.ANNOUNCEMENTS, "announcements")

    async def get_shopping_list(self, shopping_list_id: str) -> Dict[str, Any]:
        """Retrieve a shopping list by its ID.

        Args:
            shopping_list_id: The ID of the shopping list to retrieve

        Returns:
            dict: The shopping list details with 'name' and 'products_in_list' keys

        Raises:
            ValueError: If shopping_list_id is not provided
            APIRequestFailedError: If the request fails
        """
        if not shopping_list_id:
            raise ValueError("Missing argument - shopping list id")

        await self._ensure_logged_in()

        url = Endpoints.shopping_list(shopping_list_id)

        try:
            response = await self._http.get(url)
            response.raise_for_status()
            search_data = response.json()

            return {
                "name": search_data.get("name"),
                "products_in_list": search_data.get("products", [])
            }

        except httpx.HTTPError as err:
            _LOGGER.error(f"Request failed: {err}")
            raise APIRequestFailedError(f"Request failed: {err}")
