"""Tests for the service classes."""

from unittest.mock import AsyncMock, MagicMock

import pytest

from rohlik_api.auth import AuthManager
from rohlik_api.endpoints import Endpoints
from rohlik_api.http_client import HttpClient
from rohlik_api.services import (
    AccountService,
    BaseService,
    CartService,
    DeliveryService,
    OrderService,
    ProductService,
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

    async def test_get_content_calls_auth(self, mock_http, mock_auth):
        """Test get_content ensures logged in."""
        mock_response = MagicMock()
        mock_response.json.return_value = {"data": {"items": {}, "totalPrice": 0}}
        mock_response.raise_for_status = MagicMock()
        mock_http.get.return_value = mock_response

        service = CartService(mock_http, mock_auth)
        await service.get_content()
        mock_auth.ensure_logged_in.assert_called()

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
                        "brand": "TestBrand",
                    }
                },
                "totalPrice": 99.90,
                "submitConditionPassed": True,
            }
        }
        mock_response.raise_for_status = MagicMock()
        mock_http.get.return_value = mock_response

        service = CartService(mock_http, mock_auth)
        result = await service.get_content()

        assert result.total_price == 99.90
        assert result.total_items == 1
        assert result.can_make_order is True
        assert len(result.products) == 1
        assert result.products[0].name == "Test Product"

    async def test_add_items_sends_correct_payload(self, mock_http, mock_auth):
        """Test add_items sends correct payload."""
        mock_response = MagicMock()
        mock_response.raise_for_status = MagicMock()
        mock_http.post.return_value = mock_response

        service = CartService(mock_http, mock_auth)
        products = [{"product_id": 123, "quantity": 2}]
        result = await service.add_items(products)

        assert 123 in result
        mock_http.post.assert_called()


