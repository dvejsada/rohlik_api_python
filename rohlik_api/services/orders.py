"""Orders service for Rohlik.cz API."""

from __future__ import annotations

import logging
from typing import Any, Literal

from ..endpoints import Endpoints
from ..errors import APIRequestFailedError
from ..http_client import HTTP_ERRORS
from ..models import DeliveryTracking, NextDelivery, OrderItem, UpcomingOrder
from .base import BaseService

TrackingOutcome = Literal["ok", "not_found", "failed"]

# Request failures plus an unparseable body (Response.json raises ValueError,
# which is not a transport error and so not part of HTTP_ERRORS).
_READ_ERRORS: tuple[type[Exception], ...] = (*HTTP_ERRORS, ValueError)

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

    async def get_upcoming(self) -> list[UpcomingOrder] | None:
        """Get upcoming (not yet delivered) orders as typed models.

        Typed counterpart of :meth:`get_next`, which keeps returning the raw list.

        Returns:
            list: Upcoming orders, soonest delivery slot first (empty if there
            are none), or None if the request fails or the response is not a
            list.
        """
        await self._ensure_logged_in()

        try:
            response = await self._http.get(Endpoints.NEXT_ORDER)
            response.raise_for_status()
            data = response.json()
        except _READ_ERRORS as err:
            _LOGGER.warning("Error fetching upcoming orders: %s", err)
            return None
        if not isinstance(data, list):
            _LOGGER.warning("Unexpected upcoming orders response: %s", type(data).__name__)
            return None
        return UpcomingOrder.list_from_api(data)

    async def _fetch_delivery_tracking(
        self, order_id: int
    ) -> tuple[TrackingOutcome, DeliveryTracking | None, Exception | None]:
        """Fetch delivery tracking, telling "no tracking" (404) from a failure.

        Returns the outcome, the parsed tracking (only for ``"ok"``) and, for
        ``"failed"``, the underlying error to chain.
        """
        # Built outside the try so an invalid order ID raises instead of looking
        # like a failed request.
        url = Endpoints.delivery_tracking(order_id)
        await self._ensure_logged_in()

        try:
            response = await self._http.get(url)
            if response.status == 404:
                return "not_found", None, None
            response.raise_for_status()
            data = response.json()
        except _READ_ERRORS as err:
            _LOGGER.warning("Error fetching delivery tracking for %s: %s", order_id, err)
            return "failed", None, err
        if not isinstance(data, dict) or not isinstance(data.get("orderId"), int):
            # A 200 without an order ID (e.g. an error envelope) is not tracking.
            error = ValueError(f"unexpected delivery tracking response: {type(data).__name__}")
            _LOGGER.warning("Error fetching delivery tracking for %s: %s", order_id, error)
            return "failed", None, error
        return "ok", DeliveryTracking.from_api(data), None

    async def get_delivery_tracking(
        self, order_id: int, *, raise_on_error: bool = False
    ) -> DeliveryTracking | None:
        """Get live delivery tracking for an order: status, ETA, stops ahead, courier.

        Uses an unofficial endpoint observed on Rohlík.cz. The shop returns
        tracking without progress until the order is queued for a courier.

        Args:
            order_id: The ID of the order.
            raise_on_error: If True, raise on a failed request instead of
                returning None, so None means only "no tracking" (404).

        Returns:
            DeliveryTracking: The tracking, or None if the shop has no tracking
            for the order (404) or, unless ``raise_on_error``, the request fails.

        Raises:
            APIRequestFailedError: With ``raise_on_error``, if the request fails.
        """
        outcome, tracking, error = await self._fetch_delivery_tracking(order_id)
        if outcome == "failed" and raise_on_error:
            raise APIRequestFailedError(
                f"Cannot fetch delivery tracking for order {order_id}: {error}"
            ) from error
        return tracking

    async def get_next_delivery(self) -> NextDelivery | None:
        """Get the soonest upcoming order with its tracking and resolved ETA.

        Makes two requests (upcoming orders, then tracking for the soonest one)
        and combines them with :meth:`NextDelivery.resolve`. Consumers that
        already hold the upcoming list and tracking can call ``resolve``
        directly.

        Unlike most read methods this raises on a failed request, so that a
        failure is never mistaken for "no upcoming order" or "no tracking".

        The shop removes an order from the upcoming list as soon as it is
        delivered, so this rarely reports ``DELIVERED``; poll
        :meth:`get_delivery_tracking` with the order ID to observe the final
        state.

        Returns:
            NextDelivery: The soonest order with its ETA, or None if there is no
            upcoming order.

        Raises:
            APIRequestFailedError: If the upcoming orders or the tracking
                request fails, or the shop returns tracking for another order.
        """
        orders = await self.get_upcoming()
        if orders is None:
            raise APIRequestFailedError("Cannot fetch upcoming orders")
        if not orders:
            return None
        order = orders[0]
        tracking = await self.get_delivery_tracking(order.id, raise_on_error=True)
        try:
            return NextDelivery.resolve(order, tracking)
        except ValueError as err:
            raise APIRequestFailedError(f"Inconsistent delivery tracking: {err}") from err

    async def get_items(self, order_id: int) -> list[OrderItem] | None:
        """Get the line items of a single order.

        Works for upcoming and delivered orders alike. It is built on
        :meth:`get_detail` (``/api/v3/orders/{order_id}``), so it costs one
        request.

        Args:
            order_id: The ID of the order (``id`` of an entry from
                :meth:`get_next` or :meth:`get_delivered`).

        Returns:
            The order's items (empty if the order has none), or None if the
            order does not exist or the request fails.
        """
        detail = await self.get_detail(order_id)
        if detail is None:
            return None
        items = detail.get("items") or []
        return [OrderItem.from_api(item, self._cdn_url) for item in items if isinstance(item, dict)]
