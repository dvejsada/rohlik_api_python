"""Typed data models for the Rohlik.cz API client.

Service methods return these dataclasses instead of raw dictionaries. Each model
provides a ``from_api`` classmethod that parses the relevant slice of a Rohlik
API response. All models are plain dataclasses, so ``dataclasses.asdict`` can be
used to convert them back to JSON-serialisable dictionaries (useful for the
Home Assistant integration and the MCP server).

Monetary amounts come in two shapes: ``price`` fields typed as ``str`` are
pre-formatted for display (for example ``"29.90 Kč"``), while numeric ``price``
fields are raw amounts in the shop's currency, paired with a separate ISO 4217
``currency`` code where the API provides one (``"CZK"`` on Rohlík.cz, ``"EUR"``
on Knuspr.de, see :data:`~rohlik_api.SITES`).
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from datetime import datetime
from enum import StrEnum
from typing import Any, Literal, Protocol

from .helpers import format_price, parse_datetime

# ---------------------------------------------------------------------------
# Cart
# ---------------------------------------------------------------------------


@dataclass(slots=True)
class CartItem:
    """A single item (line) in the shopping cart.

    Attributes:
        id: The product ID, as a string.
        cart_item_id: The cart-line identifier (``orderFieldId``). Pass this to
            :meth:`~rohlik_api.RohlikAPI.cart`'s ``delete_item`` to remove the
            line from the cart.
        name: Product name.
        quantity: Number of units of this product in the cart.
        price: Line price for this product, in :attr:`currency`.
        category_name: Primary category name of the product.
        brand: Brand name, or an empty string if unknown.
        currency: ISO 4217 currency code of :attr:`price`, e.g. ``"CZK"``, or an
            empty string if the API omits it.
    """

    id: str
    cart_item_id: str
    name: str
    quantity: int
    price: float
    category_name: str = ""
    brand: str = ""
    currency: str = ""

    @classmethod
    def from_api(cls, item_id: str, data: dict[str, Any]) -> CartItem:
        """Build a :class:`CartItem` from a cart ``items`` entry."""
        return cls(
            id=item_id,
            cart_item_id=data.get("orderFieldId", ""),
            name=data.get("productName", ""),
            quantity=data.get("quantity", 0),
            price=data.get("price", 0),
            category_name=data.get("primaryCategoryName", ""),
            brand=data.get("brand", ""),
            currency=data.get("currency", ""),
        )


@dataclass(slots=True)
class Cart:
    """The current shopping cart.

    Attributes:
        total_price: Total price of the cart, in :attr:`currency`.
        total_items: Number of distinct products in the cart (line count, not
            the summed quantity).
        can_make_order: Whether the cart passes all of the shop's submit
            conditions (``submitConditionPassed``). These include checkout
            details such as a chosen delivery slot, so this is not a
            minimum-order indicator; compare against
            :attr:`minimum_order_price` for that.
        products: The cart's line items.
        minimum_order_price: Smallest cart total the shop accepts for an
            order (``minimalOrderPrice``), in :attr:`currency`, or ``None`` if
            the API does not report one. Anonymous carts report ``0``.
        currency: ISO 4217 currency code of the cart's prices, taken from its
            items, or ``None`` when the cart is empty or no item reports one
            (the cart payload itself has no currency; see
            :data:`~rohlik_api.SITES` for each shop's).
    """

    total_price: float
    total_items: int
    can_make_order: bool
    products: list[CartItem] = field(default_factory=list)
    minimum_order_price: float | None = None
    currency: str | None = None

    @classmethod
    def from_api(cls, payload: dict[str, Any]) -> Cart:
        """Build a :class:`Cart` from a ``/v2/cart`` response."""
        data = payload.get("data", {})
        items: dict[str, Any] = data.get("items", {})
        products = [CartItem.from_api(pid, pdata) for pid, pdata in items.items()]
        return cls(
            total_price=data.get("totalPrice", 0),
            total_items=len(items),
            can_make_order=data.get("submitConditionPassed", False),
            products=products,
            minimum_order_price=data.get("minimalOrderPrice"),
            currency=next((p.currency for p in products if p.currency), None),
        )


# ---------------------------------------------------------------------------
# Products
# ---------------------------------------------------------------------------


@dataclass(slots=True)
class ProductSearchResult:
    """A single product entry from a search response.

    Attributes:
        id: Product ID. Use it with ``cart.add_items`` or the
            ``products.get_*`` lookups.
        name: Product name.
        price: Pre-formatted price string, e.g. ``"29.90 Kč"`` (empty if the
            API omitted price information).
        brand: Brand name, if known.
        amount: Textual packaging/amount, e.g. ``"500 g"``.
    """

    id: int | None
    name: str | None
    price: str
    brand: str | None = None
    amount: str | None = None

    @classmethod
    def from_api(cls, data: dict[str, Any]) -> ProductSearchResult:
        """Build a :class:`ProductSearchResult` from a product list entry."""
        return cls(
            id=data.get("productId"),
            name=data.get("productName"),
            price=format_price(data.get("price")),
            brand=data.get("brand"),
            amount=data.get("textualAmount"),
        )


@dataclass(slots=True)
class SearchResults:
    """Container for product search results.

    Attributes:
        results: The matched products, in ranked order. Empty if nothing
            matched the search term.
    """

    results: list[ProductSearchResult] = field(default_factory=list)


@dataclass(slots=True)
class AISummary:
    """AI-generated summary for a product.

    Attributes:
        product_id: The product the summary is for.
        rating: Rohlik's rating bucket for the summary (e.g. ``"EMPTY"``).
        title: Summary title (localised, e.g. ``"AI Souhrn"``).
        content: The summary text.
    """

    product_id: int | None
    rating: str | None
    title: str | None
    content: str | None

    @classmethod
    def from_api(cls, data: dict[str, Any]) -> AISummary:
        """Build an :class:`AISummary` from an ai-summary response."""
        return cls(
            product_id=data.get("productId"),
            rating=data.get("rating"),
            title=data.get("title"),
            content=data.get("content"),
        )


@dataclass(slots=True)
class NutritionalValue:
    """Nutritional values for a single portion.

    Every amount is expressed for the stated :attr:`portion`. Any value the API
    omits is ``None``.

    Attributes:
        portion: The reference portion these values describe, e.g. ``"100 g"``.
        energy_kj: Energy in kilojoules (kJ).
        energy_kcal: Energy in kilocalories (kcal).
        fats: Total fat, in grams.
        saturated_fats: Saturated fat, in grams.
        carbohydrates: Carbohydrates, in grams.
        sugars: Sugars, in grams.
        protein: Protein, in grams.
        salt: Salt, in grams.
        fiber: Fibre, in grams.
    """

    portion: str | None
    energy_kj: float | None
    energy_kcal: float | None
    fats: float | None
    saturated_fats: float | None
    carbohydrates: float | None
    sugars: float | None
    protein: float | None
    salt: float | None
    fiber: float | None

    @classmethod
    def from_api(cls, data: dict[str, Any]) -> NutritionalValue:
        """Build a :class:`NutritionalValue` from a nutritionalValues entry."""
        values = data.get("values", {})

        def amount(key: str) -> float | None:
            value: float | None = values.get(key, {}).get("amount")
            return value

        return cls(
            portion=data.get("portion"),
            energy_kj=amount("energyKJ"),
            energy_kcal=amount("energyKCal"),
            fats=amount("fats"),
            saturated_fats=amount("saturatedFats"),
            carbohydrates=amount("carbohydrates"),
            sugars=amount("sugars"),
            protein=amount("protein"),
            salt=amount("salt"),
            fiber=amount("fiber"),
        )


@dataclass(slots=True)
class Allergens:
    """Allergen information for a product.

    Attributes:
        contained: Allergens the product definitely contains.
        possibly_contained: Allergens that may be present (e.g. traces from
            shared production lines).
    """

    contained: list[str] = field(default_factory=list)
    possibly_contained: list[str] = field(default_factory=list)


@dataclass(slots=True)
class ProductComposition:
    """Composition and nutritional information for a product.

    Attributes:
        product_id: The product this composition is for.
        nutritional_values: Nutrition broken down by portion (one entry per
            portion size the API provides).
        ingredients: Plain-text ingredient list, if available.
        allergens: Allergen information.
    """

    product_id: int | None
    nutritional_values: list[NutritionalValue] = field(default_factory=list)
    ingredients: str | None = None
    allergens: Allergens = field(default_factory=Allergens)

    @classmethod
    def from_api(cls, data: dict[str, Any]) -> ProductComposition:
        """Build a :class:`ProductComposition` from a composition response."""
        allergens = data.get("allergens", {})
        return cls(
            product_id=data.get("productId"),
            nutritional_values=[
                NutritionalValue.from_api(nv) for nv in data.get("nutritionalValues", [])
            ],
            ingredients=data.get("plainIngredients"),
            allergens=Allergens(
                contained=allergens.get("contained", []),
                possibly_contained=allergens.get("possiblyContained", []),
            ),
        )


@dataclass(slots=True)
class ProductPrice:
    """Current price information for a product.

    Attributes:
        product_id: The product this price is for.
        price: Current price as a number, expressed in :attr:`currency`.
        currency: ISO currency code, e.g. ``"CZK"``.
        price_per_unit: Price per base unit (e.g. per kg or per litre), in
            :attr:`currency`.
        sales: Raw list of active sales/discounts, in the API's own shape.
    """

    product_id: int | None
    price: float | None
    currency: str | None
    price_per_unit: float | None
    sales: list[Any] = field(default_factory=list)

    @classmethod
    def from_api(cls, data: dict[str, Any]) -> ProductPrice:
        """Build a :class:`ProductPrice` from a prices response."""
        price = data.get("price", {})
        return cls(
            product_id=data.get("productId"),
            price=price.get("amount"),
            currency=price.get("currency"),
            price_per_unit=data.get("pricePerUnit", {}).get("amount"),
            sales=data.get("sales", []),
        )


@dataclass(slots=True)
class ProductCard:
    """Basic product information from the bulk product-card endpoint.

    A trimmed, meaningful subset of the website's product card — name, packaging
    and pricing (including any active sale) — with display-only fields dropped.

    Attributes:
        id: Product ID.
        name: Product name.
        brand: Brand name, if known.
        amount: Textual packaging/amount, e.g. ``"cca 420 g"``.
        unit: Base unit the product is sold by, e.g. ``"kg"`` or ``"ks"``.
        price: Current price (the sale price when on sale, otherwise the regular
            price), in :attr:`currency`.
        original_price: Regular price before any discount, in :attr:`currency`.
        unit_price: Price per base unit (e.g. per kg), in :attr:`currency`.
        currency: ISO currency code, e.g. ``"CZK"``.
        on_sale: True when the product currently has a sale price.
        sale_valid_till: ISO timestamp the sale is valid until, if on sale.
        in_stock: True when the product is available to order.
    """

    id: int | None
    name: str | None
    brand: str | None
    amount: str | None
    unit: str | None
    price: float | None
    original_price: float | None
    unit_price: float | None
    currency: str | None
    on_sale: bool = False
    sale_valid_till: str | None = None
    in_stock: bool = True

    @classmethod
    def from_api(cls, data: dict[str, Any]) -> ProductCard:
        """Build a :class:`ProductCard` from a product-card entry."""
        prices = data.get("prices") or {}
        sale_price = prices.get("salePrice")
        original_price = prices.get("originalPrice")
        on_sale = sale_price is not None
        stock = data.get("stock") or {}
        return cls(
            id=data.get("productId"),
            name=data.get("name"),
            brand=data.get("brand"),
            amount=data.get("textualAmount"),
            unit=data.get("unit"),
            price=sale_price if on_sale else original_price,
            original_price=original_price,
            unit_price=prices.get("unitPrice"),
            currency=prices.get("currency"),
            on_sale=on_sale,
            sale_valid_till=prices.get("saleValidTill"),
            # Default to in-stock when the status is absent, matching the field
            # default (in_stock=True) so hand-built and parsed cards agree.
            in_stock=stock.get("availabilityStatus", "AVAILABLE") == "AVAILABLE",
        )


# ---------------------------------------------------------------------------
# Recipes (Rohlík Chef)
# ---------------------------------------------------------------------------


@dataclass(slots=True)
class RecipeSummary:
    """A recipe entry from a recipe search response.

    Attributes:
        id: Recipe ID. Use it with ``recipes.get_detail``.
        name: Recipe name.
        link: Relative web path to the recipe on rohlik.cz.
        image: Relative path to the recipe image.
        is_favorite: Whether the recipe is marked as a favourite by the user.
        is_new: Whether the recipe is flagged as new.
        is_best_seller: Whether the recipe is flagged as a best seller.
    """

    id: int | None
    name: str | None
    link: str | None
    image: str | None
    is_favorite: bool = False
    is_new: bool = False
    is_best_seller: bool = False

    @classmethod
    def from_api(cls, data: dict[str, Any]) -> RecipeSummary:
        """Build a :class:`RecipeSummary` from a meals entry."""
        return cls(
            id=data.get("id"),
            name=data.get("name"),
            link=data.get("link"),
            image=data.get("image"),
            is_favorite=data.get("isFavorite", False),
            is_new=data.get("isNew", False),
            is_best_seller=data.get("isBestSeller", False),
        )


@dataclass(slots=True)
class RecipeSearchResults:
    """Container for recipe search results.

    Attributes:
        recipes: The matched recipes for this page of results.
        total_hits: Total number of matching recipes (may exceed
            ``len(recipes)`` because results are paginated).
    """

    recipes: list[RecipeSummary] = field(default_factory=list)
    total_hits: int = 0

    @classmethod
    def from_api(cls, payload: dict[str, Any]) -> RecipeSearchResults:
        """Build :class:`RecipeSearchResults` from a recipe search response."""
        data = payload.get("data", {})
        return cls(
            recipes=[RecipeSummary.from_api(meal) for meal in data.get("meals", [])],
            total_hits=data.get("totalHits", 0),
        )


@dataclass(slots=True)
class IngredientItem:
    """A single ingredient within a recipe ingredient group.

    Attributes:
        name: Ingredient display name.
        ingredient_id: Ingredient ID. Pass it to ``recipes.get_ingredient_products``
            to find purchasable products for this ingredient.
        ingredient_name: Textual amount and name, e.g. ``"2 větší mrkve"``.
        products_count: Number of purchasable products available for this
            ingredient.
        image: Relative path to the ingredient image.
    """

    name: str | None
    ingredient_id: int | None
    ingredient_name: str | None
    products_count: int | None
    image: str | None

    @classmethod
    def from_api(cls, data: dict[str, Any]) -> IngredientItem:
        """Build an :class:`IngredientItem` from an ingredient entry."""
        return cls(
            name=data.get("name"),
            ingredient_id=data.get("ingredientId"),
            ingredient_name=data.get("ingredientName"),
            products_count=data.get("productsCount"),
            image=data.get("imgPath"),
        )


@dataclass(slots=True)
class IngredientGroup:
    """A named group of recipe ingredients.

    Attributes:
        name: Group name, e.g. ``"HOVĚZÍ VÝVAR"``.
        position: Ordering index of the group within the recipe.
        items: The ingredients belonging to this group.
    """

    name: str | None
    position: int | None
    items: list[IngredientItem] = field(default_factory=list)

    @classmethod
    def from_api(cls, data: dict[str, Any]) -> IngredientGroup:
        """Build an :class:`IngredientGroup` from an ingredients entry."""
        return cls(
            name=data.get("name"),
            position=data.get("position"),
            items=[IngredientItem.from_api(item) for item in data.get("items", [])],
        )


@dataclass(slots=True)
class DirectionStep:
    """A single step in a recipe direction section.

    Attributes:
        step_number: 1-based step number within its section.
        content: The step's instruction text.
    """

    step_number: int | None
    content: str | None

    @classmethod
    def from_api(cls, data: dict[str, Any]) -> DirectionStep:
        """Build a :class:`DirectionStep` from a steps entry."""
        return cls(step_number=data.get("stepNumber"), content=data.get("content"))


@dataclass(slots=True)
class DirectionSection:
    """A named section of recipe directions.

    Attributes:
        name: Section name, e.g. ``"POSTUP"``.
        position: Ordering index of the section within the recipe.
        steps: The ordered steps in this section.
    """

    name: str | None
    position: int | None
    steps: list[DirectionStep] = field(default_factory=list)

    @classmethod
    def from_api(cls, data: dict[str, Any]) -> DirectionSection:
        """Build a :class:`DirectionSection` from a directions entry."""
        return cls(
            name=data.get("name"),
            position=data.get("position"),
            steps=[DirectionStep.from_api(step) for step in data.get("steps", [])],
        )


@dataclass(slots=True)
class RecipeAuthor:
    """Author of a recipe.

    Attributes:
        name: Author name.
        annotation: Short note or bio about the author.
    """

    name: str | None
    annotation: str | None


@dataclass(slots=True)
class RecipeDetail:
    """Detailed information about a recipe.

    Attributes:
        id: Recipe ID.
        name: Recipe name.
        duration: Human-readable preparation time, e.g. ``"Do hodinky"``
            ("within an hour"). This is a display string, not a number.
        servings: Raw list of serving options, in the API's own shape (each
            entry typically has ``name`` and ``default``).
        image: Relative path to the recipe image.
        author: The recipe's author.
        tips: Free-text tips for preparing the recipe.
        ingredients: Ingredients, grouped into named sections.
        directions: Cooking directions, grouped into named sections of steps.
        is_favorite: Whether the recipe is marked as a favourite by the user.
        link: Relative web path to the recipe on rohlik.cz.
    """

    id: int | None
    name: str | None
    duration: str | None
    servings: list[Any] = field(default_factory=list)
    image: str | None = None
    author: RecipeAuthor = field(default_factory=lambda: RecipeAuthor(None, None))
    tips: list[str] = field(default_factory=list)
    ingredients: list[IngredientGroup] = field(default_factory=list)
    directions: list[DirectionSection] = field(default_factory=list)
    is_favorite: bool = False
    link: str | None = None

    @classmethod
    def from_api(cls, payload: dict[str, Any]) -> RecipeDetail:
        """Build a :class:`RecipeDetail` from a recipe detail response."""
        data = payload.get("data", {})
        author = data.get("author", {})
        return cls(
            id=data.get("id"),
            name=data.get("name"),
            duration=data.get("duration"),
            servings=data.get("servings", []),
            image=data.get("image", {}).get("path"),
            author=RecipeAuthor(name=author.get("name"), annotation=author.get("annotation")),
            tips=[tip.get("content") for tip in data.get("tips", [])],
            ingredients=[IngredientGroup.from_api(group) for group in data.get("ingredients", [])],
            directions=[
                DirectionSection.from_api(section) for section in data.get("directions", [])
            ],
            is_favorite=data.get("isFavorite", False),
            link=data.get("link"),
        )


@dataclass(slots=True)
class IngredientProduct:
    """A purchasable product matched to a recipe ingredient.

    Attributes:
        product_id: Product ID. Use it with ``cart.add_items``.
        name: Product name.
        image: Relative path to the product image.
        price: Pre-formatted price string, e.g. ``"41.88 Kč"``.
        price_value: The raw numeric price (the ``full`` amount) behind
            :attr:`price`.
        unit: Base unit the product is sold in, e.g. ``"kg"`` or ``"ks"``
            (pieces).
        amount: Textual amount, e.g. ``"cca 1,2 kg"``.
        in_stock: Whether the product is currently in stock.
        is_favorite: Whether the product is marked as a favourite by the user.
    """

    product_id: int | None
    name: str | None
    image: str | None
    price: str
    price_value: Any
    unit: str | None
    amount: str | None
    in_stock: bool = False
    is_favorite: bool = False

    @classmethod
    def from_api(cls, data: dict[str, Any]) -> IngredientProduct:
        """Build an :class:`IngredientProduct` from a product entry."""
        price_info = data.get("price", {})
        return cls(
            product_id=data.get("productId"),
            name=data.get("productName"),
            image=data.get("imgPath"),
            price=format_price(price_info),
            price_value=price_info.get("full"),
            unit=data.get("unit"),
            amount=data.get("textualAmount"),
            in_stock=data.get("inStock", False),
            is_favorite=data.get("favourite", False),
        )


@dataclass(slots=True)
class IngredientProductGroup:
    """Products available for a single recipe ingredient.

    Attributes:
        ingredient_id: The ingredient these products are matched to.
        products: The purchasable products for this ingredient (this page).
        total_hits: Total number of products available for the ingredient (may
            exceed ``len(products)`` because results are paginated).
    """

    ingredient_id: int | None
    products: list[IngredientProduct] = field(default_factory=list)
    total_hits: int = 0

    @classmethod
    def from_api(cls, data: dict[str, Any]) -> IngredientProductGroup:
        """Build an :class:`IngredientProductGroup` from an ingredients entry."""
        return cls(
            ingredient_id=data.get("id"),
            products=[IngredientProduct.from_api(p) for p in data.get("products", [])],
            total_hits=data.get("totalHits", 0),
        )


@dataclass(slots=True)
class IngredientProducts:
    """Container mapping recipe ingredients to purchasable products.

    Attributes:
        ingredients: One group per requested ingredient ID.
    """

    ingredients: list[IngredientProductGroup] = field(default_factory=list)

    @classmethod
    def from_api(cls, payload: dict[str, Any]) -> IngredientProducts:
        """Build :class:`IngredientProducts` from an ingredient products response."""
        data = payload.get("data", {})
        return cls(
            ingredients=[
                IngredientProductGroup.from_api(ing) for ing in data.get("ingredients", [])
            ]
        )


# ---------------------------------------------------------------------------
# Account
# ---------------------------------------------------------------------------


@dataclass(slots=True)
class ShoppingList:
    """A saved shopping list.

    Attributes:
        name: The shopping list's name.
        products_in_list: Raw list of product entries on the list, in the API's
            own shape (each entry typically has ``productId`` and ``quantity``).
    """

    name: str | None
    products_in_list: list[Any] = field(default_factory=list)

    @classmethod
    def from_api(cls, data: dict[str, Any]) -> ShoppingList:
        """Build a :class:`ShoppingList` from a shopping list response."""
        return cls(
            name=data.get("name"),
            products_in_list=data.get("products", []),
        )


# ---------------------------------------------------------------------------
# Delivery tracking
# ---------------------------------------------------------------------------
#
# Parsed from the unofficial ``/api/v2/orders/{id}/delivery-tracking`` endpoint
# and ``/api/v3/orders/upcoming``. Parsing never raises: a missing level or a
# value of the wrong type becomes ``None``.


def _as_int(value: Any) -> int | None:
    """Return value if it is an int (bool excluded), else None."""
    return value if isinstance(value, int) and not isinstance(value, bool) else None


def _as_float(value: Any) -> float | None:
    """Return value as a finite float if it is a real number (bool excluded), else None."""
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return None
    try:
        result = float(value)
    except OverflowError:
        return None
    return result if math.isfinite(result) else None


def _as_bool(value: Any) -> bool | None:
    """Return value if it is a bool, else None."""
    return value if isinstance(value, bool) else None


def _as_str(value: Any) -> str | None:
    """Return value if it is a non-empty string, else None."""
    return value if isinstance(value, str) and value else None


def _as_dict(value: Any) -> dict[str, Any]:
    """Return value if it is a dict, else an empty dict."""
    return value if isinstance(value, dict) else {}


class TrackingStatus(StrEnum):
    """Delivery statuses observed in ``progress.deliveryStatus``, in lifecycle order.

    Models keep the raw string, so a value not listed here is preserved as-is.
    """

    IN_QUEUE = "IN_QUEUE"
    ON_THE_WAY = "ON_THE_WAY"
    ARRIVED = "ARRIVED"
    HANDING_OVER = "HANDING_OVER"
    DELIVERED = "DELIVERED"


DeliveryEtaSource = Literal["tracking", "slot"]
"""Where :attr:`NextDelivery.eta` came from."""


#: Mean Earth radius in metres, for the haversine distance.
_EARTH_RADIUS_M = 6_371_008.8


def _distance_m(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Great-circle distance between two points in metres (haversine)."""
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = phi2 - phi1
    dlambda = math.radians(lon2 - lon1)
    a = math.sin(dphi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlambda / 2) ** 2
    return 2 * _EARTH_RADIUS_M * math.asin(min(1.0, math.sqrt(a)))