class TestProductService:
    """Tests for ProductService."""

    def test_product_service_initialization(self, mock_http, mock_auth):
        """Test ProductService initializes correctly."""
        service = ProductService(mock_http, mock_auth)
        assert isinstance(service, BaseService)

    async def test_search_returns_empty_when_no_products(self, mock_http, mock_auth):
        """Test search returns empty results when no products found."""
        mock_response = MagicMock()
        mock_response.json.return_value = {"data": {"productList": []}}
        mock_response.raise_for_status = MagicMock()
        mock_http.get.return_value = mock_response

        service = ProductService(mock_http, mock_auth)
        result = await service.search("nonexistent")

        assert result is not None
        assert result.results == []

    async def test_search_returns_none_on_error(self, mock_http, mock_auth):
        """Test search returns None when the request fails."""
        import aiohttp

        mock_http.get.side_effect = aiohttp.ClientError("Connection failed")

        service = ProductService(mock_http, mock_auth)
        result = await service.search("test")

        assert result is None

    async def test_search_filters_promoted_products(self, mock_http, mock_auth):
        """Test search filters out promoted products."""
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "data": {
                "productList": [
                    {
                        "productId": 1,
                        "productName": "Regular",
                        "badge": [],
                        "price": {"full": 10, "currency": "Kč"},
                    },
                    {
                        "productId": 2,
                        "productName": "Promoted",
                        "badge": [{"slug": "promoted"}],
                        "price": {"full": 20, "currency": "Kč"},
                    },
                ]
            }
        }
        mock_response.raise_for_status = MagicMock()
        mock_http.get.return_value = mock_response

        service = ProductService(mock_http, mock_auth)
        result = await service.search("test")

        assert len(result.results) == 1
        assert result.results[0].name == "Regular"

    async def test_get_ai_summary_returns_data(self, mock_http, mock_auth):
        """Test get_ai_summary returns properly formatted data."""
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "productId": 1384964,
            "rating": "EMPTY",
            "title": "AI Souhrn",
            "content": "Tato vepřová panenka je skvělá volba.",
        }
        mock_response.raise_for_status = MagicMock()
        mock_http.get.return_value = mock_response

        service = ProductService(mock_http, mock_auth)
        result = await service.get_ai_summary(1384964)

        assert result is not None
        assert result.product_id == 1384964
        assert result.title == "AI Souhrn"
        assert "vepřová panenka" in result.content

    async def test_get_ai_summary_returns_none_on_error(self, mock_http, mock_auth):
        """Test get_ai_summary returns None on error."""
        import aiohttp

        mock_http.get.side_effect = aiohttp.ClientError("Connection failed")

        service = ProductService(mock_http, mock_auth)
        result = await service.get_ai_summary(1384964)

        assert result is None

    async def test_get_composition_returns_data(self, mock_http, mock_auth):
        """Test get_composition returns properly formatted data."""
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "productId": 1425155,
            "nutritionalValues": [
                {
                    "portion": "100 g",
                    "values": {
                        "energyKJ": {"amount": 1309.0, "unit": "kJ"},
                        "energyKCal": {"amount": 313.0, "unit": "kCal"},
                        "fats": {"amount": 4.3, "unit": "g"},
                        "saturatedFats": {"amount": 0.8, "unit": "g"},
                        "carbohydrates": {"amount": 38.0, "unit": "g"},
                        "sugars": {"amount": 0.4, "unit": "g"},
                        "protein": {"amount": 9.6, "unit": "g"},
                        "salt": {"amount": 1.9, "unit": "g"},
                        "fiber": {"amount": 0.0, "unit": "g"},
                    },
                }
            ],
            "plainIngredients": "PŠENIČNÁ mouka, voda, sůl",
            "allergens": {
                "contained": ["Obiloviny obsahující lepek"],
                "possiblyContained": ["Vejce", "Mléko"],
            },
        }
        mock_response.raise_for_status = MagicMock()
        mock_http.get.return_value = mock_response

        service = ProductService(mock_http, mock_auth)
        result = await service.get_composition(1425155)

        assert result is not None
        assert result.product_id == 1425155
        assert len(result.nutritional_values) == 1
        assert result.nutritional_values[0].energy_kcal == 313.0
        assert result.nutritional_values[0].protein == 9.6
        assert "PŠENIČNÁ mouka" in result.ingredients
        assert "Obiloviny obsahující lepek" in result.allergens.contained
        assert "Mléko" in result.allergens.possibly_contained

    async def test_get_composition_returns_none_on_error(self, mock_http, mock_auth):
        """Test get_composition returns None on error."""
        import aiohttp

        mock_http.get.side_effect = aiohttp.ClientError("Connection failed")

        service = ProductService(mock_http, mock_auth)
        result = await service.get_composition(1425155)

        assert result is None

    async def test_get_price_returns_data(self, mock_http, mock_auth):
        """Test get_price returns properly formatted data."""
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "productId": 1425155,
            "price": {"amount": 40.9, "currency": "CZK"},
            "pricePerUnit": {"amount": 340.83, "currency": "CZK"},
            "sales": [],
        }
        mock_response.raise_for_status = MagicMock()
        mock_http.get.return_value = mock_response

        service = ProductService(mock_http, mock_auth)
        result = await service.get_price(1425155)

        assert result is not None
        assert result.product_id == 1425155
        assert result.price == 40.9
        assert result.currency == "CZK"
        assert result.price_per_unit == 340.83
        assert result.sales == []

    async def test_get_price_returns_none_on_error(self, mock_http, mock_auth):
        """Test get_price returns None on error."""
        import aiohttp

        mock_http.get.side_effect = aiohttp.ClientError("Connection failed")

        service = ProductService(mock_http, mock_auth)
        result = await service.get_price(1425155)

        assert result is None

    async def test_get_detail_returns_data(self, mock_http, mock_auth):
        """Test get_detail returns the raw product detail."""
        mock_response = MagicMock()
        mock_response.json.return_value = {"id": 123, "brand": "TestBrand"}
        mock_response.raise_for_status = MagicMock()
        mock_response.status = 200
        mock_http.get.return_value = mock_response

        service = ProductService(mock_http, mock_auth)
        result = await service.get_detail(123)

        assert result["brand"] == "TestBrand"

    async def test_get_detail_returns_none_on_404(self, mock_http, mock_auth):
        """Test get_detail returns None for a discontinued product."""
        mock_response = MagicMock()
        mock_response.status = 404
        mock_response.raise_for_status = MagicMock()
        mock_http.get.return_value = mock_response

        service = ProductService(mock_http, mock_auth)
        result = await service.get_detail(123)

        assert result is None

    # Trimmed real payload from /api/v1/products/card: one regular, one on sale.
    _CARDS = [
        {
            "productId": 1353975,
            "name": "Kachní prso Mulard",
            "brand": None,
            "unit": "kg",
            "textualAmount": "cca 420 g",
            "prices": {
                "originalPrice": 293.68,
                "salePrice": None,
                "unitPrice": 699.9,
                "saleValidTill": None,
                "currency": "CZK",
            },
            "stock": {"availabilityStatus": "AVAILABLE"},
        },
        {
            "productId": 1476819,
            "name": "Amadori BIO Kuřecí prsní plátky innerfilet",
            "brand": None,
            "unit": "kg",
            "textualAmount": "cca 400 g",
            "prices": {
                "originalPrice": 321.24,
                "salePrice": 273.05,
                "unitPrice": 679.91,
                "saleValidTill": "2026-07-30T23:59:00+02:00",
                "currency": "CZK",
            },
            "stock": {"availabilityStatus": "AVAILABLE"},
        },
    ]

    async def test_get_cards_parses_and_preserves_request_order(self, mock_http, mock_auth):
        """get_cards maps the card payload and returns it in the requested order."""
        resp = MagicMock()
        resp.json.return_value = list(reversed(self._CARDS))  # API order differs
        resp.raise_for_status = MagicMock()
        mock_http.get.return_value = resp

        service = ProductService(mock_http, mock_auth)
        result = await service.get_cards([1353975, 1476819])

        assert [c.id for c in result] == [1353975, 1476819]
        regular, sale = result
        assert regular.on_sale is False
        assert regular.price == 293.68
        assert regular.amount == "cca 420 g"
        assert regular.in_stock is True
        assert sale.on_sale is True
        assert sale.price == 273.05  # current price is the sale price
        assert sale.original_price == 321.24
        assert sale.currency == "CZK"
        url = mock_http.get.call_args[0][0]
        assert "/api/v1/products/card?" in url
        assert "products=1353975" in url and "categoryType=normal" in url

    async def test_get_cards_empty_makes_no_request(self, mock_http, mock_auth):
        """get_cards short-circuits on an empty id list."""
        service = ProductService(mock_http, mock_auth)
        assert await service.get_cards([]) == []
        mock_http.get.assert_not_called()

    async def test_get_week_sales_enriches_ids(self, mock_http, mock_auth):
        """get_week_sales resolves the deal ids then enriches them via get_cards."""
        sales_resp = MagicMock()
        sales_resp.json.return_value = {"products": [1353975, 1476819]}
        sales_resp.raise_for_status = MagicMock()
        cards_resp = MagicMock()
        cards_resp.json.return_value = self._CARDS
        cards_resp.raise_for_status = MagicMock()
        mock_http.get.side_effect = [sales_resp, cards_resp]

        service = ProductService(mock_http, mock_auth)
        result = await service.get_week_sales(size=2)

        assert [c.id for c in result] == [1353975, 1476819]
        assert result[1].on_sale is True
        assert "week-sales" in mock_http.get.call_args_list[0][0][0]
        assert "/api/v1/products/card?" in mock_http.get.call_args_list[1][0][0]

    async def test_get_week_sales_empty_when_no_products(self, mock_http, mock_auth):
        """get_week_sales returns [] (no card request) when there are no deals."""
        resp = MagicMock()
        resp.json.return_value = {"products": []}
        resp.raise_for_status = MagicMock()
        mock_http.get.return_value = resp

        service = ProductService(mock_http, mock_auth)
        assert await service.get_week_sales() == []
        assert mock_http.get.call_count == 1  # only the week-sales call

    async def test_get_categories_returns_hierarchy(self, mock_http, mock_auth):
        """Test get_categories returns the inner category list."""
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "categories": [{"level": 0, "name": "Food"}, {"level": 1, "name": "Dairy"}]
        }
        mock_response.raise_for_status = MagicMock()
        mock_response.status = 200
        mock_http.get.return_value = mock_response

        service = ProductService(mock_http, mock_auth)
        result = await service.get_categories(123)

        assert [c["name"] for c in result] == ["Food", "Dairy"]

    async def test_get_categories_returns_none_on_404(self, mock_http, mock_auth):
        """Test get_categories returns None for a discontinued product."""
        mock_response = MagicMock()
        mock_response.status = 404
        mock_response.raise_for_status = MagicMock()
        mock_http.get.return_value = mock_response

        service = ProductService(mock_http, mock_auth)
        result = await service.get_categories(123)

        assert result is None


