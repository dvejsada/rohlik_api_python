"""Cart service for Rohlik.cz API."""

from __future__ import annotations

import logging
from typing import Any

import httpx

from ..endpoints import Endpoints
from ..errors import APIRequestFailedError
from ..models import Cart
from .base import BaseService

_LOGGER = logging.getLogger(__name__)


class CartService(BaseService):
    """Service for shopping cart operations."""

    async def get_content(self) -> Cart:
        """Fetch the current cart contents.

        Returns:
            Cart: The current cart with its products.

        Raises:
            APIRequestFailedError: If the request fails.
        """
        await self._ensure_logged_in()

        try:
            response = await self._http.get(Endpoints.CART)
            response.raise_for_status()
            return Cart.from_api(response.json())
        except httpx.HTTPError as err:
            _LOGGER.error("Request failed: %s", err)
            raise APIRequestFailedError(f"Failed to fetch cart: {err}") from err

    async def add_items(self, product_list: list[dict[str, Any]]) -> list[int]:
        """Add multiple products to the shopping cart.

        Args:
            product_list: A list of dictionaries containing ``product_id`` and
                ``quantity``.

        Returns:
            The list of product IDs that were successfully added.
        """
        await self._ensure_logged_in()

        added_products: list[int] = []

        for product in product_list:
            product_id = int(product["product_id"])
            cart_payload = {
                "actionId": None,
                "productId": product_id,
                "quantity": int(product["quantity"]),
                "recipeId": None,
                "source": "true:Shopping Lists",
            }
            try:
                response = await self._http.post(Endpoints.CART, json=cart_payload)
                response.raise_for_status()
                added_products.append(product_id)
            except httpx.HTTPError as err:
                _LOGGER.warning("Error adding %s due to %s", product_id, err)

        return added_products

    async def delete_item(self, order_field_id: str) -> None:
        """Delete an item from the shopping cart using its ``orderFieldId``.

        Args:
            order_field_id: The ``orderFieldId`` (``cart_item_id``) of the item
                to delete.

        Raises:
            APIRequestFailedError: If the deletion fails.
        """
        await self._ensure_logged_in()

        try:
            response = await self._http.delete(
                Endpoints.CART, params={"orderFieldId": order_field_id}
            )
            response.raise_for_status()
        except httpx.HTTPError as err:
            _LOGGER.error("Error deleting item with orderFieldId %s: %s", order_field_id, err)
            raise APIRequestFailedError(f"Failed to delete item from cart: {err}") from err