def _coordinates(data: Any) -> tuple[float, float] | None:
    """Return (latitude, longitude) from ``data`` if valid, else None.

    Both must be real numbers within range. Exactly (0, 0), a point in the
    Gulf of Guinea, is treated as a missing-value placeholder.
    """
    data = _as_dict(data)
    latitude = _as_float(data.get("latitude"))
    longitude = _as_float(data.get("longitude"))
    if latitude is None or longitude is None:
        return None
    if not (-90.0 <= latitude <= 90.0 and -180.0 <= longitude <= 180.0):
        return None
    if latitude == 0.0 and longitude == 0.0:
        return None
    return latitude, longitude


class GeoPoint(Protocol):
    """Anything with ``latitude`` and ``longitude`` in degrees.

    :meth:`CourierPosition.distance_to` accepts any such object, e.g. a
    :class:`DeliveryDestination`, another position or your own home point.
    """

    @property
    def latitude(self) -> float: ...

    @property
    def longitude(self) -> float: ...


@dataclass(slots=True)
class DeliveryDestination:
    """Where the order is delivered (the response's ``destination``).

    This is the customer's address as coordinates, so personal data: do not
    log or expose it without redaction.

    Attributes:
        latitude: Latitude in degrees.
        longitude: Longitude in degrees.
    """

    latitude: float = field(repr=False)
    longitude: float = field(repr=False)

    @classmethod
    def from_api(cls, data: Any) -> DeliveryDestination | None:
        """Build a destination from ``destination``, or None if missing or invalid."""
        coordinates = _coordinates(data)
        if coordinates is None:
            return None
        return cls(latitude=coordinates[0], longitude=coordinates[1])


