"""Tests for favourite products and delivery slots (invented sample data)."""

from unittest.mock import AsyncMock, MagicMock

import aiohttp
import pytest

from rohlik_api.auth import AuthManager
from rohlik_api.endpoints import Endpoints
from rohlik_api.http_client import HttpClient
from rohlik_api.models import DeliverySlot, ProductCard
from rohlik_api.services import DeliveryService, ProductService
from rohlik_api.services.products import FAVOURITES_PAGE_SIZE


@pytest.fixture
def mock_http():
    http = MagicMock(spec=HttpClient)
    http.get = AsyncMock()
    return http


@pytest.fixture
def mock_auth():
    auth = MagicMock(spec=AuthManager)
    auth.ensure_logged_in = AsyncMock()
    auth.is_logged_in = True
    auth.user_id = 1
    auth.address_id = 2
    return auth


def _resp(payload):
    resp = MagicMock()
    resp.json.return_value = payload
    resp.raise_for_status = MagicMock()
    return resp


def _card(pid, name="Testprodukt", path="/images/grocery/products/1/1-2.jpg"):
    return {
        "productId": pid,
        "name": name,
        "textualAmount": "1 l",
        "unit": "l",
        "image": {"path": path},
        "prices": {"originalPrice": 1.5, "currency": "EUR"},
        "stock": {"availabilityStatus": "AVAILABLE"},
    }


# --- endpoints -------------------------------------------------------------


def test_favourite_products_endpoint():
    url = Endpoints.favourite_products(page=2, size=50)
    assert url.startswith("/api/v1/categories/favorite/products?")
    assert "page=2" in url and "size=50" in url and "sort=recommended" in url


# --- ProductCard image -----------------------------------------------------


def test_product_card_image_from_image_path():
    card = ProductCard.from_api(_card(1), "https://cdn.example.test")
    assert card.image == "https://cdn.example.test/images/grocery/products/1/1-2.jpg"


def test_product_card_image_absolute_and_imgpath_fallback():
    assert ProductCard.from_api(_card(1, path="https://img.test/a.jpg")).image == (
        "https://img.test/a.jpg"
    )
    data = _card(1)
    data.pop("image")
    data["imgPath"] = "//img.test/b.jpg"
    assert ProductCard.from_api(data).image == "https://img.test/b.jpg"


def test_product_card_without_image():
    data = _card(1)
    data.pop("image")
    assert ProductCard.from_api(data, "https://cdn.example.test").image is None


# --- favourites ------------------------------------------------------------


async def test_get_favourite_ids_skips_ads_and_duplicates(mock_http, mock_auth):
    mock_http.get.return_value = _resp(
        {"productIds": [5, 6, 7, 5], "interactiveProductCardAds": [{"productId": 6}]}
    )
    ids = await ProductService(mock_http, mock_auth).get_favourite_ids()
    assert ids == [5, 7]
    assert mock_http.get.call_count == 1


async def test_get_favourite_ids_pages_until_short_page(mock_http, mock_auth):
    full = list(range(1, FAVOURITES_PAGE_SIZE + 1))
    mock_http.get.side_effect = [_resp({"productIds": full}), _resp({"productIds": [999]})]
    ids = await ProductService(mock_http, mock_auth).get_favourite_ids()
    assert ids == full + [999]
    assert "page=1" in mock_http.get.call_args_list[1][0][0]


async def test_get_favourite_ids_accepts_data_envelope(mock_http, mock_auth):
    mock_http.get.return_value = _resp({"status": 200, "data": {"productIds": [3]}})
    assert await ProductService(mock_http, mock_auth).get_favourite_ids() == [3]


async def test_get_favourite_ids_none_on_first_page_error(mock_http, mock_auth):
    mock_http.get.side_effect = aiohttp.ClientError("down")
    assert await ProductService(mock_http, mock_auth).get_favourite_ids() is None


async def test_get_favourite_ids_none_on_unexpected_shape(mock_http, mock_auth):
    mock_http.get.return_value = _resp({"unexpected": True})
    assert await ProductService(mock_http, mock_auth).get_favourite_ids() is None


async def test_get_favourite_ids_keeps_collected_on_later_error(mock_http, mock_auth):
    full = list(range(1, FAVOURITES_PAGE_SIZE + 1))
    mock_http.get.side_effect = [_resp({"productIds": full}), aiohttp.ClientError("down")]
    assert await ProductService(mock_http, mock_auth).get_favourite_ids() == full


