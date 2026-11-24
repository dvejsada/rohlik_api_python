"""Tests for delivery tracking: models, ETA resolution and the order service methods."""

import copy
import dataclasses
import json
import logging
from datetime import UTC, datetime
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock

import aiohttp
import pytest

from rohlik_api.auth import AuthManager
from rohlik_api.endpoints import Endpoints
from rohlik_api.errors import APIRequestFailedError, InvalidCredentialsError
from rohlik_api.http_client import HttpClient
from rohlik_api.models import (
    CourierPosition,
    DeliveryDestination,
    DeliveryTracking,
    NextDelivery,
    TrackingStatus,
    UpcomingOrder,
)
from rohlik_api.services import OrderService

FIXTURES = Path(__file__).parent / "fixtures" / "delivery_tracking"

SLOT_SINCE = datetime(2026, 11, 24, 12, 0, 1, tzinfo=UTC)
EARLY_FROM = datetime(2026, 11, 24, 11, 0, 1, tzinfo=UTC)


def load(name):
    """Load a fixture as fresh JSON data."""
    return json.loads((FIXTURES / name).read_text())


def tracking(name):
    """Parse a delivery-tracking fixture."""
    return DeliveryTracking.from_api(load(name))


def upcoming_order():
    """The single upcoming order fixture, parsed."""
    return UpcomingOrder.list_from_api(load("upcoming_one.json"))[0]


def response(body=None, status=200, json_error=None):
    """A mocked Response with a status, a JSON body and raise_for_status."""
    resp = MagicMock()
    resp.status = status
    if json_error is not None:
        resp.json.side_effect = json_error
    else:
        resp.json.return_value = body
    if status >= 400:
        resp.raise_for_status.side_effect = aiohttp.ClientResponseError(
            request_info=MagicMock(), history=(), status=status
        )
    else:
        resp.raise_for_status = MagicMock()
    return resp


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
    return auth


# ---------------------------------------------------------------------------
# DeliveryTracking parsing
# ---------------------------------------------------------------------------