@dataclass(slots=True)
class CourierPosition:
    """The courier's last reported location.

    This is personal data (a third party's location): do not log or expose it
    without redaction.

    Attributes:
        latitude: Latitude in degrees.
        longitude: Longitude in degrees.
        recorded_at: When the position was recorded (aware), or None.
    """

    latitude: float = field(repr=False)
    longitude: float = field(repr=False)
    recorded_at: datetime | None

    @classmethod
    def from_api(cls, data: Any) -> CourierPosition | None:
        """Build a position from ``progress.courierPosition``, or None if missing or invalid.

        Out-of-range coordinates and the (0, 0) placeholder count as missing.
        """
        coordinates = _coordinates(data)
        if coordinates is None:
            return None
        return cls(
            latitude=coordinates[0],
            longitude=coordinates[1],
            recorded_at=parse_datetime(_as_dict(data).get("recordedAt")),
        )

    def distance_to(self, other: GeoPoint) -> float:
        """Straight-line (great-circle) distance to ``other`` in metres.

        ``other`` is any object with ``latitude`` and ``longitude`` (see
        :class:`GeoPoint`). This is not the driving distance: the courier's
        route is longer.
        """
        return _distance_m(self.latitude, self.longitude, other.latitude, other.longitude)


@dataclass(slots=True)
class DeliveryProgress:
    """The live part of delivery tracking (the response's ``progress`` object).

    The shop returns no progress until the order is queued for a courier.

    Attributes:
        status: Raw ``deliveryStatus``; see :class:`TrackingStatus` for known values.
        generated_at: When the shop generated this snapshot. It can be several
            minutes old and stops changing after delivery, so it is not the time
            of the request.
        estimated_arrival: The courier's estimated arrival (aware, UTC). It can
            be None early in the queue. After delivery it keeps the last
            estimate, which is not the actual arrival time.
        stops_before: Stops the courier makes before this order. ``0`` means
            none; None means unknown (e.g. after delivery).
        courier_location_stale: Whether the shop flags the position as stale.
        courier_position: The courier's location while on the way (personal
            data, hidden from ``repr``).
    """

    status: str | None
    generated_at: datetime | None
    estimated_arrival: datetime | None
    stops_before: int | None
    courier_location_stale: bool | None
    courier_position: CourierPosition | None = field(default=None, repr=False)

    @classmethod
    def from_api(cls, data: Any) -> DeliveryProgress | None:
        """Build progress from the ``progress`` object, or None if it is absent."""
        if not isinstance(data, dict):
            return None
        return cls(
            status=_as_str(data.get("deliveryStatus")),
            generated_at=parse_datetime(data.get("generatedAt")),
            estimated_arrival=parse_datetime(data.get("estimatedArrival")),
            stops_before=_as_int(data.get("stopsBefore")),
            courier_location_stale=_as_bool(data.get("courierLocationStale")),
            courier_position=CourierPosition.from_api(data.get("courierPosition")),
        )


