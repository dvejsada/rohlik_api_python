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

    async def get_next_slots(
        self, user_id: int | None = None, address_id: int | None = None
    ) -> dict[str, Any] | None:
        """Get next available delivery slots.

        Args:
            user_id: User ID (uses auth manager's user_id if not provided)
            address_id: Address ID (uses auth manager's address_id if not provided)

        Returns:
            dict: Available delivery slots or None if request fails
        """
        # Log in first (also done by _fetch_endpoint below) so that the auth
        # manager's user_id/address_id are populated before we build the URL.
        await self._ensure_logged_in()

        uid = user_id or self._auth.user_id
        aid = address_id or self._auth.address_id

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
