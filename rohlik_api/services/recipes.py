"""Recipe service for Rohlik.cz API."""

from __future__ import annotations

import logging

import httpx

from ..endpoints import Endpoints
from ..models import IngredientProducts, RecipeDetail, RecipeSearchResults
from .base import BaseService

_LOGGER = logging.getLogger(__name__)


class RecipeService(BaseService):
    """Service for recipe and ingredient operations (Rohlík Chef)."""

    async def search(
        self, query: str, limit: int = 10, offset: int = 0
    ) -> RecipeSearchResults | None:
        """Search for recipes by name.

        Args:
            query: Search term for recipes.
            limit: Maximum number of results to return.
            offset: Offset for pagination.

        Returns:
            RecipeSearchResults with the matching recipes, or None if the
            request fails.
        """
        await self._ensure_logged_in()

        try:
            url = Endpoints.recipe_search(query, limit=limit, offset=offset)
            response = await self._http.get(url)
            response.raise_for_status()
            return RecipeSearchResults.from_api(response.json())
        except httpx.HTTPError as err:
            _LOGGER.error("Error searching recipes: %s", err)
            return None

    async def get_detail(self, recipe_id: int) -> RecipeDetail | None:
        """Get detailed information about a recipe.

        Args:
            recipe_id: The ID of the recipe.

        Returns:
            A RecipeDetail with ingredients and directions, or None if the
            request fails.
        """
        await self._ensure_logged_in()

        try:
            response = await self._http.get(Endpoints.recipe_detail(recipe_id))
            response.raise_for_status()
            return RecipeDetail.from_api(response.json())
        except httpx.HTTPError as err:
            _LOGGER.error("Error fetching recipe detail: %s", err)
            return None

    async def get_ingredient_products(
        self, ingredient_ids: list[int], limit: int = 5, offset: int = 0
    ) -> IngredientProducts | None:
        """Get purchasable products for specific ingredients.

        Args:
            ingredient_ids: List of ingredient IDs to fetch products for.
            limit: Maximum number of products per ingredient.
            offset: Offset for pagination.

        Returns:
            IngredientProducts with the available products per ingredient, or
            None if the request fails.
        """
        await self._ensure_logged_in()

        payload = {"ingredientIds": ingredient_ids, "offset": offset, "limit": limit}

        try:
            response = await self._http.post(Endpoints.INGREDIENT_PRODUCTS, json=payload)
            response.raise_for_status()
            return IngredientProducts.from_api(response.json())
        except httpx.HTTPError as err:
            _LOGGER.error("Error fetching ingredient products: %s", err)
            return None