class TestDeliveryTrackingParsing:
    def test_before_queue_has_no_progress_or_courier(self):
        t = tracking("before_queue.json")
        assert t.order_id == 1000000001
        assert t.progress is None
        assert t.courier_name is None
        assert t.status is None
        assert t.estimated_arrival is None
        assert t.stops_before is None
        assert not t.is_active and not t.has_arrived and not t.is_delivered
        assert t.slot_since == SLOT_SINCE
        assert t.slot_till == datetime(2026, 11, 24, 12, 15, tzinfo=UTC)
        assert t.slot_type == "ON_TIME"
        assert t.early_delivery_available is True
        assert t.early_delivery_requested is False
        assert t.early_delivery_allowed_from is None

    def test_in_queue_without_eta(self):
        t = tracking("in_queue_no_eta.json")
        assert t.status == TrackingStatus.IN_QUEUE
        assert t.is_active
        assert t.stops_before == 11
        assert t.estimated_arrival is None
        assert t.courier_name == "Courier"
        # Nanosecond timestamps are truncated to microseconds.
        assert t.progress.generated_at == datetime(2026, 11, 24, 8, 4, 54, 614157, tzinfo=UTC)

    def test_on_the_way_has_position(self):
        t = tracking("on_the_way.json")
        assert t.status == TrackingStatus.ON_THE_WAY
        assert t.stops_before == 0
        assert t.estimated_arrival == datetime(2026, 11, 24, 11, 46, 18, tzinfo=UTC)
        pos = t.progress.courier_position
        assert pos == CourierPosition(
            latitude=50.001,
            longitude=14.001,
            recorded_at=datetime(2026, 11, 24, 11, 40, 19, 886000, tzinfo=UTC),
        )
        assert t.progress.courier_location_stale is False

    @pytest.mark.parametrize("name", ["arrived.json", "handing_over.json"])
    def test_arrived_states(self, name):
        t = tracking(name)
        assert t.has_arrived
        assert t.is_active
        assert not t.is_delivered

    def test_delivered_keeps_eta_and_clears_stops(self):
        t = tracking("delivered.json")
        assert t.is_delivered
        assert not t.is_active
        assert not t.has_arrived
        assert t.stops_before is None
        assert t.estimated_arrival == datetime(2026, 11, 24, 11, 46, 18, tzinfo=UTC)
        assert t.progress.courier_position is None
        assert t.early_delivery_available is False

    def test_unknown_status_is_kept_and_counts_as_active(self):
        data = load("in_queue_eta.json")
        data["progress"]["deliveryStatus"] = "DELAYED"
        t = DeliveryTracking.from_api(data)
        assert t.status == "DELAYED"
        assert t.is_active
        assert not t.has_arrived

    @pytest.mark.parametrize("value", [True, "3", 2.5])
    def test_non_int_stops_become_none(self, value):
        data = load("in_queue_eta.json")
        data["progress"]["stopsBefore"] = value
        assert DeliveryTracking.from_api(data).stops_before is None

    @pytest.mark.parametrize(
        "position",
        [
            {"latitude": True, "longitude": 14.0},
            {"latitude": "50.0", "longitude": 14.0},
            {"latitude": 50.0},
            "50,14",
            None,
        ],
    )
    def test_incomplete_position_is_dropped(self, position):
        data = load("on_the_way.json")
        data["progress"]["courierPosition"] = position
        assert DeliveryTracking.from_api(data).progress.courier_position is None

    @pytest.mark.parametrize("data", [None, [], "x", {}, {"progress": "x", "courier": "x"}])
    def test_malformed_input_never_raises(self, data):
        t = DeliveryTracking.from_api(data)
        assert t.progress is None
        assert t.order_id is None
        assert t.courier_name is None
        assert t.destination is None

    def test_personal_data_is_not_kept(self):
        dumped = json.dumps(dataclasses.asdict(tracking("on_the_way.json")), default=str)
        assert "+420000000000" not in dumped
        assert "phoneNumber" not in dumped
        assert "encodedPolyline" not in dumped
        assert "photoUrl" not in dumped

    def test_repr_hides_courier_name_and_position(self):
        text = repr(tracking("on_the_way.json"))
        assert "Courier" not in text
        assert "50.001" not in text and "14.001" not in text
        assert "ON_THE_WAY" in text


class TestArrivalFloor:
    def test_slot_start_without_early_delivery(self):
        assert tracking("in_queue_eta.json").arrival_floor == SLOT_SINCE

    def test_allowed_from_with_early_delivery(self):
        assert tracking("in_queue_early.json").arrival_floor == EARLY_FROM

    def test_requested_without_allowed_from_falls_back_to_slot(self):
        data = load("in_queue_early.json")
        data["earlyDelivery"]["allowedFrom"] = None
        assert DeliveryTracking.from_api(data).arrival_floor == SLOT_SINCE

    def test_none_without_slot(self):
        data = load("in_queue_eta.json")
        data["deliverySlot"] = None
        assert DeliveryTracking.from_api(data).arrival_floor is None


# ---------------------------------------------------------------------------
# UpcomingOrder parsing
# ---------------------------------------------------------------------------


class TestUpcomingOrder:
    def test_parses_full_entry(self):
        order = upcoming_order()
        assert order.id == 1000000001
        assert order.slot_id == 1000001
        assert order.slot_type == "ON_TIME"
        assert order.slot_since == SLOT_SINCE  # +0100 parsed to the same instant
        assert order.items_count == 17
        assert order.items_total_quantity == 29
        assert order.total_price == 1097.64
        assert order.currency == "CZK"
        assert order.available_actions == ["NOTE_CHANGE"]
        assert order.order_time is not None and order.order_time.utcoffset() is not None

    def test_address_and_payment_are_not_kept(self):
        dumped = json.dumps(dataclasses.asdict(upcoming_order()), default=str)
        assert "Example Street" not in dumped
        assert "example.invalid" not in dumped

    @pytest.mark.parametrize("order_id", [None, True, "1000000001"])
    def test_entry_without_int_id_is_skipped(self, order_id):
        entry = load("upcoming_one.json")[0]
        entry["id"] = order_id
        assert UpcomingOrder.from_api(entry) is None
        assert UpcomingOrder.list_from_api([entry]) == []

    def test_missing_slot(self):
        entry = load("upcoming_one.json")[0]
        del entry["deliverySlot"]
        order = UpcomingOrder.from_api(entry)
        assert order.slot_since is None and order.slot_id is None

    def test_sorted_by_slot_across_offset_formats(self):
        # upcoming_two lists the 13:00+01:00 order before the 11:30Z (= 12:30+01:00) one.
        orders = UpcomingOrder.list_from_api(load("upcoming_two.json"))
        assert [o.id for o in orders] == [1000000002, 1000000001]

    def test_orders_without_slot_sort_last(self):
        first, second = load("upcoming_two.json")
        del first["deliverySlot"]
        orders = UpcomingOrder.list_from_api([first, second])
        assert [o.id for o in orders] == [1000000002, 1000000001]

    @pytest.mark.parametrize("data", [None, {}, "x", 1])
    def test_non_list_gives_empty(self, data):
        assert UpcomingOrder.list_from_api(data) == []

    def test_empty_list(self):
        assert UpcomingOrder.list_from_api(load("upcoming_empty.json")) == []