class TestOrderService:
    """Tests for OrderService."""

    def test_order_service_initialization(self, mock_http, mock_auth):
        """Test OrderService initializes correctly."""
        service = OrderService(mock_http, mock_auth)
        assert isinstance(service, BaseService)

    async def test_get_next_returns_data(self, mock_http, mock_auth):
        """Test get_next returns order data."""
        mock_response = MagicMock()
        mock_response.json.return_value = {"order_id": 123}
        mock_response.raise_for_status = MagicMock()
        mock_http.get.return_value = mock_response

        service = OrderService(mock_http, mock_auth)
        result = await service.get_next()

        assert result == {"order_id": 123}

    async def test_get_delivered_with_pagination(self, mock_http, mock_auth):
        """Test get_delivered accepts pagination parameters."""
        mock_response = MagicMock()
        mock_response.json.return_value = [{"order_id": 1}, {"order_id": 2}]
        mock_response.raise_for_status = MagicMock()
        mock_http.get.return_value = mock_response

        service = OrderService(mock_http, mock_auth)
        result = await service.get_delivered(limit=10, offset=5)

        assert len(result) == 2

    async def test_get_all_delivered_paginates(self, mock_http, mock_auth):
        """Test get_all_delivered walks pages until a short page ends it."""
        page1 = MagicMock()
        page1.json.return_value = [{"id": 1}, {"id": 2}]
        page1.raise_for_status = MagicMock()
        page1.status = 200
        page2 = MagicMock()
        page2.json.return_value = [{"id": 3}]
        page2.raise_for_status = MagicMock()
        page2.status = 200
        mock_http.get.side_effect = [page1, page2]

        service = OrderService(mock_http, mock_auth)
        result = await service.get_all_delivered(page_size=2)

        assert [o["id"] for o in result] == [1, 2, 3]
        assert mock_http.get.call_count == 2

    async def test_get_detail_returns_data(self, mock_http, mock_auth):
        """Test get_detail returns the order detail."""
        mock_response = MagicMock()
        mock_response.json.return_value = {"id": 42, "items": [{"name": "Milk"}]}
        mock_response.raise_for_status = MagicMock()
        mock_response.status = 200
        mock_http.get.return_value = mock_response

        service = OrderService(mock_http, mock_auth)
        result = await service.get_detail(42)

        assert result["id"] == 42
        assert result["items"][0]["name"] == "Milk"

    async def test_get_detail_returns_none_on_404(self, mock_http, mock_auth):
        """Test get_detail returns None when the order does not exist."""
        mock_response = MagicMock()
        mock_response.status = 404
        mock_response.raise_for_status = MagicMock()
        mock_http.get.return_value = mock_response

        service = OrderService(mock_http, mock_auth)
        result = await service.get_detail(999)

        assert result is None
        mock_response.raise_for_status.assert_not_called()


