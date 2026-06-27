"""Rohlik.cz API Python Client.

An async Python client for the Rohlik.cz API, built on httpx with HTTP/2 support.
"""

from .auth import AuthManager
from .client import RohlikAPI
from .endpoints import BASE_URL, Endpoints
from .errors import APIRequestFailedError, InvalidCredentialsError, RohlikAPIError
from .helpers import format_price, mask_data
from .http_client import HttpClient
from .models import (
    AISummary,
    Allergens,
    Cart,
    CartItem,
    DirectionSection,
    DirectionStep,
    IngredientGroup,
    IngredientItem,
    IngredientProduct,
    IngredientProductGroup,
    IngredientProducts,
    NutritionalValue,
    ProductComposition,
    ProductPrice,
    ProductSearchResult,
    RecipeAuthor,
    RecipeDetail,
    RecipeSearchResults,
    RecipeSummary,
    SearchResults,
    ShoppingList,
)

__version__ = "0.1.0"
__all__ = [
    # Main client (facade)
    "RohlikAPI",
    # Errors
    "RohlikAPIError",
    "InvalidCredentialsError",
    "APIRequestFailedError",
    # Models
    "Cart",
    "CartItem",
    "SearchResults",
    "ProductSearchResult",
    "AISummary",
    "ProductComposition",
    "NutritionalValue",
    "Allergens",
    "ProductPrice",
    "RecipeSearchResults",
    "RecipeSummary",
    "RecipeDetail",
    "RecipeAuthor",
    "IngredientGroup",
    "IngredientItem",
    "DirectionSection",
    "DirectionStep",
    "IngredientProducts",
    "IngredientProductGroup",
    "IngredientProduct",
    "ShoppingList",
    # Utilities
    "mask_data",
    "format_price",
    # Advanced: low-level components
    "HttpClient",
    "AuthManager",
    "Endpoints",
    "BASE_URL",
]