# ---------------------------------------------------------------------------
# NextDelivery.resolve
# ---------------------------------------------------------------------------


class TestNextDeliveryResolve:
    def test_queued_eta_before_slot_is_capped_to_slot_start(self):
        t = tracking("in_queue_eta.json")  # ETA 11:49:32Z, slot 12:00:01Z, not early
        result = NextDelivery.resolve(upcoming_order(), t)
        assert result.eta == SLOT_SINCE
        assert result.eta_capped is True
        assert result.eta_source == "tracking"
        assert result.status == TrackingStatus.IN_QUEUE
        assert t.estimated_arrival == datetime(2026, 11, 24, 11, 49, 32, tzinfo=UTC)

    def test_queued_with_early_delivery_uses_estimate_above_floor(self):
        t = tracking("in_queue_early.json")  # ETA 11:49:37Z, floor 11:00:01Z
        result = NextDelivery.resolve(upcoming_order(), t)
        assert result.eta == datetime(2026, 11, 24, 11, 49, 37, tzinfo=UTC)
        assert result.eta_capped is False

    def test_queued_with_early_delivery_capped_to_allowed_from(self):
        data = load("in_queue_early.json")
        data["progress"]["estimatedArrival"] = "2026-11-24T10:30:00Z"
        result = NextDelivery.resolve(upcoming_order(), DeliveryTracking.from_api(data))
        assert result.eta == EARLY_FROM
        assert result.eta_capped is True

    def test_queued_estimate_after_slot_is_used_as_is(self):
        data = load("in_queue_eta.json")
        data["progress"]["estimatedArrival"] = "2026-11-24T12:20:00Z"
        result = NextDelivery.resolve(upcoming_order(), DeliveryTracking.from_api(data))
        assert result.eta == datetime(2026, 11, 24, 12, 20, tzinfo=UTC)
        assert result.eta_capped is False

    @pytest.mark.parametrize(
        "name", ["on_the_way.json", "arrived.json", "handing_over.json", "delivered.json"]
    )
    def test_not_capped_once_on_the_way(self, name):
        # All have ETA 11:46:18Z; without early delivery the floor is the 12:00:01Z slot.
        data = load(name)
        data["earlyDelivery"] = {"available": True, "requested": False, "allowedFrom": None}
        t = DeliveryTracking.from_api(data)
        assert t.estimated_arrival < t.arrival_floor
        result = NextDelivery.resolve(upcoming_order(), t)
        assert result.eta == t.estimated_arrival
        assert result.eta_capped is False
        assert result.eta_source == "tracking"

    def test_tracking_without_estimate_falls_back_to_slot(self):
        result = NextDelivery.resolve(upcoming_order(), tracking("in_queue_no_eta.json"))
        assert result.eta == SLOT_SINCE
        assert result.eta_source == "slot"
        assert result.status == TrackingStatus.IN_QUEUE

    def test_no_tracking_falls_back_to_slot(self):
        result = NextDelivery.resolve(upcoming_order(), None)
        assert result.eta == SLOT_SINCE
        assert result.eta_source == "slot"
        assert result.status is None
        assert result.tracking is None

    def test_no_slot_and_no_tracking(self):
        entry = load("upcoming_one.json")[0]
        del entry["deliverySlot"]
        result = NextDelivery.resolve(UpcomingOrder.from_api(entry), None)
        assert result.eta is None and result.eta_source is None and result.eta_capped is False


