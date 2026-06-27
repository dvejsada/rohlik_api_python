"""Products service for Rohlik.cz API."""

from __future__ import annotations

import logging

from ..endpoints import Endpoints
from ..http_client import HTTP_ERRORS
from ..models import AISummary, ProductComposition, ProductPrice, ProductSearchResult, SearchResults
from .base import BaseService

_LOGGER = logging.getLogger(__name__)


class ProductService(BaseService):
    """Service for product-related operations."""

    async def search(
        self,
        product_name: str,
        limit: int = 10,
        favourite: bool = False,
    ) -> SearchResults | None:
        """Search for products by name.

        Args:
            product_name: The name or search term for the product.
            limit: Maximum number of products returned.
            favourite: Whether only favourite items should be returned.

        Returns:
            SearchResults with the matching products (possibly empty), or None
            if the request fails.
        """
        await self._ensure_logged_in()

        search_payload = {
            "search": product_name,
            "offset": 0,
            "limit": limit + 5,
            "companyId": 1,
            "filterData": {"filters": []},
            "canCorrect": True,
        }

        try:
            response = await self._http.get(Endpoints.SEARCH, params=search_payload)
            response.raise_for_status()
            found_products = response.json().get("data", {}).get("productList", [])
        except HTTP_ERRORS as err:
            _LOGGER.warning("Request failed: %s", err)
            return None

        # Remove sponsored content
        found_products = [
            p
            for p in found_products
            if not any(badge.get("slug") == "promoted" for badge in p.get("badge", []))
        ]

        # Keep only favourites if requested
        if favourite:
            found_products = [p for p in found_products if p.get("favourite", False)]

        # Keep only results up to the specified limit
        found_products = found_products[:limit]

        return SearchResults(
            results=[ProductSearchResult.from_api(product) for product in found_products]
        )

    async def get_ai_summary(self, product_id: int) -> AISummary | None:
        """Get the AI-generated summary for a product.

        Args:
            product_id: The ID of the product.

        Returns:
            An AISummary, or None if the request fails.
        """
        await self._ensure_logged_in()

        try:
            response = await self._http.get(Endpoints.product_ai_summary(product_id))
            response.raise_for_status()
            return AISummary.from_api(response.json())
        except HTTP_ERRORS as err:
            _LOGGER.warning("Error fetching AI summary for product %s: %s", product_id, err)
            return None

    async def get_composition(self, product_id: int) -> ProductComposition | None:
        """Get composition and nutritional values for a product.

        Args:
            product_id: The ID of the product.

        Returns:
            A ProductComposition, or None if the request fails.
        """
        await self._ensure_logged_in()

        try:
            response = await self._http.get(Endpoints.product_composition(product_id))
            response.raise_for_status()
            return ProductComposition.from_api(response.json())
        except HTTP_ERRORS as err:
            _LOGGER.warning("Error fetching composition for product %s: %s", product_id, err)
            return None

    async def get_price(self, product_id: int) -> ProductPrice | None:
        """Get the current price for a product.

        Args:
            product_id: The ID of the product.

        Returns:
            A ProductPrice, or None if the request fails.
        """
        await self._ensure_logged_in()

        try:
            response = await self._http.get(Endpoints.product_price(product_id))
            response.raise_for_status()
            return ProductPrice.from_api(response.json())
        except HTTP_ERRORS as err:
            _LOGGER.warning("Error fetching price for product %s: %s", product_id, err)
            return None
