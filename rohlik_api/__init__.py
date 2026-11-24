"""Rohlik.cz API Python Client.

An async Python client for the Rohlik.cz API, built on aiohttp. The same API
serves the other Rohlík Group shops (Knuspr.de, Gurkerl.at, Kifli.hu,
Sezamo.ro); see :data:`SITES`.
"""

from .auth import AuthManager
from .client import RohlikAPI
from .endpoints import BASE_URL, Endpoints
from .errors import APIRequestFailedError, InvalidCredentialsError, RohlikAPIError
from .helpers import format_price, mask_data, parse_datetime
from .http_client import HttpClient
from .models import (
    AISummary,
    Allergens,
    Cart,
    CartItem,
    CourierPosition,
    DeliveryDestination,
    DeliveryEtaSource,
    DeliveryProgress,
    DeliveryTracking,
    DirectionSection,
    DirectionStep,
    GeoPoint,
    IngredientGroup,
    IngredientItem,
    IngredientProduct,
    IngredientProductGroup,
    IngredientProducts,
    NextDelivery,
    NutritionalValue,
    ProductCard,
    ProductComposition,
    ProductPrice,
    ProductSearchResult,
    RecipeAuthor,
    RecipeDetail,
    RecipeSearchResults,
    RecipeSummary,
    SearchResults,
    ShoppingList,
    TrackingStatus,
    UpcomingOrder,
)
from .sites import SITES, Site

__version__ = "0.5.0"
__all__ = [
    # Main client (facade)
    "RohlikAPI",
    # Shops
    "Site",
    "SITES",
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
    "ProductCard",
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
    "UpcomingOrder",
    "DeliveryTracking",
    "DeliveryProgress",
    "CourierPosition",
    "DeliveryDestination",
    "GeoPoint",
    "NextDelivery",
    "TrackingStatus",
    "DeliveryEtaSource",
    # Utilities
    "mask_data",
    "format_price",
    "parse_datetime",
    # Advanced: low-level components
    "HttpClient",
    "AuthManager",
    "Endpoints",
    "BASE_URL",
]