# ---------------------------------------------------------------------------
# OrderService methods
# ---------------------------------------------------------------------------


class TestGetDeliveryTracking:
    async def test_returns_model(self, mock_http, mock_auth):
        mock_http.get.return_value = response(load("on_the_way.json"))
        result = await OrderService(mock_http, mock_auth).get_delivery_tracking(1000000001)
        assert isinstance(result, DeliveryTracking)
        assert result.status == TrackingStatus.ON_THE_WAY
        assert mock_http.get.call_args[0][0] == "/api/v2/orders/1000000001/delivery-tracking"
        mock_auth.ensure_logged_in.assert_awaited()

    async def test_404_returns_none_without_warning(self, mock_http, mock_auth, caplog):
        mock_http.get.return_value = response(load("not_found.json"), status=404)
        with caplog.at_level(logging.WARNING):
            result = await OrderService(mock_http, mock_auth).get_delivery_tracking(1)
        assert result is None
        assert caplog.records == []

    async def test_server_error_returns_none_with_warning(self, mock_http, mock_auth, caplog):
        mock_http.get.return_value = response(status=500)
        with caplog.at_level(logging.WARNING):
            result = await OrderService(mock_http, mock_auth).get_delivery_tracking(1)
        assert result is None
        assert any("delivery tracking" in r.getMessage() for r in caplog.records)

    @pytest.mark.parametrize("error", [aiohttp.ClientError("boom"), TimeoutError()])
    async def test_transport_error_returns_none(self, mock_http, mock_auth, error):
        mock_http.get.side_effect = error
        assert await OrderService(mock_http, mock_auth).get_delivery_tracking(1) is None

    async def test_invalid_json_returns_none(self, mock_http, mock_auth):
        mock_http.get.return_value = response(json_error=json.JSONDecodeError("bad", "", 0))
        assert await OrderService(mock_http, mock_auth).get_delivery_tracking(1) is None

    @pytest.mark.parametrize("body", [[], "x", None])
    async def test_non_dict_body_returns_none(self, mock_http, mock_auth, body):
        mock_http.get.return_value = response(body)
        assert await OrderService(mock_http, mock_auth).get_delivery_tracking(1) is None

    async def test_auth_failure_propagates(self, mock_http, mock_auth):
        mock_auth.ensure_logged_in.side_effect = InvalidCredentialsError("bad credentials")
        with pytest.raises(InvalidCredentialsError):
            await OrderService(mock_http, mock_auth).get_delivery_tracking(1)
        mock_http.get.assert_not_called()


class TestGetUpcoming:
    async def test_parses_and_sorts(self, mock_http, mock_auth):
        mock_http.get.return_value = response(load("upcoming_two.json"))
        result = await OrderService(mock_http, mock_auth).get_upcoming()
        assert [o.id for o in result] == [1000000002, 1000000001]
        assert mock_http.get.call_args[0][0] == Endpoints.NEXT_ORDER

    async def test_empty(self, mock_http, mock_auth):
        mock_http.get.return_value = response([])
        assert await OrderService(mock_http, mock_auth).get_upcoming() == []

    async def test_failure_returns_none(self, mock_http, mock_auth):
        mock_http.get.return_value = response(status=503)
        assert await OrderService(mock_http, mock_auth).get_upcoming() is None

    async def test_invalid_json_returns_none(self, mock_http, mock_auth):
        mock_http.get.return_value = response(json_error=ValueError("bad"))
        assert await OrderService(mock_http, mock_auth).get_upcoming() is None

    async def test_non_list_returns_none(self, mock_http, mock_auth):
        mock_http.get.return_value = response({"data": []})
        assert await OrderService(mock_http, mock_auth).get_upcoming() is None


