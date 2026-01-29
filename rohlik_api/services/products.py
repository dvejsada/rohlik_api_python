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