async def test_get_favourites_loads_cards_with_images(mock_http, mock_auth):
    mock_http.get.side_effect = [
        _resp({"productIds": [11, 12]}),
        _resp([_card(12, "Zwei"), _card(11, "Eins")]),
    ]
    service = ProductService(mock_http, mock_auth)
    service._cdn_url = "https://cdn.example.test"
    cards = await service.get_favourites()
    assert [c.name for c in cards] == ["Eins", "Zwei"]
    assert cards[0].image.startswith("https://cdn.example.test/")
    assert "categoryType=favorite" in mock_http.get.call_args_list[1][0][0]


async def test_get_favourites_chunks_card_requests(mock_http, mock_auth):
    ids = list(range(1, FAVOURITES_PAGE_SIZE + 6))
    mock_http.get.side_effect = [
        _resp({"productIds": ids[:FAVOURITES_PAGE_SIZE]}),
        _resp({"productIds": ids[FAVOURITES_PAGE_SIZE:]}),
        _resp([_card(i) for i in ids[:FAVOURITES_PAGE_SIZE]]),
        _resp([_card(i) for i in ids[FAVOURITES_PAGE_SIZE:]]),
    ]
    cards = await ProductService(mock_http, mock_auth).get_favourites()
    assert [c.id for c in cards] == ids
    assert mock_http.get.call_count == 4


async def test_get_favourites_empty(mock_http, mock_auth):
    mock_http.get.return_value = _resp({"productIds": []})
    assert await ProductService(mock_http, mock_auth).get_favourites() == []
    assert mock_http.get.call_count == 1


async def test_get_favourites_none_when_cards_fail(mock_http, mock_auth):
    mock_http.get.side_effect = [_resp({"productIds": [1]}), aiohttp.ClientError("down")]
    assert await ProductService(mock_http, mock_auth).get_favourites() is None


# --- delivery slots --------------------------------------------------------


def _slot(sid, typ, since, till, free, premium=False, msg="Frei", window=""):
    return {
        "slotId": sid,
        "type": typ,
        "premium": premium,
        "eco": False,
        "timeSlotCapacityDTO": {"totalFreeCapacityPercent": free, "capacityMessage": msg},
        "timeSlotReservationDTO": {"enabled": True, "duration": 60},
        "price": 0,
        "interval": {"since": since, "till": till},
        "timeWindow": window,
    }


SLOTS = {
    "status": 200,
    "data": {
        "availabilityDays": [
            {
                "date": "2030-01-02",
                "label": "Morgen",
                "slots": {
                    "10": [
                        _slot(
                            2,
                            "ON_TIME",
                            "2030-01-02T10:15:01+01:00",
                            "2030-01-02T10:30:00+01:00",
                            0,
                            True,
                            "Ausgebucht",
                        ),
                        _slot(
                            1,
                            "VIRTUAL",
                            "2030-01-02T10:00:00+01:00",
                            "2030-01-02T11:00:00+01:00",
                            40,
                            window="10:00 – 11:00",
                        ),
                        _slot(
                            3,
                            "ON_TIME",
                            "2030-01-02T10:00:01+01:00",
                            "2030-01-02T10:15:00+01:00",
                            30,
                            True,
                        ),
                    ]
                },
            },
            {"date": "2030-01-03", "label": "Do.", "slots": {}},
        ]
    },
}


def test_delivery_slot_list_from_api():
    slots = DeliverySlot.list_from_api(SLOTS)
    assert [s.id for s in slots] == [1, 3, 2]
    hour = slots[0]
    assert (hour.minutes, hour.free_percent, hour.available, hour.window) == (
        60,
        40,
        True,
        "10:00 – 11:00",
    )
    assert hour.date == "2030-01-02" and hour.day_label == "Morgen"
    assert slots[1].minutes == 15 and slots[1].premium is True
    assert slots[2].available is False and slots[2].capacity_message == "Ausgebucht"
    assert hour.reservable is True


@pytest.mark.parametrize("payload", [None, {}, {"data": None}, {"data": {"availabilityDays": 5}}])
def test_delivery_slot_list_from_api_malformed(payload):
    assert DeliverySlot.list_from_api(payload) == []


def test_delivery_slot_bad_capacity_is_zero():
    slot = DeliverySlot.from_api(
        {"type": "VIRTUAL", "timeSlotCapacityDTO": {"totalFreeCapacityPercent": "x"}}
    )
    assert slot.free_percent == 0 and slot.available is False


async def test_get_slots_parses_next_slots(mock_http, mock_auth):
    service = DeliveryService(mock_http, mock_auth)
    service.get_next_slots = AsyncMock(return_value=SLOTS)
    slots = await service.get_slots()
    assert len(slots) == 3


async def test_get_slots_none_on_failure(mock_http, mock_auth):
    service = DeliveryService(mock_http, mock_auth)
    service.get_next_slots = AsyncMock(return_value=None)
    assert await service.get_slots() is None