@dataclass(slots=True)
class DeliveryTracking:
    """Live tracking of one order's delivery.

    Attributes:
        order_id: The tracked order's ID.
        slot_since: Start of the booked delivery slot (aware).
        slot_till: End of the booked delivery slot (aware).
        slot_type: Slot type, e.g. ``"ON_TIME"``.
        early_delivery_available: Whether the customer may allow early delivery.
        early_delivery_requested: Whether the customer allowed early delivery.
        early_delivery_allowed_from: Earliest delivery time once early delivery
            is allowed (aware), or None.
        progress: The live state, or None before the order is queued.
        courier_name: The courier's display name (a first name in observed
            data), or None until the order is queued. Personal data, hidden
            from ``repr``.
        destination: The delivery address as coordinates, or None if the
            response has none. Personal data, hidden from ``repr``.
    """

    order_id: int | None
    slot_since: datetime | None
    slot_till: datetime | None
    slot_type: str | None
    early_delivery_available: bool | None
    early_delivery_requested: bool | None
    early_delivery_allowed_from: datetime | None
    progress: DeliveryProgress | None
    courier_name: str | None = field(default=None, repr=False)
    destination: DeliveryDestination | None = field(default=None, repr=False)

    @classmethod
    def from_api(cls, data: Any) -> DeliveryTracking:
        """Build tracking from a delivery-tracking response.

        The courier's phone number and photo and the route/movement polylines
        are deliberately not kept.
        """
        data = _as_dict(data)
        slot = _as_dict(data.get("deliverySlot"))
        early = _as_dict(data.get("earlyDelivery"))
        courier = _as_dict(data.get("courier"))
        return cls(
            order_id=_as_int(data.get("orderId")),
            slot_since=parse_datetime(slot.get("since")),
            slot_till=parse_datetime(slot.get("till")),
            slot_type=_as_str(slot.get("type")),
            early_delivery_available=_as_bool(early.get("available")),
            early_delivery_requested=_as_bool(early.get("requested")),
            early_delivery_allowed_from=parse_datetime(early.get("allowedFrom")),
            progress=DeliveryProgress.from_api(data.get("progress")),
            courier_name=_as_str(courier.get("displayName")),
            destination=DeliveryDestination.from_api(data.get("destination")),
        )

    @property
    def status(self) -> str | None:
        """The raw delivery status, or None before the order is queued."""
        return self.progress.status if self.progress else None

    @property
    def estimated_arrival(self) -> datetime | None:
        """The courier's estimated arrival as served (uncapped), or None."""
        return self.progress.estimated_arrival if self.progress else None

    @property
    def stops_before(self) -> int | None:
        """Stops the courier makes before this order, or None."""
        return self.progress.stops_before if self.progress else None

    @property
    def courier_position(self) -> CourierPosition | None:
        """The courier's last reported location, or None.

        In observed data the shop reports it from ``ON_THE_WAY`` through
        ``HANDING_OVER``; it is kept in whatever status it comes with. Check
        ``progress.courier_location_stale`` before trusting it as current.
        """
        return self.progress.courier_position if self.progress else None

    @property
    def courier_distance(self) -> float | None:
        """Straight-line distance from the courier to the destination in metres.

        None unless both the courier position and the destination are known.
        This is not the driving distance: the courier's route is longer. It
        does not check ``progress.courier_location_stale`` or the status: a
        stale or last-known position still gives a distance, so check those
        yourself before showing it as current.
        """
        position = self.courier_position
        if position is None or self.destination is None:
            return None
        return position.distance_to(self.destination)

    @property
    def is_active(self) -> bool:
        """Whether a delivery is in progress.

        True for any status other than ``DELIVERED``, including values not in
        :class:`TrackingStatus`, so a new status never hides a live delivery.
        """
        status = self.status
        return status is not None and status != TrackingStatus.DELIVERED

    @property
    def has_arrived(self) -> bool:
        """Whether the courier is at the destination (``ARRIVED``/``HANDING_OVER``)."""
        return self.status in (TrackingStatus.ARRIVED, TrackingStatus.HANDING_OVER)

    @property
    def is_delivered(self) -> bool:
        """Whether the order has been delivered."""
        return self.status == TrackingStatus.DELIVERED

    @property
    def arrival_floor(self) -> datetime | None:
        """The earliest time the shop lets the courier arrive.

        ``early_delivery_allowed_from`` once early delivery is allowed,
        otherwise the slot start; None if unknown.
        """
        if self.early_delivery_requested and self.early_delivery_allowed_from is not None:
            return self.early_delivery_allowed_from
        return self.slot_since


