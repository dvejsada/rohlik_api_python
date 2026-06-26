"""Recipe service for Rohlik.cz API."""

from __future__ import annotations

import logging
from typing import Any

import httpx

from ..endpoints import Endpoints
from ..helpers import format_price
from .base import BaseService

_LOGGER = logging.getLogger(__name__)


class RecipeService(BaseService):
    """Service for recipe and ingredient operations (Rohlík Chef)."""

    async def search(self, query: str, limit: int = 10, offset: int = 0) -> dict[str, Any] | None:
        """Search for recipes by name.

        Args:
            query: Search term for recipes
            limit: Maximum number of results to return
            offset: Offset for pagination

        Returns:
            dict: Search results with recipes list and total hits, or None if request fails
        """
        await self._ensure_logged_in()

        try:
            url = Endpoints.recipe_search(query, limit=limit, offset=offset)
            response = await self._http.get(url)
            response.raise_for_status()
            data = response.json()

            meals = data.get("data", {}).get("meals", [])
            total_hits = data.get("data", {}).get("totalHits", 0)

            return {
                "recipes": [
                    {
                        "id": meal.get("id"),
                        "name": meal.get("name"),
                        "link": meal.get("link"),
                        "image": meal.get("image"),
                        "is_favorite": meal.get("isFavorite", False),
                        "is_new": meal.get("isNew", False),
                        "is_best_seller": meal.get("isBestSeller", False),
                    }
                    for meal in meals
                ],
                "total_hits": total_hits,
            }

        except httpx.HTTPError as err:
            _LOGGER.error(f"Error searching recipes: {err}")
            return None

    async def get_detail(self, recipe_id: int) -> dict[str, Any] | None:
        """Get detailed information about a recipe.

        Args:
            recipe_id: The ID of the recipe

        Returns:
            dict: Recipe details including ingredients and directions, or None if request fails
        """
        await self._ensure_logged_in()

        try:
            url = Endpoints.recipe_detail(recipe_id)
            response = await self._http.get(url)
            response.raise_for_status()
            data = response.json().get("data", {})

            # Parse ingredients
            ingredients = []
            for group in data.get("ingredients", []):
                ingredient_group = {
                    "name": group.get("name"),
                    "position": group.get("position"),
                    "items": [
                        {
                            "name": item.get("name"),
                            "ingredient_id": item.get("ingredientId"),
                            "ingredient_name": item.get("ingredientName"),
                            "products_count": item.get("productsCount"),
                            "image": item.get("imgPath"),
                        }
                        for item in group.get("items", [])
                    ],
                }
                ingredients.append(ingredient_group)

            # Parse directions
            directions = []
            for section in data.get("directions", []):
                direction_section = {
                    "name": section.get("name"),
                    "position": section.get("position"),
                    "steps": [
                        {
                            "step_number": step.get("stepNumber"),
                            "content": step.get("content"),
                        }
                        for step in section.get("steps", [])
                    ],
                }
                directions.append(direction_section)

            return {
                "id": data.get("id"),
                "name": data.get("name"),
                "duration": data.get("duration"),
                "servings": data.get("servings", []),
                "image": data.get("image", {}).get("path"),
                "author": {
                    "name": data.get("author", {}).get("name"),
                    "annotation": data.get("author", {}).get("annotation"),
                },
                "tips": [tip.get("content") for tip in data.get("tips", [])],
                "ingredients": ingredients,
                "directions": directions,
                "is_favorite": data.get("isFavorite", False),
                "link": data.get("link"),
            }

        except httpx.HTTPError as err:
            _LOGGER.error(f"Error fetching recipe detail: {err}")
            return None

    async def get_ingredient_products(
        self, ingredient_ids: list[int], limit: int = 5, offset: int = 0
    ) -> dict[str, Any] | None:
        """Get products for specific ingredients.

        Args:
            ingredient_ids: List of ingredient IDs to fetch products for
            limit: Maximum number of products per ingredient
            offset: Offset for pagination

        Returns:
            dict: Ingredients with their available products, or None if request fails
        """
        await self._ensure_logged_in()

        payload = {"ingredientIds": ingredient_ids, "offset": offset, "limit": limit}

        try:
            response = await self._http.post(Endpoints.INGREDIENT_PRODUCTS, json=payload)
            response.raise_for_status()
            data = response.json().get("data", {})

            ingredients_data = []
            for ingredient in data.get("ingredients", []):
                products = []
                for product in ingredient.get("products", []):
                    price_info = product.get("price", {})
                    products.append(
                        {
                            "product_id": product.get("productId"),
                            "name": product.get("productName"),
                            "image": product.get("imgPath"),
                            "price": format_price(price_info),
                            "price_value": price_info.get("full"),
                            "unit": product.get("unit"),
                            "amount": product.get("textualAmount"),
                            "in_stock": product.get("inStock", False),
                            "is_favorite": product.get("favourite", False),
                        }
                    )

                ingredients_data.append(
                    {
                        "ingredient_id": ingredient.get("id"),
                        "products": products,
                        "total_hits": ingredient.get("totalHits", 0),
                    }
                )

            return {"ingredients": ingredients_data}

        except httpx.HTTPError as err:
            _LOGGER.error(f"Error fetching ingredient products: {err}")
            return None