class TestDeliveryService:
    """Tests for DeliveryService."""

    def test_delivery_service_initialization(self, mock_http, mock_auth):
        """Test DeliveryService initializes correctly."""
        service = DeliveryService(mock_http, mock_auth)
        assert isinstance(service, BaseService)

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

    async def test_get_next_slots_returns_none_without_ids(self, mock_http, mock_auth):
        """Test get_next_slots returns None when IDs are missing."""
        mock_auth.user_id = None
        mock_auth.address_id = None
        # The address list also yields nothing, so no address can be resolved.
        empty = MagicMock()
        empty.json.return_value = {"status": 200, "data": []}
        empty.raise_for_status = MagicMock()
        mock_http.get.return_value = empty

        service = DeliveryService(mock_http, mock_auth)
        result = await service.get_next_slots()

        assert result is None

    # Real (anonymised) payload shape from /delivery-address/list.
    _ADDRESS_LIST = {
        "status": 200,
        "messages": [],
        "data": [
            {"address": {"id": 11723996, "isDeliveredTo": True}, "store": {"storeId": 8799}},
            {"address": {"id": 5436937, "isDeliveredTo": True}, "store": {"storeId": 8799}},
        ],
    }

    async def test_get_addresses_returns_envelope(self, mock_http, mock_auth):
        """get_addresses returns the delivery-address list envelope."""
        resp = MagicMock()
        resp.json.return_value = self._ADDRESS_LIST
        resp.raise_for_status = MagicMock()
        mock_http.get.return_value = resp

        service = DeliveryService(mock_http, mock_auth)
        result = await service.get_addresses()

        assert result["data"][0]["address"]["id"] == 11723996
        assert mock_http.get.call_args[0][0] == Endpoints.DELIVERY_ADDRESS_LIST

    async def test_get_active_address_id_prefers_delivered_to(self, mock_http, mock_auth):
        """get_active_address_id returns the first isDeliveredTo address id."""
        resp = MagicMock()
        resp.json.return_value = {
            "data": [
                {"address": {"id": 1, "isDeliveredTo": False}},
                {"address": {"id": 22, "isDeliveredTo": True}},
            ]
        }
        resp.raise_for_status = MagicMock()
        mock_http.get.return_value = resp

        service = DeliveryService(mock_http, mock_auth)
        assert await service.get_active_address_id() == 22

    async def test_get_next_slots_resolves_address_from_list(self, mock_http, mock_auth):
        """When login lacks an address, get_next_slots resolves it from the list."""
        mock_auth.address_id = None  # login did not provide one

        address_resp = MagicMock()
        address_resp.json.return_value = self._ADDRESS_LIST
        address_resp.raise_for_status = MagicMock()
        slots_resp = MagicMock()
        slots_resp.json.return_value = {"slots": ["x"]}
        slots_resp.raise_for_status = MagicMock()
        # First GET resolves the address list, second GET fetches the slots.
        mock_http.get.side_effect = [address_resp, slots_resp]

        service = DeliveryService(mock_http, mock_auth)
        result = await service.get_next_slots()

        assert result == {"slots": ["x"]}
        slots_url = mock_http.get.call_args_list[1][0][0]
        assert "userId=12345" in slots_url
        assert "addressId=11723996" in slots_url
        # the resolved id is cached back on the auth manager
        assert mock_auth.address_id == 11723996


class TestAccountService:
    """Tests for AccountService."""

    def test_account_service_initialization(self, mock_http, mock_auth):
        """Test AccountService initializes correctly."""
        service = AccountService(mock_http, mock_auth)
        assert isinstance(service, BaseService)

    async def test_get_shopping_list_requires_id(self, mock_http, mock_auth):
        """Test get_shopping_list raises ValueError without ID."""
        service = AccountService(mock_http, mock_auth)

        with pytest.raises(ValueError, match="Missing argument"):
            await service.get_shopping_list("")

    async def test_get_shopping_list_returns_formatted_data(self, mock_http, mock_auth):
        """Test get_shopping_list returns properly formatted data."""
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "name": "My List",
            "products": [{"productId": 123, "quantity": 2}],
        }
        mock_response.raise_for_status = MagicMock()
        mock_http.get.return_value = mock_response

        service = AccountService(mock_http, mock_auth)
        result = await service.get_shopping_list("list_123")

        assert result.name == "My List"
        assert len(result.products_in_list) == 1
