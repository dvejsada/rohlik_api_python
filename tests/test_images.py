"""Tests for product images and order line items.

The payloads below are constructed, not recorded: they use the field names the
existing code already reads (``productName``, ``orderFieldId``, ``priceComposition``
and so on) plus ``imgPath``. Product names and IDs are made up.
"""

from unittest.mock import AsyncMock, MagicMock

import pytest

import rohlik_api
from rohlik_api import SITES, OrderItem, cdn_url_for, image_url
from rohlik_api.auth import AuthManager
from rohlik_api.http_client import HttpClient
from rohlik_api.models import Cart, CartItem, ProductSearchResult
from rohlik_api.services import CartService, OrderService, ProductService

GURKERL = SITES["at"].base_url
IMG = "/images/grocery/products/1001/1001-1700000000000.jpg"
IMG_URL = "https://cdn.gurkerl.at" + IMG


@pytest.fixture
def mock_auth():
    auth = MagicMock(spec=AuthManager)
    auth.ensure_logged_in = AsyncMock()
    return auth


def make_http(payload, base_url=GURKERL, status=200):
    """A mocked HttpClient for ``base_url`` whose GET returns ``payload``."""
    http = MagicMock(spec=HttpClient)
    http.base_url = base_url
    response = MagicMock()
    response.status = status
    response.json.return_value = payload
    response.raise_for_status = MagicMock()
    http.get = AsyncMock(return_value=response)
    return http


# ---------------------------------------------------------------------------
# image_url / cdn_url_for
# ---------------------------------------------------------------------------


class TestImageUrl:
    def test_relative_path_is_joined_onto_cdn(self):
        assert image_url(IMG, "https://cdn.gurkerl.at") == IMG_URL

    def test_slashes_are_not_doubled(self):
        assert image_url("images/a.jpg", "https://cdn.gurkerl.at/") == (
            "https://cdn.gurkerl.at/images/a.jpg"
        )

    def test_absolute_url_is_kept(self):
        assert image_url(IMG_URL, "https://cdn.rohlik.cz") == IMG_URL

    def test_protocol_relative_url_gets_https(self):
        assert image_url("//cdn.gurkerl.at/x.jpg") == "https://cdn.gurkerl.at/x.jpg"

    @pytest.mark.parametrize("value", [None, "", "   ", 123, {"path": IMG}])
    def test_missing_or_invalid_path_gives_none(self, value):
        assert image_url(value, "https://cdn.gurkerl.at") is None

    def test_relative_path_without_cdn_gives_none(self):
        assert image_url(IMG, "") is None


class TestCdnUrl:
    def test_every_site_has_a_cdn(self):
        for site in SITES.values():
            assert site.cdn_url.startswith("https://cdn.")
            assert not site.cdn_url.endswith("/")

    def test_known_hosts(self):
        assert cdn_url_for("https://www.gurkerl.at") == "https://cdn.gurkerl.at"
        assert cdn_url_for("https://www.rohlik.cz/") == "https://cdn.rohlik.cz"

    def test_unknown_shop_follows_pattern(self):
        assert cdn_url_for("https://www.example.test") == "https://cdn.example.test"

    def test_exported(self):
        for name in ("image_url", "cdn_url_for", "OrderItem"):
            assert name in rohlik_api.__all__


# ---------------------------------------------------------------------------
# Models
# ---------------------------------------------------------------------------


class TestModelImages:
    def test_search_result_image(self):
        result = ProductSearchResult.from_api(
            {"productId": 1001, "productName": "Testmilch", "imgPath": IMG},
            "https://cdn.gurkerl.at",
        )
        assert result.image == IMG_URL

    def test_search_result_without_image(self):
        result = ProductSearchResult.from_api({"productId": 1001, "productName": "Testmilch"})
        assert result.image is None

    def test_cart_item_image(self):
        item = CartItem.from_api(
            "1001", {"productName": "Testmilch", "imgPath": IMG}, "https://cdn.gurkerl.at"
        )
        assert item.image == IMG_URL

    def test_cart_passes_cdn_to_items(self):
        cart = Cart.from_api(
            {"data": {"items": {"1001": {"productName": "Testmilch", "imgPath": IMG}}}},
            "https://cdn.gurkerl.at",
        )
        assert cart.products[0].image == IMG_URL

    def test_existing_callers_still_work(self):
        """Positional calls without ``cdn_url`` keep working (backwards compatible)."""
        item = CartItem.from_api("1", {"productName": "X"})
        assert item.image is None
        assert Cart.from_api({"data": {"items": {}}}).products == []


class TestOrderItem:
    PAYLOAD = {
        "id": 1001,
        "name": "Testmilch 3,5 %",
        "amount": 2,
        "textualAmount": "1 l",
        "priceComposition": {
            "total": {"amount": 3.58, "currency": "EUR"},
            "unit": {"amount": 1.79, "currency": "EUR"},
        },
        "imgPath": IMG,
    }

    def test_from_api(self):
        item = OrderItem.from_api(self.PAYLOAD, "https://cdn.gurkerl.at")
        assert item == OrderItem(
            id=1001,
            name="Testmilch 3,5 %",
            quantity=2,
            price=3.58,
            unit_price=1.79,
            textual_amount="1 l",
            currency="EUR",
            image=IMG_URL,
        )

    def test_defaults_for_missing_fields(self):
        item = OrderItem.from_api({})
        assert item.id is None
        assert item.name == ""
        assert item.quantity == 1
        assert item.price == 0
        assert item.unit_price == 0
        assert item.textual_amount == ""
        assert item.currency == ""
        assert item.image is None

    def test_null_price_composition(self):
        item = OrderItem.from_api({"name": "X", "priceComposition": None})
        assert item.price == 0


# ---------------------------------------------------------------------------
# Services
# ---------------------------------------------------------------------------


class TestServices:
    async def test_search_resolves_images_for_the_shop(self, mock_auth):
        http = make_http({"data": {"productList": [{"productId": 1, "imgPath": IMG}]}})
        results = await ProductService(http, mock_auth).search("milch")
        assert results is not None
        assert results.results[0].image == IMG_URL

    async def test_search_on_rohlik_uses_rohlik_cdn(self, mock_auth):
        http = make_http(
            {"data": {"productList": [{"productId": 1, "imgPath": IMG}]}},
            base_url=SITES["cz"].base_url,
        )
        results = await ProductService(http, mock_auth).search("mleko")
        assert results is not None
        assert results.results[0].image == "https://cdn.rohlik.cz" + IMG

    async def test_cart_resolves_images(self, mock_auth):
        http = make_http({"data": {"items": {"1": {"productName": "X", "imgPath": IMG}}}})
        cart = await CartService(http, mock_auth).get_content()
        assert cart.products[0].image == IMG_URL

    async def test_get_items(self, mock_auth):
        http = make_http({"id": 42, "items": [TestOrderItem.PAYLOAD, "junk"]})
        items = await OrderService(http, mock_auth).get_items(42)
        assert items is not None
        assert [i.name for i in items] == ["Testmilch 3,5 %"]
        assert items[0].image == IMG_URL
        assert http.get.call_args.args[0] == "/api/v3/orders/42"

    async def test_get_items_empty_order(self, mock_auth):
        http = make_http({"id": 42, "items": None})
        assert await OrderService(http, mock_auth).get_items(42) == []

    async def test_get_items_unknown_order(self, mock_auth):
        http = make_http({}, status=404)
        assert await OrderService(http, mock_auth).get_items(999) is None
