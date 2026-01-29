"""Cart service for Rohlik.cz API."""

import logging
from typing import Dict, Any, List

import httpx

from .base import BaseService
from ..endpoints import Endpoints
from ..errors import APIRequestFailedError

_LOGGER = logging.getLogger(__name__)


class CartService(BaseService):
    """Service for shopping cart operations."""

    async def get_content(self) -> Dict[str, Any]:
        """Fetch the current cart contents.

        Returns:
            dict: Dictionary with cart content including total_price, total_items,
                  can_make_order, and products list

        Raises:
            APIRequestFailedError: If the request fails
        """
        await self._ensure_logged_in()

        try:
            response = await self._http.get(Endpoints.CART)
            response.raise_for_status()
            cart_content = response.json()

            data = cart_content.get("data", {})

            cart_info: Dict[str, Any] = {
                "total_price": data.get("totalPrice", 0),
                "total_items": len(data.get("items", {})),
                "can_make_order": data.get("submitConditionPassed", False),
                "products": []
            }

            for product_id, product_data in data.get("items", {}).items():
                product_info = {
                    "id": product_id,
                    "cart_item_id": product_data.get("orderFieldId", ""),
                    "name": product_data.get("productName", ""),
                    "quantity": product_data.get("quantity", 0),
                    "price": product_data.get("price", 0),
                    "category_name": product_data.get("primaryCategoryName", ""),
                    "brand": product_data.get("brand", "")
                }
                cart_info["products"].append(product_info)

            return cart_info

        except httpx.HTTPError as err:
            _LOGGER.error(f"Request failed: {err}")
            raise APIRequestFailedError(f"Failed to fetch cart: {err}")

    async def add_items(self, product_list: List[Dict[str, Any]]) -> Dict[str, List[int]]:
        """Add multiple products to the shopping cart.

        Args:
            product_list: A list of dictionaries containing product_id and quantity

        Returns:
            dict: A dictionary with 'added_products' key containing list of product IDs
                  that were successfully added

        Raises:
            APIRequestFailedError: If the request fails
        """
        await self._ensure_logged_in()

        added_products: List[int] = []

        for product in product_list:
            cart_payload = {
                "actionId": None,
                "productId": int(product["product_id"]),
                "quantity": int(product["quantity"]),
                "recipeId": None,
                "source": "true:Shopping Lists"
            }
            try:
                response = await self._http.post(Endpoints.CART, json=cart_payload)
                response.raise_for_status()
                added_products.append(product["product_id"])
            except httpx.HTTPError as err:
                _LOGGER.error(f"Error adding {product['product_id']} due to {err}")

        return {"added_products": added_products}

    async def delete_item(self, order_field_id: str) -> Dict[str, Any]:
        """Delete an item from the shopping cart using orderFieldId.

        Args:
            order_field_id: The orderFieldId of the item to delete

        Returns:
            dict: Response from the deletion operation

        Raises:
            APIRequestFailedError: If the deletion fails
        """
        await self._ensure_logged_in()

        try:
            response = await self._http.delete(
                Endpoints.CART,
                params={"orderFieldId": order_field_id}
            )
            response.raise_for_status()

            try:
                return response.json()
            except Exception:
                return {"success": True, "status_code": response.status_code}

        except httpx.HTTPError as err:
            _LOGGER.error(f"Error deleting item with orderFieldId {order_field_id}: {err}")
            raise APIRequestFailedError(f"Failed to delete item from cart: {err}")
