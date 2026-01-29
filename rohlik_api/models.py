"""Data models for Rohlik.cz API."""

from dataclasses import dataclass, field
from typing import List, Optional


@dataclass
class CartItem:
    """Represents an item in the shopping cart."""
    id: str
    cart_item_id: str
    name: str
    quantity: int
    price: float
    category_name: str = ""
    brand: str = ""


@dataclass
class Cart:
    """Represents the shopping cart."""
    total_price: float
    total_items: int
    can_make_order: bool
    products: List[CartItem] = field(default_factory=list)


@dataclass
class ProductSearchResult:
    """Represents a product from search results."""
    id: int
    name: str
    price: str
    brand: Optional[str] = None
    amount: Optional[str] = None


@dataclass
class SearchResults:
    """Container for product search results."""
    results: List[ProductSearchResult] = field(default_factory=list)


@dataclass
class ShoppingListItem:
    """Represents an item in a shopping list."""
    product_id: int
    quantity: int


@dataclass
class ShoppingList:
    """Represents a shopping list."""
    name: str
    products: List[ShoppingListItem] = field(default_factory=list)


@dataclass
class AddToCartRequest:
    """Request to add a product to cart."""
    product_id: int
    quantity: int
