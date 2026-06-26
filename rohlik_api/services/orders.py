"""Orders service for Rohlik.cz API."""

from __future__ import annotations

import logging
from typing import Any

import httpx

from ..endpoints import Endpoints
from .base import BaseService

_LOGGER = logging.getLogger(__name__)


class OrderService(BaseService):
    """Service for order-related operations."""

    async def get_next(self) -> dict[str, Any] | None:
        """Get upcoming order information.

        Returns:
            dict: Next order information or None if request fails
        """
        return await self._fetch_endpoint(Endpoints.NEXT_ORDER, "next order")

    async def get_last(self) -> dict[str, Any] | None:
        """Get last delivered order information.

        Returns:
            dict: Last order information or None if request fails
        """
        return await self._fetch_endpoint(Endpoints.LAST_ORDER, "last order")

    async def get_delivered(self, limit: int = 50, offset: int = 0) -> list[dict[str, Any]] | None:
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
            orders: list[dict[str, Any]] = response.json()
            return orders
        except httpx.HTTPError as err:
            _LOGGER.error("Error fetching delivered orders: %s", err)
            return None
