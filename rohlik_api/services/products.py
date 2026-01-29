"""Products service for Rohlik.cz API."""

import logging
from typing import Dict, Any, List, Optional

import httpx

from .base import BaseService
from ..endpoints import Endpoints

_LOGGER = logging.getLogger(__name__)


class ProductService(BaseService):
    """Service for product-related operations."""

    async def search(
        self,
        product_name: str,
        limit: int = 10,
        favourite: bool = False
    ) -> Optional[Dict[str, Any]]:
        """Search for products by name.

        Args:
            product_name: The name or search term for the product
            limit: Number of products returned
            favourite: Whether only favourite items shall be returned

        Returns:
            dict: Search results with product details, or None if no products found
        """
        await self._ensure_logged_in()

        search_payload = {
            "search": product_name,
            "offset": 0,
            "limit": limit + 5,
            "companyId": 1,
            "filterData": {"filters": []},
            "canCorrect": True
        }

        try:
            response = await self._http.get(Endpoints.SEARCH, params=search_payload)
            response.raise_for_status()
            search_data = response.json()
            found_products: List[Dict] = search_data.get("data", {}).get("productList", [])

            # Remove sponsored content
            found_products = [
                p for p in found_products
                if not any(badge.get("slug") == "promoted" for badge in p.get("badge", []))
            ]

            # Keep only favourites if requested
            if favourite:
                found_products = [p for p in found_products if p.get("favourite", False)]

            # Keep only results up to the specified limit
            if len(found_products) > limit:
                found_products = found_products[:limit]

            if found_products:
                search_results = {"search_results": []}
                for product in found_products:
                    price_info = product.get("price", {})
                    search_results["search_results"].append({
                        "id": product.get("productId"),
                        "name": product.get("productName"),
                        "price": f"{price_info.get('full', '')} {price_info.get('currency', '')}",
                        "brand": product.get("brand"),
                        "amount": product.get("textualAmount")
                    })
                return search_results
            else:
                return None

        except httpx.HTTPError as err:
            _LOGGER.error(f"Request failed: {err}")
            return None

    async def get_ai_summary(self, product_id: int) -> Optional[Dict[str, Any]]:
        """Get AI-generated summary for a product.

        Args:
            product_id: The ID of the product

        Returns:
            dict: AI summary with title and content, or None if request fails
        """
        await self._ensure_logged_in()

        try:
            url = Endpoints.product_ai_summary(product_id)
            response = await self._http.get(url)
            response.raise_for_status()
            data = response.json()

            return {
                "product_id": data.get("productId"),
                "rating": data.get("rating"),
                "title": data.get("title"),
                "content": data.get("content"),
            }

        except httpx.HTTPError as err:
            _LOGGER.error(f"Error fetching AI summary for product {product_id}: {err}")
            return None

    async def get_composition(self, product_id: int) -> Optional[Dict[str, Any]]:
        """Get composition and nutritional values for a product.

        Args:
            product_id: The ID of the product

        Returns:
            dict: Product composition including nutritional values, ingredients, and allergens
        """
        await self._ensure_logged_in()

        try:
            url = Endpoints.product_composition(product_id)
            response = await self._http.get(url)
            response.raise_for_status()
            data = response.json()

            # Parse nutritional values
            nutritional_values = []
            for nv in data.get("nutritionalValues", []):
                values = nv.get("values", {})
                nutritional_values.append({
                    "portion": nv.get("portion"),
                    "energy_kj": values.get("energyKJ", {}).get("amount"),
                    "energy_kcal": values.get("energyKCal", {}).get("amount"),
                    "fats": values.get("fats", {}).get("amount"),
                    "saturated_fats": values.get("saturatedFats", {}).get("amount"),
                    "carbohydrates": values.get("carbohydrates", {}).get("amount"),
                    "sugars": values.get("sugars", {}).get("amount"),
                    "protein": values.get("protein", {}).get("amount"),
                    "salt": values.get("salt", {}).get("amount"),
                    "fiber": values.get("fiber", {}).get("amount"),
                })

            # Parse allergens
            allergens_data = data.get("allergens", {})

            return {
                "product_id": data.get("productId"),
                "nutritional_values": nutritional_values,
                "ingredients": data.get("plainIngredients"),
                "allergens": {
                    "contained": allergens_data.get("contained", []),
                    "possibly_contained": allergens_data.get("possiblyContained", []),
                },
            }

        except httpx.HTTPError as err:
            _LOGGER.error(f"Error fetching composition for product {product_id}: {err}")
            return None

    async def get_price(self, product_id: int) -> Optional[Dict[str, Any]]:
        """Get current price for a product.

        Args:
            product_id: The ID of the product

        Returns:
            dict: Product price information including price per unit and sales
        """
        await self._ensure_logged_in()

        try:
            url = Endpoints.product_price(product_id)
            response = await self._http.get(url)
            response.raise_for_status()
            data = response.json()

            price = data.get("price", {})
            price_per_unit = data.get("pricePerUnit", {})

            return {
                "product_id": data.get("productId"),
                "price": price.get("amount"),
                "currency": price.get("currency"),
                "price_per_unit": price_per_unit.get("amount"),
                "sales": data.get("sales", []),
            }

        except httpx.HTTPError as err:
            _LOGGER.error(f"Error fetching price for product {product_id}: {err}")
            return None