class TestGetNextDelivery:
    async def test_no_upcoming_order_returns_none(self, mock_http, mock_auth):
        mock_http.get.return_value = response([])
        assert await OrderService(mock_http, mock_auth).get_next_delivery() is None
        assert mock_http.get.call_count == 1

    async def test_upcoming_failure_raises(self, mock_http, mock_auth):
        mock_http.get.return_value = response(status=500)
        with pytest.raises(APIRequestFailedError):
            await OrderService(mock_http, mock_auth).get_next_delivery()

    async def test_tracking_failure_raises(self, mock_http, mock_auth):
        mock_http.get.side_effect = [response(load("upcoming_one.json")), response(status=500)]
        with pytest.raises(APIRequestFailedError):
            await OrderService(mock_http, mock_auth).get_next_delivery()

    async def test_tracking_404_falls_back_to_slot(self, mock_http, mock_auth):
        mock_http.get.side_effect = [
            response(load("upcoming_one.json")),
            response(load("not_found.json"), status=404),
        ]
        result = await OrderService(mock_http, mock_auth).get_next_delivery()
        assert result.tracking is None
        assert result.eta == SLOT_SINCE
        assert result.eta_source == "slot"

    async def test_tracks_soonest_order(self, mock_http, mock_auth):
        on_the_way = load("on_the_way.json")
        on_the_way["orderId"] = 1000000002
        mock_http.get.side_effect = [response(load("upcoming_two.json")), response(on_the_way)]
        result = await OrderService(mock_http, mock_auth).get_next_delivery()
        assert result.order.id == 1000000002
        assert result.status == TrackingStatus.ON_THE_WAY
        assert result.eta == datetime(2026, 11, 24, 11, 46, 18, tzinfo=UTC)
        paths = [call.args[0] for call in mock_http.get.call_args_list]
        assert paths == [Endpoints.NEXT_ORDER, "/api/v2/orders/1000000002/delivery-tracking"]

    async def test_returns_capped_eta_while_queued(self, mock_http, mock_auth):
        mock_http.get.side_effect = [
            response(load("upcoming_one.json")),
            response(copy.deepcopy(load("in_queue_eta.json"))),
        ]
        result = await OrderService(mock_http, mock_auth).get_next_delivery()
        assert result.eta == SLOT_SINCE
        assert result.eta_capped is True


def test_endpoint_builder_coerces_to_int():
    assert Endpoints.delivery_tracking(42) == "/api/v2/orders/42/delivery-tracking"
    assert Endpoints.delivery_tracking("42") == "/api/v2/orders/42/delivery-tracking"


# ---------------------------------------------------------------------------
# Review follow-ups
# ---------------------------------------------------------------------------


class TestStrictParsing:
    @pytest.mark.parametrize("value", [10**400, float("nan"), float("inf"), -float("inf")])
    def test_non_finite_coordinates_are_dropped(self, value):
        data = load("on_the_way.json")
        data["progress"]["courierPosition"]["latitude"] = value
        assert DeliveryTracking.from_api(data).progress.courier_position is None

    def test_huge_price_does_not_raise(self):
        entry = load("upcoming_one.json")[0]
        entry["priceComposition"]["total"]["amount"] = 10**400
        assert UpcomingOrder.from_api(entry).total_price is None

    @pytest.mark.parametrize("value", ["true", 1, None])
    def test_non_bool_flags_become_none(self, value):
        data = load("on_the_way.json")
        data["earlyDelivery"]["available"] = value
        data["earlyDelivery"]["requested"] = value
        data["progress"]["courierLocationStale"] = value
        t = DeliveryTracking.from_api(data)
        assert t.early_delivery_available is None
        assert t.early_delivery_requested is None
        assert t.progress.courier_location_stale is None

    def test_non_numeric_price_and_odd_actions(self):
        entry = load("upcoming_one.json")[0]
        entry["priceComposition"]["total"]["amount"] = "1097.64"
        entry["availableActions"] = ["NOTE_CHANGE", 3, None, "REPEAT_ORDER"]
        order = UpcomingOrder.from_api(entry)
        assert order.total_price is None
        assert order.available_actions == ["NOTE_CHANGE", "REPEAT_ORDER"]

    def test_upcoming_slot_till(self):
        assert upcoming_order().slot_till == datetime(2026, 11, 24, 12, 15, tzinfo=UTC)

    def test_courier_position_repr_hides_coordinates(self):
        position = tracking("on_the_way.json").progress.courier_position
        assert "50.001" not in repr(position) and "14.001" not in repr(position)

    def test_allowed_from_ignored_when_not_requested(self):
        data = load("in_queue_eta.json")
        data["earlyDelivery"] = {
            "available": True,
            "requested": False,
            "allowedFrom": "2026-11-24T11:00:01Z",
        }
        assert DeliveryTracking.from_api(data).arrival_floor == SLOT_SINCE


