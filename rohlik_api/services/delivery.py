"""Delivery service for Rohlik.cz API."""

from __future__ import annotations

import logging
from typing import Any

from ..endpoints import Endpoints
from .base import BaseService

_LOGGER = logging.getLogger(__name__)


class DeliveryService(BaseService):
    """Service for delivery-related operations."""

    async def get_info(self) -> dict[str, Any] | None:
        """Get first delivery information.

        Returns:
            dict: Delivery information or None if request fails
        """
        return await self._fetch_endpoint(Endpoints.DELIVERY, "delivery info")

    async def get_timeslot_reservation(self) -> dict[str, Any] | None:
        """Get current timeslot reservation.

        Returns:
            dict: Timeslot reservation information or None if request fails
        """
        return await self._fetch_endpoint(Endpoints.TIMESLOT_RESERVATION, "timeslot reservation")

    async def get_addresses(self) -> dict[str, Any] | None:
        """Get the account's saved delivery addresses.

        Returns:
            dict: The ``{status, messages, data}`` envelope whose ``data`` is a
            list of saved addresses, or None if the request fails.
        """
        return await self._fetch_endpoint(Endpoints.DELIVERY_ADDRESS_LIST, "delivery addresses")

    async def get_active_address_id(self) -> int | None:
        """Resolve the delivery address ID to use for timeslot lookups.

        The login response does not always include an address, so fall back to
        the saved delivery-address list. Prefers the first address the account
        is currently delivered to (``isDeliveredTo``), otherwise the first one.

        Returns:
            int: The resolved address ID, or None if none could be found.
        """
        response = await self.get_addresses()
        addresses = response.get("data") if isinstance(response, dict) else None
        if not isinstance(addresses, list) or not addresses:
            return None

        def address_id_of(entry: Any) -> int | None:
            return ((entry or {}).get("address") or {}).get("id")

        for entry in addresses:
            if ((entry or {}).get("address") or {}).get("isDeliveredTo"):
                chosen = address_id_of(entry)
                if chosen is not None:
                    return chosen
        return address_id_of(addresses[0])

    async def get_next_slots(
        self, user_id: int | None = None, address_id: int | None = None
    ) -> dict[str, Any] | None:
        """Get next available delivery slots.

        Args:
            user_id: User ID (uses auth manager's user_id if not provided)
            address_id: Address ID (uses auth manager's address_id if not provided;
                falls back to the saved delivery-address list when unknown)

        Returns:
            dict: Available delivery slots or None if request fails
        """
        # Log in first (also done by _fetch_endpoint below) so that the auth
        # manager's user_id/address_id are populated before we build the URL.
        await self._ensure_logged_in()

        uid = user_id or self._auth.user_id
        aid = address_id or self._auth.address_id

        if not aid:
            # The login response did not carry an address; resolve it from the
            # saved address list and cache it for subsequent calls.
            aid = await self.get_active_address_id()
            if aid is not None:
                self._auth.address_id = aid

        if not uid or not aid:
            _LOGGER.warning("User ID or Address ID not available for timeslots request")
            return None

        url = Endpoints.timeslots(user_id=uid, address_id=aid)
        return await self._fetch_endpoint(url, "next delivery slots")

    async def get_announcements(self) -> dict[str, Any] | None:
        """Get delivery announcements.

        Returns:
            dict: Delivery announcements or None if request fails
        """
        return await self._fetch_endpoint(
            Endpoints.DELIVERY_ANNOUNCEMENTS, "delivery announcements"
        )
