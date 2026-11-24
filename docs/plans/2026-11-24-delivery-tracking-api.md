# Delivery tracking in rohlik-api — Implementation Plan (3.1–3.3)

**Goal:** Give every consumer of `rohlik-api` (Home Assistant, rohlik-mcp, scripts) a typed,
locale-independent view of a delivery in progress: status, ETA, stops ahead and courier
position. It is built on the delivery-tracking endpoint observed through one complete live
delivery on 2026-11-24 (see HA-RohlikCZ `docs/plans/2026-11-24-delivery-tracking-observations.md`).

**Scope:** three additive features. No existing method changes behaviour or shape.

| # | Feature | Requests |
| --- | --- | --- |
| 3.1 | `orders.get_delivery_tracking(order_id) -> DeliveryTracking \| None` | 1 |
| 3.2 | `orders.get_upcoming() -> list[UpcomingOrder] \| None` | 1 |
| 3.3 | `orders.get_next_delivery() -> NextDelivery \| None` | 2 (upcoming + tracking) |

Out of scope: the SSE stream, announcement changes, moving order detail to v4 and HA work.
`get_data()` is not extended.

---

## Endpoint facts this plan relies on (observed)

- `GET /api/v2/orders/{id}/delivery-tracking` returns 200 through the whole lifecycle with the
  web-login cookie session. An unknown ID returns 404 with `{status, messages[{messageCode,…}]}`.
- **Top level:** `orderId`, `deliverySlot{since, till, type}` (UTC `Z`), `destination{latitude,longitude}`,
  `courier{displayName, phoneNumber, photoUrl}`, `earlyDelivery{available, requested, allowedFrom}`,
  `progress`.
- **`progress`:**
  - It is `null` before the queue starts.
  - Then `{generatedAt, deliveryStatus, stopsBefore, estimatedArrival, courierLocationStale, courierPosition{latitude, longitude, recordedAt}, courierMovement{…}, routeToStop{…}}`.
- **Status:** `IN_QUEUE → ON_THE_WAY → ARRIVED → HANDING_OVER → DELIVERED`.
  - `estimatedArrival` may be null early in `IN_QUEUE`.
  - It is kept after `DELIVERED`.
  - `stopsBefore` becomes null at `DELIVERED`.
  - Position exists from `ON_THE_WAY` to `HANDING_OVER`.
- **`earlyDelivery`:** `allowedFrom` is `slot.since − 1 h` once `requested`. The shop's own texts show
  the slot start until early delivery is requested, even when the courier ETA is earlier.
- **Timestamp formats:** `2026-11-24T12:00:01Z`, `…19.886Z`, `…20.12272713Z` (9 fractional
  digits) and in upcoming orders `2026-11-24T13:00:01.000+0100`. All parse with
  `datetime.fromisoformat` on Python ≥ 3.13 (the package minimum), giving aware datetimes.
- **`/api/v3/orders/upcoming`:** returns `[]` with no order. The order drops out within 1 s of
  `DELIVERED`. Item keys: `id, itemsCount, itemsTotalQuantity, priceComposition.total{amount,currency},
  orderTime, deliverySlot{id,type,since,till}, address, payment, itemImages, availableActions,
  expressDeliveryPromise, pblLink, invoiceAwaitingPayment`.

---

## Design

### Naming

- `TrackingStatus` (`StrEnum`): constants for the five observed status values. The models keep
  the **raw string**, so a future value survives parsing.
- 3.3's result is named `NextDelivery`. That avoids a clash with `DeliveryStatus` and with the
  HA integration's own names.

### Datetime helper (`rohlik_api/helpers.py`)

```python
def parse_datetime(value: Any) -> datetime | None:
    """Parse an API timestamp into an aware datetime, or None.

    Accepts the formats the API uses (``Z``, ``+0100``, up to 9 fractional digits,
    truncated to microseconds by the stdlib). Returns None for None, non-strings,
    unparseable or offset-less (naive) values: callers never get a naive datetime.
    """
```

This is public, exported, and unit-tested against every observed format. Naive values become
`None` instead of guessing a timezone. None of the observed tracking or order timestamps is naive.

### Models (`rohlik_api/models.py`, new "Delivery tracking" section)

Plain `@dataclass(slots=True)` with `from_api`, like existing models. Parsing is defensive: every
level may be missing or `null`, wrong types become `None`, and parsing never raises.

