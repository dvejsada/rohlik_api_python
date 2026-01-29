"""Tests for the data models."""

import pytest
from rohlik_api.models import (
    CartItem,
    Cart,
    ProductSearchResult,
    SearchResults,
    ShoppingListItem,
    ShoppingList,
    AddToCartRequest,
)


class TestCartItem:
    """Tests for CartItem model."""

    def test_cart_item_creation(self):
        """Test CartItem can be created with required fields."""
        item = CartItem(
            id="123",
            cart_item_id="cart_456",
            name="Test Product",
            quantity=2,
            price=99.90
        )
        assert item.id == "123"
        assert item.cart_item_id == "cart_456"
        assert item.name == "Test Product"
        assert item.quantity == 2
        assert item.price == 99.90

    def test_cart_item_with_optional_fields(self):
        """Test CartItem with optional fields."""
        item = CartItem(
            id="123",
            cart_item_id="cart_456",
            name="Test Product",
            quantity=2,
            price=99.90,
            category_name="Food",
            brand="TestBrand"
        )
        assert item.category_name == "Food"
        assert item.brand == "TestBrand"

    def test_cart_item_default_optional_fields(self):
        """Test CartItem default values for optional fields."""
        item = CartItem(
            id="123",
            cart_item_id="cart_456",
            name="Test Product",
            quantity=2,
            price=99.90
        )
        assert item.category_name == ""
        assert item.brand == ""


class TestCart:
    """Tests for Cart model."""

    def test_cart_creation(self):
        """Test Cart can be created."""
        cart = Cart(
            total_price=199.90,
            total_items=3,
            can_make_order=True
        )
        assert cart.total_price == 199.90
        assert cart.total_items == 3
        assert cart.can_make_order is True
        assert cart.products == []

    def test_cart_with_products(self):
        """Test Cart with products."""
        item = CartItem(
            id="123",
            cart_item_id="cart_456",
            name="Test Product",
            quantity=2,
            price=99.90
        )
        cart = Cart(
            total_price=99.90,
            total_items=1,
            can_make_order=True,
            products=[item]
        )
        assert len(cart.products) == 1
        assert cart.products[0].name == "Test Product"


class TestProductSearchResult:
    """Tests for ProductSearchResult model."""

    def test_product_search_result_creation(self):
        """Test ProductSearchResult can be created."""
        product = ProductSearchResult(
            id=12345,
            name="Test Product",
            price="99.90 Kč"
        )
        assert product.id == 12345
        assert product.name == "Test Product"
        assert product.price == "99.90 Kč"

    def test_product_search_result_with_optional(self):
        """Test ProductSearchResult with optional fields."""
        product = ProductSearchResult(
            id=12345,
            name="Test Product",
            price="99.90 Kč",
            brand="TestBrand",
            amount="500g"
        )
        assert product.brand == "TestBrand"
        assert product.amount == "500g"


class TestSearchResults:
    """Tests for SearchResults model."""

    def test_search_results_empty(self):
        """Test empty SearchResults."""
        results = SearchResults()
        assert results.results == []

    def test_search_results_with_products(self):
        """Test SearchResults with products."""
        product = ProductSearchResult(id=1, name="Test", price="10 Kč")
        results = SearchResults(results=[product])
        assert len(results.results) == 1


class TestShoppingListItem:
    """Tests for ShoppingListItem model."""

    def test_shopping_list_item_creation(self):
        """Test ShoppingListItem can be created."""
        item = ShoppingListItem(product_id=12345, quantity=3)
        assert item.product_id == 12345
        assert item.quantity == 3


class TestShoppingList:
    """Tests for ShoppingList model."""

    def test_shopping_list_creation(self):
        """Test ShoppingList can be created."""
        shopping_list = ShoppingList(name="My List")
        assert shopping_list.name == "My List"
        assert shopping_list.products == []

    def test_shopping_list_with_products(self):
        """Test ShoppingList with products."""
        item = ShoppingListItem(product_id=123, quantity=2)
        shopping_list = ShoppingList(name="My List", products=[item])
        assert len(shopping_list.products) == 1


class TestAddToCartRequest:
    """Tests for AddToCartRequest model."""

    def test_add_to_cart_request_creation(self):
        """Test AddToCartRequest can be created."""
        request = AddToCartRequest(product_id=12345, quantity=2)
        assert request.product_id == 12345
        assert request.quantity == 2