class TestSortingByInstant:
    def test_sorts_by_absolute_time_not_wall_clock(self):
        # 12:15+01:00 is 11:15Z, i.e. before 11:30Z, although "12:15" > "11:30" on the wall.
        first, second = load("upcoming_two.json")
        first["deliverySlot"]["since"] = "2026-11-24T12:15:00.000+0100"
        orders = UpcomingOrder.list_from_api([second, first])
        assert [o.id for o in orders] == [1000000001, 1000000002]


class TestResolveConsistency:
    def test_tracking_for_another_order_is_rejected(self):
        data = load("in_queue_eta.json")
        data["orderId"] = 1000000002
        with pytest.raises(ValueError):
            NextDelivery.resolve(upcoming_order(), DeliveryTracking.from_api(data))

    def test_slot_fallback_uses_tracking_slot_when_order_has_none(self):
        entry = load("upcoming_one.json")[0]
        del entry["deliverySlot"]
        result = NextDelivery.resolve(
            UpcomingOrder.from_api(entry), tracking("in_queue_no_eta.json")
        )
        assert result.eta == SLOT_SINCE
        assert result.eta_source == "slot"

    def test_eta_moves_earlier_when_courier_sets_off_without_early_delivery(self):
        # Documented behaviour: the floor is lifted at ON_THE_WAY, so the ETA can drop.
        queued = NextDelivery.resolve(upcoming_order(), tracking("in_queue_eta.json"))
        data = load("on_the_way.json")
        data["earlyDelivery"] = {"available": True, "requested": False, "allowedFrom": None}
        on_the_way = NextDelivery.resolve(upcoming_order(), DeliveryTracking.from_api(data))
        assert queued.eta_capped and not on_the_way.eta_capped
        assert on_the_way.eta < queued.eta


class TestServiceFollowUps:
    async def test_raise_on_error(self, mock_http, mock_auth):
        mock_http.get.return_value = response(status=502)
        with pytest.raises(APIRequestFailedError):
            await OrderService(mock_http, mock_auth).get_delivery_tracking(1, raise_on_error=True)

    async def test_raise_on_error_still_returns_none_on_404(self, mock_http, mock_auth):
        mock_http.get.return_value = response(load("not_found.json"), status=404)
        service = OrderService(mock_http, mock_auth)
        assert await service.get_delivery_tracking(1, raise_on_error=True) is None

    @pytest.mark.parametrize("order_id", ["abc", None])
    async def test_invalid_order_id_raises(self, mock_http, mock_auth, order_id):
        with pytest.raises((TypeError, ValueError)):
            await OrderService(mock_http, mock_auth).get_delivery_tracking(order_id)
        mock_http.get.assert_not_called()

    async def test_invalid_json_logs_warning(self, mock_http, mock_auth, caplog):
        mock_http.get.return_value = response(json_error=ValueError("bad"))
        with caplog.at_level(logging.WARNING):
            await OrderService(mock_http, mock_auth).get_delivery_tracking(1)
        assert any("delivery tracking" in r.getMessage() for r in caplog.records)

    async def test_next_delivery_non_dict_tracking_raises(self, mock_http, mock_auth):
        mock_http.get.side_effect = [response(load("upcoming_one.json")), response([])]
        with pytest.raises(APIRequestFailedError):
            await OrderService(mock_http, mock_auth).get_next_delivery()

    async def test_next_delivery_auth_failure_propagates(self, mock_http, mock_auth):
        mock_auth.ensure_logged_in.side_effect = InvalidCredentialsError("bad credentials")
        with pytest.raises(InvalidCredentialsError):
            await OrderService(mock_http, mock_auth).get_next_delivery()

    async def test_get_upcoming_logs_in(self, mock_http, mock_auth):
        mock_http.get.return_value = response([])
        await OrderService(mock_http, mock_auth).get_upcoming()
        mock_auth.ensure_logged_in.assert_awaited_once()


