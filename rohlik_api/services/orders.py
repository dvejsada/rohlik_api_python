"""Orders service for Rohlik.cz API."""

from __future__ import annotations

import logging
from typing import Any

from ..endpoints import Endpoints
from ..http_client import HTTP_ERRORS
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
        except HTTP_ERRORS as err:
            _LOGGER.warning("Error fetching delivered orders: %s", err)
            return None

    async def get_all_delivered(self, page_size: int = 50) -> list[dict[str, Any]]:
        """Get every delivered order by paginating until the list is exhausted.

        Args:
            page_size: Number of orders fetched per request.

        Returns:
            list: All delivered orders (empty if there are none). If a request
            fails partway through pagination, the orders gathered so far are
            returned and a warning is logged, so the result may be incomplete.
        """
        await self._ensure_logged_in()

        all_orders: list[dict[str, Any]] = []
        offset = 0
        while True:
            page = await self.get_delivered(limit=page_size, offset=offset)
            if page is None:
                # Request error (already logged by get_delivered): stop and
                # return what we have rather than silently looping forever.
                _LOGGER.warning(
                    "Stopped paginating delivered orders at offset %s; result may be incomplete",
                    offset,
                )
                break
            if not page:
                break  # Empty page: genuinely no more orders.
            all_orders.extend(page)
            if len(page) < page_size:
                break
            offset += page_size

        return all_orders

    async def get_detail(self, order_id: int) -> dict[str, Any] | None:
        """Get full detail for a single order, including its line items.

        Args:
            order_id: The ID of the order.

        Returns:
            dict: The order detail, or None if the order does not exist (404)
            or the request fails.
        """
        await self._ensure_logged_in()

        try:
            response = await self._http.get(Endpoints.order_detail(order_id))
            if response.status == 404:
                return None
            response.raise_for_status()
            detail: dict[str, Any] = response.json()
            return detail
        except HTTP_ERRORS as err:
            _LOGGER.warning("Error fetching order detail for %s: %s", order_id, err)
            return None
