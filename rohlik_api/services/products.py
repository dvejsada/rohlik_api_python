"""Products service for Rohlik.cz API."""

from __future__ import annotations

import logging
from typing import Any

from ..endpoints import Endpoints
from ..http_client import HTTP_ERRORS
from ..models import (
    AISummary,
    ProductCard,
    ProductComposition,
    ProductPrice,
    ProductSearchResult,
    SearchResults,
)
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

    async def get_cards(
        self, product_ids: list[int], category_type: str = "normal"
    ) -> list[ProductCard] | None:
        """Get basic product cards for several products in a single request.

        Args:
            product_ids: The product IDs to look up.
            category_type: The ``categoryType`` query parameter (default "normal").

        Returns:
            A list of :class:`ProductCard` in the same order as ``product_ids``
            (IDs the API did not return are skipped), an empty list if
            ``product_ids`` is empty, or None if the request fails.
        """
        await self._ensure_logged_in()

        if not product_ids:
            return []

        try:
            url = Endpoints.product_cards(product_ids, category_type=category_type)
            response = await self._http.get(url)
            response.raise_for_status()
            payload = response.json()
        except HTTP_ERRORS as err:
            _LOGGER.warning("Error fetching product cards: %s", err)
            return None

        if not isinstance(payload, list):
            return None

        by_id = {card.id: card for card in (ProductCard.from_api(item) for item in payload)}
        return [by_id[pid] for pid in product_ids if pid in by_id]

    async def get_week_sales(
        self, page: int = 0, size: int = 30, sort: str = "recommended"
    ) -> list[ProductCard] | None:
        """Get this week's deals ("Akce týdne"), enriched with basic product data.

        The deals endpoint returns only product IDs; these are enriched via the
        bulk product-card endpoint in a single follow-up request.

        Args:
            page: Result page (default 0).
            size: Maximum number of products (default 30).
            sort: Sort order (default "recommended").

        Returns:
            A list of :class:`ProductCard` for the products on sale, an empty
            list if there are none, or None if the request fails.
        """
        await self._ensure_logged_in()

        try:
            url = Endpoints.week_sales(page=page, size=size, sort=sort)
            response = await self._http.get(url)
            response.raise_for_status()
            payload = response.json()
        except HTTP_ERRORS as err:
            _LOGGER.warning("Error fetching week sales: %s", err)
            return None

        data = payload.get("data", payload) if isinstance(payload, dict) else {}
        product_ids = data.get("products") if isinstance(data, dict) else None
        if not isinstance(product_ids, list) or not product_ids:
            return []

        return await self.get_cards(product_ids)

    async def get_detail(self, product_id: int) -> dict[str, Any] | None:
        """Get the full product detail (brand, attributes, etc.).

        Args:
            product_id: The ID of the product.

        Returns:
            dict: The raw product detail, or None if the product does not exist
            (404) or the request fails.
        """
        await self._ensure_logged_in()

        try:
            response = await self._http.get(Endpoints.product_detail(product_id))
            if response.status == 404:
                return None
            response.raise_for_status()
            detail: dict[str, Any] = response.json()
            return detail
        except HTTP_ERRORS as err:
            _LOGGER.warning("Error fetching detail for product %s: %s", product_id, err)
            return None

    async def get_categories(self, product_id: int) -> list[dict[str, Any]] | None:
        """Get the category hierarchy for a product.

        Args:
            product_id: The ID of the product.

        Returns:
            list: The category hierarchy (possibly empty), or None if the
            product no longer exists (404) or the request fails. A 404 typically
            means the product has been discontinued.
        """
        await self._ensure_logged_in()

        try:
            response = await self._http.get(Endpoints.product_categories(product_id))
            if response.status == 404:
                _LOGGER.debug("Product %s not found (discontinued)", product_id)
                return None
            response.raise_for_status()
            categories: list[dict[str, Any]] = response.json().get("categories", [])
            return categories
        except HTTP_ERRORS as err:
            _LOGGER.warning("Error fetching categories for product %s: %s", product_id, err)
            return None