```python
@dataclass(slots=True)
class Coordinates:
    latitude: float
    longitude: float

@dataclass(slots=True)
class CourierPosition:
    latitude: float
    longitude: float
    recorded_at: datetime | None
    # from_api returns None unless both coordinates are real numbers (bool excluded)

@dataclass(slots=True)
class DeliveryProgress:
    """The live part of tracking; null before the order is queued.
    Shaped so the SSE ``eventData`` (same keys) can reuse it later."""
    status: str | None                 # raw deliveryStatus
    generated_at: datetime | None
    estimated_arrival: datetime | None
    stops_before: int | None           # 0 and None are different
    courier_position: CourierPosition | None
    courier_location_stale: bool | None

@dataclass(slots=True)
class DeliveryTracking:
    order_id: int | None
    slot_since: datetime | None
    slot_till: datetime | None
    slot_type: str | None
    early_delivery_available: bool
    early_delivery_requested: bool
    early_delivery_allowed_from: datetime | None
    courier_name: str | None           # displayName only — first name in the sample
    destination: Coordinates | None    # the customer's delivery point
    progress: DeliveryProgress | None

    # convenience, all derived from progress / slot:
    status -> str | None
    estimated_arrival -> datetime | None
    stops_before -> int | None
    is_active -> bool       # IN_QUEUE / ON_THE_WAY / ARRIVED / HANDING_OVER
    has_arrived -> bool     # ARRIVED / HANDING_OVER
    is_delivered -> bool    # DELIVERED
    promised_arrival -> datetime | None  # see below
```

Left out on purpose: `courier.phoneNumber`, `courier.photoUrl`, `courierMovement` and
`routeToStop` polylines (personal data or map-rendering detail that nothing needs yet). There is
no `raw` field, because it would carry the phone number. The docstrings flag `courier_name`,
`destination` and `courier_position` as personal data, so consumers redact them in logs and
diagnostics.

**`promised_arrival`** turns the observation into library logic:

```
eta = progress.estimated_arrival
if eta is None:                    return None
if has_arrived or is_delivered:    return eta          # no capping once it's over
floor = early_delivery_allowed_from if early_delivery_requested else slot_since
return max(eta, floor) if floor else eta
```

In words: the courier plan, but never earlier than the shop allows the courier to arrive.

```python
@dataclass(slots=True)
class UpcomingOrder:
    id: int
    slot_id: int | None
    slot_type: str | None            # ON_TIME / EXPRESS / …
    slot_since: datetime | None
    slot_till: datetime | None
    order_time: datetime | None
    items_count: int | None          # order lines
    items_total_quantity: int | None # units
    total_price: float | None
    currency: str | None
    available_actions: list[str] = field(default_factory=list)
```

Left out: `address`, `payment`, `itemImages`, `pblLink`, `invoiceAwaitingPayment`,
`expressDeliveryPromise` (the last was always null when observed; it can be added once seen populated).
`from_api` returns `None` for an entry without an integer `id`, and the list skips those entries.

```python
EtaSource = Literal["tracking", "slot"]

@dataclass(slots=True)
class NextDelivery:
    order: UpcomingOrder
    tracking: DeliveryTracking | None  # None: not available (404/failed)
    eta: datetime | None               # tracking.promised_arrival, else order.slot_since
    eta_source: EtaSource | None
    status: str | None                 # tracking status, None without tracking
```

### Endpoint (`rohlik_api/endpoints.py`)

```python
@classmethod
def delivery_tracking(cls, order_id: int) -> str:
    return f"/api/v2/orders/{int(order_id)}/delivery-tracking"
```

### Service methods (`rohlik_api/services/orders.py`)

**3.1 `get_delivery_tracking(order_id)`**
- Same pattern as `get_detail`.
- `404` → `None`, no warning logged, because it is a normal answer for a finished or unknown order.
- `HTTP_ERRORS` and other `raise_for_status` failures → warning, `None`.
- JSON decode error or non-dict body → warning, `None`.
- Otherwise `DeliveryTracking.from_api(body)`.

**3.2 `get_upcoming()`**
- One GET on `Endpoints.NEXT_ORDER`. Returns `None` on failure or a non-list body, so the shared
  `_fetch_endpoint` can't be used (it is typed for dicts and doesn't check the body type).
- Otherwise it parses each entry and returns them sorted by `slot_since`, with orders without a slot last.
- `get_next()` stays as it is (raw).

**3.3 `get_next_delivery()`**
1. `orders = await self.get_upcoming()`.
   - If `orders is None`, raise `APIRequestFailedError("Cannot fetch upcoming orders")`. Returning
     `None` here would be indistinguishable from "no order", and a consumer would wrongly clear its state.
   - If `orders == []`, return `None`.
2. Take `order = orders[0]` (the soonest slot).
3. Fetch `tracking = await self.get_delivery_tracking(order.id)`, which is `None` on 404 or failure.
4. Resolve the ETA:
   - `eta = tracking.promised_arrival if tracking else None`
   - if `eta` is set, `eta_source = "tracking"`
   - otherwise, if `order.slot_since` is set, use it with `eta_source = "slot"`
   - otherwise `eta = eta_source = None`
