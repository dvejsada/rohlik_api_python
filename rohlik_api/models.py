"""Typed data models for the Rohlik.cz API client.

Service methods return these dataclasses instead of raw dictionaries. Each model
provides a ``from_api`` classmethod that parses the relevant slice of a Rohlik
API response. All models are plain dataclasses, so ``dataclasses.asdict`` can be
used to convert them back to JSON-serialisable dictionaries (useful for the
Home Assistant integration and the MCP server).

Monetary amounts come in two shapes: ``price`` fields typed as ``str`` are
pre-formatted for display (for example ``"29.90 Kč"``), while numeric ``price``
fields are raw amounts paired with a separate ``currency``. Czech crowns (CZK,
"Kč") are the usual currency.
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
    """A single item (line) in the shopping cart.

    Attributes:
        id: The product ID, as a string.
        cart_item_id: The cart-line identifier (``orderFieldId``). Pass this to
            :meth:`~rohlik_api.RohlikAPI.cart`'s ``delete_item`` to remove the
            line from the cart.
        name: Product name.
        quantity: Number of units of this product in the cart.
        price: Line price for this product, in the account currency (CZK).
        category_name: Primary category name of the product.
        brand: Brand name, or an empty string if unknown.
    """

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
    """The current shopping cart.

    Attributes:
        total_price: Total price of the cart, in the account currency (CZK).
        total_items: Number of distinct products in the cart (line count, not
            the summed quantity).
        can_make_order: Whether the cart currently satisfies the conditions to
            place an order (e.g. the minimum order value is met).
        products: The cart's line items.
    """

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
            in_stock=stock.get("availabilityStatus") == "AVAILABLE",
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
