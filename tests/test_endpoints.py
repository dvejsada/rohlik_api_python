"""Tests for the Endpoints class."""

import pytest
from rohlik_api import Endpoints, BASE_URL


class TestEndpointsConstants:
    """Tests for Endpoints constants."""

    def test_base_url(self):
        """Test BASE_URL is correct."""
        assert BASE_URL == "https://www.rohlik.cz"

    def test_login_endpoint(self):
        """Test LOGIN endpoint."""
        assert Endpoints.LOGIN == "/services/frontend-service/login"

    def test_logout_endpoint(self):
        """Test LOGOUT endpoint."""
        assert Endpoints.LOGOUT == "/services/frontend-service/logout"

    def test_cart_endpoint(self):
        """Test CART endpoint."""
        assert Endpoints.CART == "/services/frontend-service/v2/cart"

    def test_search_endpoint(self):
        """Test SEARCH endpoint."""
        assert Endpoints.SEARCH == "/services/frontend-service/search-metadata"

    def test_delivery_endpoint(self):
        """Test DELIVERY endpoint."""
        assert "first-delivery" in Endpoints.DELIVERY

    def test_next_order_endpoint(self):
        """Test NEXT_ORDER endpoint."""
        assert Endpoints.NEXT_ORDER == "/api/v3/orders/upcoming"

    def test_delivered_orders_endpoint(self):
        """Test DELIVERED_ORDERS endpoint."""
        assert Endpoints.DELIVERED_ORDERS == "/api/v3/orders/delivered"

    def test_premium_profile_endpoint(self):
        """Test PREMIUM_PROFILE endpoint."""
        assert "premium/profile" in Endpoints.PREMIUM_PROFILE

    def test_bags_endpoint(self):
        """Test BAGS endpoint."""
        assert "reusable-bags" in Endpoints.BAGS


class TestEndpointsBuilders:
    """Tests for Endpoints builder methods."""

    def test_shopping_list_builder(self):
        """Test shopping_list endpoint builder."""
        result = Endpoints.shopping_list("abc123")
        assert "abc123" in result
        assert "/api/v1/shopping-lists/id/" in result

    def test_shopping_list_builder_with_uuid(self):
        """Test shopping_list with UUID-like ID."""
        uuid = "550e8400-e29b-41d4-a716-446655440000"
        result = Endpoints.shopping_list(uuid)
        assert uuid in result

    def test_delivered_orders_builder_default(self):
        """Test delivered_orders builder with defaults."""
        result = Endpoints.delivered_orders()
        assert "offset=0" in result
        assert "limit=50" in result

    def test_delivered_orders_builder_custom(self):
        """Test delivered_orders builder with custom values."""
        result = Endpoints.delivered_orders(limit=10, offset=20)
        assert "offset=20" in result
        assert "limit=10" in result

    def test_timeslots_builder(self):
        """Test timeslots endpoint builder."""
        result = Endpoints.timeslots(user_id=12345, address_id=67890)
        assert "userId=12345" in result
        assert "addressId=67890" in result
        assert "reasonableDeliveryTime=true" in result

    def test_timeslots_builder_different_ids(self):
        """Test timeslots with different IDs."""
        result = Endpoints.timeslots(user_id=1, address_id=2)
        assert "userId=1" in result
        assert "addressId=2" in result


class TestEndpointsCompleteness:
    """Tests for Endpoints completeness."""

    def test_all_auth_endpoints_exist(self):
        """Test all authentication endpoints exist."""
        assert hasattr(Endpoints, 'LOGIN')
        assert hasattr(Endpoints, 'LOGOUT')

    def test_all_cart_endpoints_exist(self):
        """Test all cart endpoints exist."""
        assert hasattr(Endpoints, 'CART')

    def test_all_product_endpoints_exist(self):
        """Test all product endpoints exist."""
        assert hasattr(Endpoints, 'SEARCH')
        assert hasattr(Endpoints, 'SHOPPING_LIST')

    def test_all_delivery_endpoints_exist(self):
        """Test all delivery endpoints exist."""
        assert hasattr(Endpoints, 'DELIVERY')
        assert hasattr(Endpoints, 'TIMESLOT_RESERVATION')
        assert hasattr(Endpoints, 'TIMESLOTS_BASE')
        assert hasattr(Endpoints, 'DELIVERY_ANNOUNCEMENTS')

    def test_all_order_endpoints_exist(self):
        """Test all order endpoints exist."""
        assert hasattr(Endpoints, 'NEXT_ORDER')
        assert hasattr(Endpoints, 'LAST_ORDER')
        assert hasattr(Endpoints, 'DELIVERED_ORDERS')

    def test_all_account_endpoints_exist(self):
        """Test all account endpoints exist."""
        assert hasattr(Endpoints, 'PREMIUM_PROFILE')
        assert hasattr(Endpoints, 'BAGS')
        assert hasattr(Endpoints, 'ANNOUNCEMENTS')

    def test_all_recipe_endpoints_exist(self):
        """Test all recipe endpoints exist."""
        assert hasattr(Endpoints, 'RECIPE_SEARCH')
        assert hasattr(Endpoints, 'RECIPE_DETAIL')
        assert hasattr(Endpoints, 'INGREDIENT_PRODUCTS')


class TestEndpointsRecipeBuilders:
    """Tests for recipe endpoint builder methods."""

    def test_recipe_search_builder(self):
        """Test recipe_search endpoint builder."""
        result = Endpoints.recipe_search("rajská", limit=5, offset=0)
        assert "raj" in result  # URL encoded
        assert "limit=5" in result
        assert "offset=0" in result

    def test_recipe_search_builder_encodes_query(self):
        """Test recipe_search URL encodes the query."""
        result = Endpoints.recipe_search("česká kuchyně")
        assert "%C4%8D" in result or "česká" not in result  # Should be encoded

    def test_recipe_detail_builder(self):
        """Test recipe_detail endpoint builder."""
        result = Endpoints.recipe_detail(59)
        assert "/59" in result
        assert "recipe" in result

