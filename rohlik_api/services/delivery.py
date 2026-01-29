"""Delivery service for Rohlik.cz API."""

import logging
from typing import Dict, Any, Optional

from .base import BaseService
from ..endpoints import Endpoints

_LOGGER = logging.getLogger(__name__)


class DeliveryService(BaseService):
    """Service for delivery-related operations."""

    async def get_info(self) -> Optional[Dict[str, Any]]:
        """Get first delivery information.

        Returns:
            dict: Delivery information or None if request fails
        """
        return await self._fetch_endpoint(Endpoints.DELIVERY, "delivery info")

    async def get_timeslot_reservation(self) -> Optional[Dict[str, Any]]:
        """Get current timeslot reservation.

        Returns:
            dict: Timeslot reservation information or None if request fails
        """
        return await self._fetch_endpoint(
            Endpoints.TIMESLOT_RESERVATION,
            "timeslot reservation"
        )

    async def get_next_slots(
        self,
        user_id: Optional[int] = None,
        address_id: Optional[int] = None
    ) -> Optional[Dict[str, Any]]:
        """Get next available delivery slots.

        Args:
            user_id: User ID (uses auth manager's user_id if not provided)
            address_id: Address ID (uses auth manager's address_id if not provided)

        Returns:
            dict: Available delivery slots or None if request fails
        """
        await self._ensure_logged_in()

        uid = user_id or self._auth.user_id
        aid = address_id or self._auth.address_id

        if not uid or not aid:
            _LOGGER.error("User ID or Address ID not available for timeslots request")
            return None

        url = Endpoints.timeslots(user_id=uid, address_id=aid)
        return await self._fetch_endpoint(url, "next delivery slots")

    async def get_announcements(self) -> Optional[Dict[str, Any]]:
        """Get delivery announcements.

        Returns:
            dict: Delivery announcements or None if request fails
        """
        return await self._fetch_endpoint(
            Endpoints.DELIVERY_ANNOUNCEMENTS,
            "delivery announcements"
        )