5. Return `NextDelivery(order, tracking, eta, eta_source, tracking.status if tracking else None)`.

This is documented as "the soonest order only". Consumers with several concurrent orders call
3.2 + 3.1 themselves.

The raise in step 1 is the only deviation from the "read methods return None" convention. It is
justified in the docstring and README. Alternative for review: return `None` and accept the ambiguity.

### Exports, docs, version

- `__init__.py`: export `DeliveryTracking`, `DeliveryProgress`, `CourierPosition`, `Coordinates`,
  `UpcomingOrder`, `NextDelivery`, `TrackingStatus`, `parse_datetime`.
- README:
  - Orders service: add three lines to the API reference.
  - New "Tracking a delivery" example covering `get_next_delivery()`, status/ETA/stops and `promised_arrival` semantics.
  - Note that the endpoint is unofficial, was verified on Rohlík.cz only, and that other shops may return 404 (→ `None`).
  - Note which fields are personal data.
- Typed-models table: add the new models.
- `__version__ = "0.4.0"`. Release via PUBLISHING.md after CI (ruff, black, mypy, pytest) passes.

---

## Tests

**Fixtures:** `tests/fixtures/delivery_tracking/*.json`. They are generated once from the
2026-11-24 capture by a throwaway local script that is **not** committed. The script:
- replaces IDs with fakes
- sets coordinates to a fixed public point (0.0 offsets from a dummy)
- sets the courier name to `"Courier"` and the phone number to `"+420000000000"`, so tests prove the phone is dropped
- puts empty strings in the polylines

All times are kept. The review checks the files by hand before they are committed.

| Fixture | Source state |
| --- | --- |
| `before_queue.json` | `progress: null`, early delivery available |
| `in_queue_no_eta.json` | IN_QUEUE, 11 stops, ETA null |
| `in_queue_eta.json` | IN_QUEUE, ETA, not early-requested (ETA before slot) |
| `in_queue_early.json` | IN_QUEUE, early requested, allowedFrom |
| `on_the_way.json` | position + movement + route |
| `arrived.json`, `handing_over.json` | |
| `delivered.json` | stops null, position null, ETA kept |
| `not_found.json` | 404 envelope |
| `upcoming_one.json`, `upcoming_empty.json` | |

**Unit tests** (`tests/test_models.py`, `test_helpers.py`, `test_services.py`, `test_endpoints.py`):

- **`parse_datetime`:** `Z`, ms, 9 fractional digits, `+0100`, `+01:00`, naive → None, garbage → None, non-str → None.
- **`DeliveryTracking.from_api`** for each fixture:
  - fields, properties, and that `progress` is None for `before_queue`
  - positions: non-numeric or bool coordinates → `None`
  - the phone number appears nowhere in `dataclasses.asdict(model)`
  - an unknown status string is kept and `is_active` is False
- **`promised_arrival`:**
  - capped to `slot_since` (not requested)
  - capped to `allowed_from` (requested)
  - not capped when the ETA is later
  - not capped once arrived or delivered
  - None without an ETA
- **`UpcomingOrder.from_api`:** full fixture, missing slot, missing ID (skipped), sorting with multiple orders.
- **Service:**
  - `get_delivery_tracking`: 200 → model; 404 → None and no warning (caplog); 500 → None and a warning; ClientError and timeout → None; non-dict JSON → None.
  - `get_upcoming`: list → models; `[]` → `[]`; failure → None.
  - `get_next_delivery`:
    - no orders → None
    - upcoming failure → raises `APIRequestFailedError`
    - tracking with ETA → source "tracking"
    - tracking 404 → source "slot"
    - tracking without ETA → "slot"
    - picks the soonest of two orders
    - exactly 2 GETs with the expected paths
- **Endpoint builder:** path, `int()` coercion.

**Live check (manual, not in CI):** an opt-in script calls `get_next_delivery()` during a real
delivery and prints the redacted fields. It is run once before release.

---

## Steps

1. `parse_datetime` + tests.
2. Models + `TrackingStatus` + model tests (fixtures added here).
3. Endpoint builder + `get_delivery_tracking` + tests.
4. `get_upcoming` + tests.
5. `get_next_delivery` + tests.
6. Exports, README, version 0.4.0; run ruff, black, mypy, pytest.
7. Live check during the next delivery, then release.

## Open questions for review

1. Is raising in `get_next_delivery` when upcoming fails right, or should it stay `None`?
2. Should `promised_arrival` be the default `eta` in `NextDelivery`, with the raw ETA always on
   `tracking.estimated_arrival`, or the other way round?
3. Is `destination` worth exposing (distance calculation) given that it is the customer's location?
4. Is a flat `DeliveryTracking` with `progress` nested the right shape for the later SSE reuse?
