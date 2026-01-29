"""Tests for the service classes."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from rohlik_api.http_client import HttpClient
from rohlik_api.auth import AuthManager
from rohlik_api.services import (
    BaseService,
    CartService,
    ProductService,
    OrderService,
    DeliveryService,
    AccountService,
)


# Fixtures
@pytest.fixture
def mock_http():
    """Create a mock HttpClient."""
    http = MagicMock(spec=HttpClient)
    http.get = AsyncMock()
    http.post = AsyncMock()
    http.delete = AsyncMock()
    return http


@pytest.fixture
def mock_auth():
    """Create a mock AuthManager."""
    auth = MagicMock(spec=AuthManager)
    auth.ensure_logged_in = AsyncMock()
    auth.is_logged_in = True
    auth.user_id = 12345
    auth.address_id = 67890
    return auth


class TestBaseService:
    """Tests for BaseService."""

    def test_base_service_initialization(self, mock_http, mock_auth):
        """Test BaseService initializes correctly."""
        service = BaseService(mock_http, mock_auth)
        assert service._http == mock_http
        assert service._auth == mock_auth

    @pytest.mark.asyncio
    async def test_ensure_logged_in_calls_auth(self, mock_http, mock_auth):
        """Test _ensure_logged_in delegates to auth manager."""
        service = BaseService(mock_http, mock_auth)
        await service._ensure_logged_in()
        mock_auth.ensure_logged_in.assert_called_once()


class TestCartService:
    """Tests for CartService."""

    def test_cart_service_initialization(self, mock_http, mock_auth):
        """Test CartService initializes correctly."""
        service = CartService(mock_http, mock_auth)
        assert isinstance(service, BaseService)

    @pytest.mark.asyncio
    async def test_get_content_calls_auth(self, mock_http, mock_auth):
        """Test get_content ensures logged in."""
        mock_response = MagicMock()
        mock_response.json.return_value = {"data": {"items": {}, "totalPrice": 0}}
        mock_response.raise_for_status = MagicMock()
        mock_http.get.return_value = mock_response

        service = CartService(mock_http, mock_auth)
        await service.get_content()
        mock_auth.ensure_logged_in.assert_called()

    @pytest.mark.asyncio
    async def test_get_content_returns_formatted_data(self, mock_http, mock_auth):
        """Test get_content returns properly formatted cart data."""
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "data": {
                "items": {
                    "123": {
                        "orderFieldId": "field_1",
                        "productName": "Test Product",
                        "quantity": 2,
                        "price": 99.90,
                        "primaryCategoryName": "Food",
                        "brand": "TestBrand"
                    }
                },
                "totalPrice": 99.90,
                "submitConditionPassed": True
            }
        }
        mock_response.raise_for_status = MagicMock()
        mock_http.get.return_value = mock_response

        service = CartService(mock_http, mock_auth)
        result = await service.get_content()

        assert result["total_price"] == 99.90
        assert result["total_items"] == 1
        assert result["can_make_order"] is True
        assert len(result["products"]) == 1
        assert result["products"][0]["name"] == "Test Product"

    @pytest.mark.asyncio
    async def test_add_items_sends_correct_payload(self, mock_http, mock_auth):
        """Test add_items sends correct payload."""
        mock_response = MagicMock()
        mock_response.raise_for_status = MagicMock()
        mock_http.post.return_value = mock_response

        service = CartService(mock_http, mock_auth)
        products = [{"product_id": 123, "quantity": 2}]
        result = await service.add_items(products)

        assert 123 in result["added_products"]
        mock_http.post.assert_called()


class TestProductService:
    """Tests for ProductService."""

    def test_product_service_initialization(self, mock_http, mock_auth):
        """Test ProductService initializes correctly."""
        service = ProductService(mock_http, mock_auth)
        assert isinstance(service, BaseService)

    @pytest.mark.asyncio
    async def test_search_returns_none_when_no_products(self, mock_http, mock_auth):
        """Test search returns None when no products found."""
        mock_response = MagicMock()
        mock_response.json.return_value = {"data": {"productList": []}}
        mock_response.raise_for_status = MagicMock()
        mock_http.get.return_value = mock_response

        service = ProductService(mock_http, mock_auth)
        result = await service.search("nonexistent")

        assert result is None

    @pytest.mark.asyncio
    async def test_search_filters_promoted_products(self, mock_http, mock_auth):
        """Test search filters out promoted products."""
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "data": {
                "productList": [
                    {"productId": 1, "productName": "Regular", "badge": [], "price": {"full": 10, "currency": "Kč"}},
                    {"productId": 2, "productName": "Promoted", "badge": [{"slug": "promoted"}], "price": {"full": 20, "currency": "Kč"}},
                ]
            }
        }
        mock_response.raise_for_status = MagicMock()
        mock_http.get.return_value = mock_response

        service = ProductService(mock_http, mock_auth)
        result = await service.search("test")

        assert len(result["search_results"]) == 1
        assert result["search_results"][0]["name"] == "Regular"


class TestOrderService:
    """Tests for OrderService."""

    def test_order_service_initialization(self, mock_http, mock_auth):
        """Test OrderService initializes correctly."""
        service = OrderService(mock_http, mock_auth)
        assert isinstance(service, BaseService)

    @pytest.mark.asyncio
    async def test_get_next_returns_data(self, mock_http, mock_auth):
        """Test get_next returns order data."""
        mock_response = MagicMock()
        mock_response.json.return_value = {"order_id": 123}
        mock_response.raise_for_status = MagicMock()
        mock_http.get.return_value = mock_response

        service = OrderService(mock_http, mock_auth)
        result = await service.get_next()

        assert result == {"order_id": 123}

    @pytest.mark.asyncio
    async def test_get_delivered_with_pagination(self, mock_http, mock_auth):
        """Test get_delivered accepts pagination parameters."""
        mock_response = MagicMock()
        mock_response.json.return_value = [{"order_id": 1}, {"order_id": 2}]
        mock_response.raise_for_status = MagicMock()
        mock_http.get.return_value = mock_response

        service = OrderService(mock_http, mock_auth)
        result = await service.get_delivered(limit=10, offset=5)

        assert len(result) == 2


class TestDeliveryService:
    """Tests for DeliveryService."""

    def test_delivery_service_initialization(self, mock_http, mock_auth):
        """Test DeliveryService initializes correctly."""
        service = DeliveryService(mock_http, mock_auth)
        assert isinstance(service, BaseService)

    @pytest.mark.asyncio
    async def test_get_next_slots_uses_auth_ids(self, mock_http, mock_auth):
        """Test get_next_slots uses user_id and address_id from auth."""
        mock_response = MagicMock()
        mock_response.json.return_value = {"slots": []}
        mock_response.raise_for_status = MagicMock()
        mock_http.get.return_value = mock_response

        service = DeliveryService(mock_http, mock_auth)
        await service.get_next_slots()

        # Verify the URL contains the auth IDs
        call_args = mock_http.get.call_args
        url = call_args[0][0]
        assert "userId=12345" in url
        assert "addressId=67890" in url

    @pytest.mark.asyncio
    async def test_get_next_slots_returns_none_without_ids(self, mock_http, mock_auth):
        """Test get_next_slots returns None when IDs are missing."""
        mock_auth.user_id = None
        mock_auth.address_id = None

        service = DeliveryService(mock_http, mock_auth)
        result = await service.get_next_slots()

        assert result is None


class TestAccountService:
    """Tests for AccountService."""

    def test_account_service_initialization(self, mock_http, mock_auth):
        """Test AccountService initializes correctly."""
        service = AccountService(mock_http, mock_auth)
        assert isinstance(service, BaseService)

    @pytest.mark.asyncio
    async def test_get_shopping_list_requires_id(self, mock_http, mock_auth):
        """Test get_shopping_list raises ValueError without ID."""
        service = AccountService(mock_http, mock_auth)

        with pytest.raises(ValueError, match="Missing argument"):
            await service.get_shopping_list("")

    @pytest.mark.asyncio
    async def test_get_shopping_list_returns_formatted_data(self, mock_http, mock_auth):
        """Test get_shopping_list returns properly formatted data."""
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "name": "My List",
            "products": [{"productId": 123, "quantity": 2}]
        }
        mock_response.raise_for_status = MagicMock()
        mock_http.get.return_value = mock_response

        service = AccountService(mock_http, mock_auth)
        result = await service.get_shopping_list("list_123")

        assert result["name"] == "My List"
        assert len(result["products_in_list"]) == 1