# ---------------------------------------------------------------------------
# Second review follow-ups
# ---------------------------------------------------------------------------


class TestSecondReview:
    @pytest.mark.parametrize("order_id", [True, 12.9, "1_0", "-1", -1, "12a"])
    def test_endpoint_rejects_non_integer_ids(self, order_id):
        with pytest.raises((TypeError, ValueError)):
            Endpoints.delivery_tracking(order_id)

    def test_resolve_accepts_tracking_without_order_id(self):
        data = load("in_queue_eta.json")
        del data["orderId"]
        result = NextDelivery.resolve(upcoming_order(), DeliveryTracking.from_api(data))
        assert result.eta_source == "tracking"

    def test_order_slot_takes_precedence_over_tracking_slot(self):
        data = load("in_queue_no_eta.json")
        data["deliverySlot"]["since"] = "2026-11-24T15:00:00Z"
        result = NextDelivery.resolve(upcoming_order(), DeliveryTracking.from_api(data))
        assert result.eta == SLOT_SINCE

    def test_estimate_equal_to_floor_is_not_capped(self):
        data = load("in_queue_eta.json")
        data["progress"]["estimatedArrival"] = "2026-11-24T12:00:01Z"
        result = NextDelivery.resolve(upcoming_order(), DeliveryTracking.from_api(data))
        assert result.eta == SLOT_SINCE
        assert result.eta_capped is False

    def test_empty_courier_name_becomes_none(self):
        data = load("in_queue_eta.json")
        data["courier"]["displayName"] = ""
        assert DeliveryTracking.from_api(data).courier_name is None

    async def test_200_without_order_id_is_a_failure(self, mock_http, mock_auth, caplog):
        mock_http.get.return_value = response({"status": 200, "messages": []})
        service = OrderService(mock_http, mock_auth)
        with caplog.at_level(logging.WARNING):
            assert await service.get_delivery_tracking(1) is None
        assert any("delivery tracking" in r.getMessage() for r in caplog.records)
        mock_http.get.return_value = response({"status": 200, "messages": []})
        with pytest.raises(APIRequestFailedError):
            await service.get_delivery_tracking(1, raise_on_error=True)

    async def test_raised_error_chains_the_cause(self, mock_http, mock_auth):
        mock_http.get.side_effect = TimeoutError("slow")
        with pytest.raises(APIRequestFailedError) as excinfo:
            await OrderService(mock_http, mock_auth).get_delivery_tracking(1, raise_on_error=True)
        assert isinstance(excinfo.value.__cause__, TimeoutError)

    async def test_next_delivery_reports_mismatched_tracking_as_api_error(
        self, mock_http, mock_auth
    ):
        other = load("on_the_way.json")
        other["orderId"] = 1000000002
        mock_http.get.side_effect = [response(load("upcoming_one.json")), response(other)]
        with pytest.raises(APIRequestFailedError) as excinfo:
            await OrderService(mock_http, mock_auth).get_next_delivery()
        assert isinstance(excinfo.value.__cause__, ValueError)


