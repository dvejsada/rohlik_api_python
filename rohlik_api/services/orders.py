"""Orders service for Rohlik.cz API."""

import logging
from typing import Dict, Any, List, Optional

import httpx

from .base import BaseService
from ..endpoints import Endpoints

_LOGGER = logging.getLogger(__name__)


class OrderService(BaseService):
    """Service for order-related operations."""

    async def get_next(self) -> Optional[Dict[str, Any]]:
        """Get upcoming order information.

        Returns:
            dict: Next order information or None if request fails
        """
        return await self._fetch_endpoint(Endpoints.NEXT_ORDER, "next order")

    async def get_last(self) -> Optional[Dict[str, Any]]:
        """Get last delivered order information.

        Returns:
            dict: Last order information or None if request fails
        """
        return await self._fetch_endpoint(Endpoints.LAST_ORDER, "last order")

    async def get_delivered(
        self,
        limit: int = 50,
        offset: int = 0
    ) -> Optional[List[Dict[str, Any]]]:
        """Get list of delivered orders.

        Args:
            limit: Maximum number of orders to return
            offset: Offset for pagination

        Returns:
            list: List of delivered orders or None if request fails
        """
        await self._ensure_logged_in()

        try:
            url = Endpoints.delivered_orders(limit=limit, offset=offset)
            response = await self._http.get(url)
            response.raise_for_status()
            return response.json()
        except httpx.HTTPError as err:
            _LOGGER.error(f"Error fetching delivered orders: {err}")
            return None
