"""Typed data models for the Rohlik.cz API client.

Service methods return these dataclasses instead of raw dictionaries. Each model
provides a ``from_api`` classmethod that parses the relevant slice of a Rohlik
API response. All models are plain dataclasses, so ``dataclasses.asdict`` can be
used to convert them back to JSON-serialisable dictionaries (useful for the
Home Assistant integration and the MCP server).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from .helpers import format_price

# ---------------------------------------------------------------------------
# Cart
# ---------------------------------------------------------------------------


@dataclass(slots=True)
class CartItem:
    """A single item in the shopping cart."""

    id: str
    cart_item_id: str
    name: str
    quantity: int
    price: float
    category_name: str = ""
    brand: str = ""

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
        )


@dataclass(slots=True)
class Cart:
    """The current shopping cart."""

    total_price: float
    total_items: int
    can_make_order: bool
    products: list[CartItem] = field(default_factory=list)

    @classmethod
    def from_api(cls, payload: dict[str, Any]) -> Cart:
        """Build a :class:`Cart` from a ``/v2/cart`` response."""
        data = payload.get("data", {})
        items: dict[str, Any] = data.get("items", {})
        return cls(
            total_price=data.get("totalPrice", 0),
            total_items=len(items),
            can_make_order=data.get("submitConditionPassed", False),
            products=[CartItem.from_api(pid, pdata) for pid, pdata in items.items()],
        )


# ---------------------------------------------------------------------------
# Products
# ---------------------------------------------------------------------------


@dataclass(slots=True)
class ProductSearchResult:
    """A product entry from a search response."""

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
    """Container for product search results."""

    results: list[ProductSearchResult] = field(default_factory=list)


@dataclass(slots=True)
class AISummary:
    """AI-generated summary for a product."""

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
    """Nutritional values for a single portion."""

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
    """Allergen information for a product."""

    contained: list[str] = field(default_factory=list)
    possibly_contained: list[str] = field(default_factory=list)


@dataclass(slots=True)
class ProductComposition:
    """Composition and nutritional information for a product."""

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
    """Current price information for a product."""

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


# ---------------------------------------------------------------------------
# Recipes (Rohlík Chef)
# ---------------------------------------------------------------------------


@dataclass(slots=True)
class RecipeSummary:
    """A recipe entry from a recipe search response."""

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
    """Container for recipe search results."""

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
    """A single ingredient within a recipe ingredient group."""

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
    """A named group of recipe ingredients."""

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
    """A single step in a recipe direction section."""

    step_number: int | None
    content: str | None

    @classmethod
    def from_api(cls, data: dict[str, Any]) -> DirectionStep:
        """Build a :class:`DirectionStep` from a steps entry."""
        return cls(step_number=data.get("stepNumber"), content=data.get("content"))


@dataclass(slots=True)
class DirectionSection:
    """A named section of recipe directions."""

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
    """Author of a recipe."""

    name: str | None
    annotation: str | None


@dataclass(slots=True)
class RecipeDetail:
    """Detailed information about a recipe."""

    id: int | None
    name: str | None
    duration: int | None
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
    """A purchasable product matched to a recipe ingredient."""

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
    """Products available for a single ingredient."""

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
    """Container for ingredient product groups."""

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
    """A saved shopping list."""

    name: str | None
    products_in_list: list[Any] = field(default_factory=list)

    @classmethod
    def from_api(cls, data: dict[str, Any]) -> ShoppingList:
        """Build a :class:`ShoppingList` from a shopping list response."""
        return cls(
            name=data.get("name"),
            products_in_list=data.get("products", []),
        )