class TestCourierLocation:
    def test_destination_is_parsed(self):
        t = tracking("before_queue.json")
        assert t.destination == DeliveryDestination(latitude=50.0, longitude=14.0)
        assert t.progress is None
        assert t.courier_position is None
        assert t.courier_distance is None

    @pytest.mark.parametrize(
        "coordinates",
        [
            {"latitude": 50.0},
            {"latitude": "50", "longitude": 14.0},
            {"latitude": True, "longitude": 14.0},
            {"latitude": float("nan"), "longitude": 14.0},
            {"latitude": 50.0, "longitude": float("inf")},
            {"latitude": 90.5, "longitude": 14.0},
            {"latitude": -91, "longitude": 14.0},
            {"latitude": 50.0, "longitude": 180.5},
            {"latitude": 500, "longitude": 1e6},
            {"latitude": 0, "longitude": 0},
            {"latitude": 0.0, "longitude": 0.0},
            "50,14",
            None,
        ],
    )
    def test_invalid_coordinates_are_dropped(self, coordinates):
        data = load("on_the_way.json")
        data["destination"] = coordinates
        data["progress"]["courierPosition"] = (
            {**coordinates, "recordedAt": "2026-11-24T11:40:19Z"}
            if isinstance(coordinates, dict)
            else coordinates
        )
        t = DeliveryTracking.from_api(data)
        assert t.destination is None
        assert t.courier_position is None
        assert t.courier_distance is None

    @pytest.mark.parametrize(
        "coordinates",
        [
            {"latitude": 50, "longitude": 14},
            {"latitude": 90, "longitude": 180},
            {"latitude": -90, "longitude": -180},
            {"latitude": 0, "longitude": 14.0},
        ],
    )
    def test_edge_and_integer_coordinates_are_kept(self, coordinates):
        data = load("on_the_way.json")
        data["destination"] = coordinates
        destination = DeliveryTracking.from_api(data).destination
        assert destination == DeliveryDestination(
            latitude=float(coordinates["latitude"]), longitude=float(coordinates["longitude"])
        )
        assert isinstance(destination.latitude, float)

    def test_missing_destination_keeps_position(self):
        data = load("on_the_way.json")
        del data["destination"]
        t = DeliveryTracking.from_api(data)
        assert t.destination is None
        assert t.courier_position is not None
        assert t.courier_distance is None

    def test_courier_distance_on_the_way(self):
        t = tracking("on_the_way.json")
        assert t.courier_position is t.progress.courier_position
        # 0.001° of latitude ≈ 111.2 m, 0.001° of longitude at 50° N ≈ 71.5 m.
        assert t.courier_distance == pytest.approx(132.2, abs=0.5)

    def test_courier_distance_ignores_staleness(self):
        """Documented: callers check courier_location_stale themselves."""
        data = load("on_the_way.json")
        data["progress"]["courierLocationStale"] = True
        t = DeliveryTracking.from_api(data)
        assert t.progress.courier_location_stale is True
        assert t.courier_distance == pytest.approx(132.2, abs=0.5)

    def test_distance_to_known_city_pair(self):
        prague = CourierPosition(latitude=50.0755, longitude=14.4378, recorded_at=None)
        brno = DeliveryDestination(latitude=49.1951, longitude=16.6068)
        assert prague.distance_to(brno) == pytest.approx(185_000, rel=0.01)

    def test_distance_to_same_point_is_zero(self):
        here = CourierPosition(latitude=50.0, longitude=14.0, recorded_at=None)
        assert here.distance_to(DeliveryDestination(latitude=50.0, longitude=14.0)) == 0.0

    def test_distance_to_antipode_is_half_the_circumference(self):
        here = CourierPosition(latitude=0.0, longitude=1.0, recorded_at=None)
        there = DeliveryDestination(latitude=0.0, longitude=-179.0)
        assert here.distance_to(there) == pytest.approx(20_015_000, rel=0.001)

    def test_distance_to_any_geo_point(self):
        @dataclasses.dataclass
        class Home:
            latitude: float
            longitude: float

        here = CourierPosition(latitude=50.001, longitude=14.0, recorded_at=None)
        assert here.distance_to(Home(50.0, 14.0)) == pytest.approx(111.2, abs=0.5)
        assert here.distance_to(here) == 0.0

    def test_destination_repr_hides_coordinates(self):
        t = tracking("on_the_way.json")
        assert repr(t.destination) == "DeliveryDestination()"
        assert repr(t.progress.courier_position).startswith("CourierPosition(recorded_at=")
        text = repr(t)
        assert "50.0" not in text and "14.0" not in text

    def test_asdict_includes_the_destination(self):
        """Contract: asdict() is not redacted, so consumers must redact it."""
        dumped = dataclasses.asdict(tracking("on_the_way.json"))
        assert dumped["destination"] == {"latitude": 50.0, "longitude": 14.0}