@dataclass(slots=True)
class UpcomingOrder:
    """An order that has not been delivered yet.

    Attributes:
        id: The order ID.
        slot_id: The booked delivery slot's ID.
        slot_type: Slot type, e.g. ``"ON_TIME"``.
        slot_since: Start of the delivery slot (aware).
        slot_till: End of the delivery slot (aware).
        order_time: When the order was placed (aware).
        items_count: Number of order lines.
        items_total_quantity: Total number of units across all lines.
        total_price: Order total, in :attr:`currency`.
        currency: ISO 4217 currency code, e.g. ``"CZK"``.
        available_actions: Actions the shop offers, e.g. ``["NOTE_CHANGE"]``.
    """

    id: int
    slot_id: int | None
    slot_type: str | None
    slot_since: datetime | None
    slot_till: datetime | None
    order_time: datetime | None
    items_count: int | None
    items_total_quantity: int | None
    total_price: float | None
    currency: str | None
    available_actions: list[str] = field(default_factory=list)

    @classmethod
    def from_api(cls, data: Any) -> UpcomingOrder | None:
        """Build an order from an upcoming-orders entry, or None without an ID.

        The delivery address, payment details and item images are not kept.
        """
        data = _as_dict(data)
        order_id = _as_int(data.get("id"))
        if order_id is None:
            return None
        slot = _as_dict(data.get("deliverySlot"))
        total = _as_dict(_as_dict(data.get("priceComposition")).get("total"))
        actions = data.get("availableActions")
        return cls(
            id=order_id,
            slot_id=_as_int(slot.get("id")),
            slot_type=_as_str(slot.get("type")),
            slot_since=parse_datetime(slot.get("since")),
            slot_till=parse_datetime(slot.get("till")),
            order_time=parse_datetime(data.get("orderTime")),
            items_count=_as_int(data.get("itemsCount")),
            items_total_quantity=_as_int(data.get("itemsTotalQuantity")),
            total_price=_as_float(total.get("amount")),
            currency=_as_str(total.get("currency")),
            available_actions=(
                [a for a in actions if isinstance(a, str)] if isinstance(actions, list) else []
            ),
        )

    @classmethod
    def list_from_api(cls, data: Any) -> list[UpcomingOrder]:
        """Parse a raw upcoming-orders list, soonest delivery slot first.

        Accepts the response of ``/api/v3/orders/upcoming`` (for example
        ``RohlikAPI.get_data()["next_order"]``). Entries without an ID are
        skipped; orders without a slot are sorted last. A non-list gives ``[]``.
        """
        if not isinstance(data, list):
            return []
        orders = [order for order in map(cls.from_api, data) if order is not None]
        return sorted(
            orders,
            key=lambda o: (o.slot_since is None, o.slot_since.timestamp() if o.slot_since else 0),
        )


@dataclass(slots=True)
class NextDelivery:
    """The soonest upcoming order with its tracking and resolved ETA.

    Attributes:
        order: The soonest upcoming order.
        tracking: Its delivery tracking, or None if the shop has none for it.
        eta: The best estimate of the arrival time (aware), or None.
        eta_source: ``"tracking"`` (courier estimate) or ``"slot"`` (booked
            slot start), or None without an ETA.
        eta_capped: True when the courier estimate was earlier than the shop
            allows delivery and :attr:`eta` was raised to that limit.
        status: The tracking status, or None without tracking progress.
    """

    order: UpcomingOrder
    tracking: DeliveryTracking | None
    eta: datetime | None
    eta_source: DeliveryEtaSource | None
    eta_capped: bool
    status: str | None

    @classmethod
    def resolve(cls, order: UpcomingOrder, tracking: DeliveryTracking | None) -> NextDelivery:
        """Combine an order and its tracking into a :class:`NextDelivery` (no I/O).

        ETA rule (a heuristic based on one observed delivery): use the courier
        estimate; while the order is still ``IN_QUEUE``, never report it earlier
        than :attr:`DeliveryTracking.arrival_floor`, because the shop does not
        deliver before the slot start unless early delivery was allowed. Once
        the courier is on the way the estimate is used as served, so the ETA
        can move earlier at that moment (``eta_capped`` turns False). Without
        an estimate, fall back to the slot start (the order's, else the
        tracking's). The uncapped estimate stays available as
        ``tracking.estimated_arrival``.

        Raises:
            ValueError: If ``tracking`` belongs to a different order.
        """
        if tracking is not None and tracking.order_id is not None and tracking.order_id != order.id:
            raise ValueError(f"Tracking is for order {tracking.order_id}, not for order {order.id}")
        estimate = tracking.estimated_arrival if tracking else None
        slot_since = order.slot_since or (tracking.slot_since if tracking else None)
        eta: datetime | None
        source: DeliveryEtaSource | None
        capped = False
        if tracking is not None and estimate is not None:
            eta, source = estimate, "tracking"
            floor = tracking.arrival_floor
            queued = tracking.status == TrackingStatus.IN_QUEUE
            if queued and floor is not None and estimate < floor:
                eta, capped = floor, True
        elif slot_since is not None:
            eta, source = slot_since, "slot"
        else:
            eta, source = None, None
        return cls(
            order=order,
            tracking=tracking,
            eta=eta,
            eta_source=source,
            eta_capped=capped,
            status=tracking.status if tracking else None,
        )
