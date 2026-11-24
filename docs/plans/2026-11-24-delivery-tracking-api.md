# Delivery tracking in rohlik-api — Implementation Plan (3.1–3.3)

**Revision 2**, amended by **Revision 3** at the end, which records the changes made during the two code reviews. Where they differ, Revision 3 wins.

**Goal:** give every consumer of `rohlik-api` (Home Assistant, rohlik-mcp, scripts) a typed,
locale-independent view of a delivery in progress: status, ETA, stops ahead and courier
position. It is built on the delivery-tracking endpoint observed through one complete live
delivery on 2026-11-24 (HA-RohlikCZ `docs/plans/2026-11-24-delivery-tracking-observations.md`).

**Scope:** additive only. No existing method changes behaviour or shape. `get_data()` is not extended.

| # | Feature | Requests |
| --- | --- | --- |
| 3.1 | `orders.get_delivery_tracking(order_id) -> DeliveryTracking \| None` | 1 |
| 3.2 | `orders.get_upcoming() -> list[UpcomingOrder] \| None`, plus `UpcomingOrder.list_from_api(raw)` | 1 / 0 |
| 3.3 | `NextDelivery.resolve(order, tracking)` (pure), plus `orders.get_next_delivery()` (thin wrapper) | 0 / 2 |

Out of scope: the SSE stream, announcements, moving order detail to v4, the delivery destination, and HA work.

> **Update (0.5.0):** the delivery destination is now parsed as `DeliveryTracking.destination`,
> with `courier_position`/`courier_distance` shortcuts, for the HA courier map. The notes below
> about dropping `destination` describe 0.4.0.

---

## What was observed (and what was not)

Evidence: 262 tracking polls (all HTTP 200), the SSE stream, and 3 upcoming-orders samples, for one
Rohlík.cz order (`ON_TIME` slot, early delivery requested by the customer at T−1 h).

- **Response:** `orderId`, `deliverySlot{since, till, type}` (UTC `Z`; `since` is `…:00:01`),
  `destination{latitude, longitude}`, `courier{displayName, phoneNumber, photoUrl}`,
  `earlyDelivery{available, requested, allowedFrom}`, `progress`.
- **`progress: null` before the queue starts.** `courier` is then **null as well** (9 of 9 such polls).
  `progress`, when present, is `{generatedAt, deliveryStatus, stopsBefore, estimatedArrival,
  courierLocationStale, courierPosition{latitude, longitude, recordedAt}, courierMovement, routeToStop}`.
- **Status:** `IN_QUEUE → ON_THE_WAY → ARRIVED → HANDING_OVER → DELIVERED`.
  - `estimatedArrival` is null at first in `IN_QUEUE` and is kept after `DELIVERED`. The kept value is
    the last ETA, **not** the arrival time (ETA 12:46:18; `ARRIVED` seen 12:45:51).
  - `stopsBefore` becomes null at `DELIVERED`.
  - Position exists from `ON_THE_WAY` to `HANDING_OVER`.
- **`generatedAt` is not "now".**
  - In `IN_QUEUE`, 40 of 209 polls returned a snapshot more than 60 s old, and the oldest was 477 s.
  - After `DELIVERED` it is frozen at the delivery moment. The endpoint stayed 200 for the 20 minutes observed.
- **`earlyDelivery.allowedFrom`** equals `slot.since − 1 h` once requested.
  - The shop's own texts switched from slot start to ETA in the same minute as three other things: the
    request, the T−1 h mark and stops 4 → 3.
  - **It is unknown which caused it.** The capping rule below is therefore a documented heuristic.
- **Timestamps** use `…Z`, `….886Z`, `….12272713Z` (9 digits) and, in upcoming orders, `….000+0100`.
  All parse to aware datetimes with `datetime.fromisoformat` on Python ≥ 3.13 (the package minimum).
- **404:** seen **only for a made-up order ID**. A 404 for a finished, cancelled or old order was **not**
  observed (a past order returned 200 with `progress: null`).
- **Upcoming orders** returned `[]` with no order, and dropped the order within about 1 s of `DELIVERED`
  (one sample). Item keys: `id, itemsCount, itemsTotalQuantity, priceComposition.total{amount, currency},
  orderTime, deliverySlot{id, type, since, till}, address, payment, itemImages, availableActions,
  expressDeliveryPromise, pblLink, invoiceAwaitingPayment`.
- **Never observed:**
  - early delivery not requested all the way to arrival
  - two concurrent orders
  - a slot type other than `ON_TIME`
  - a cancelled or delayed order
  - any shop other than Rohlík.cz

  The README says so.

---

## Design

### Naming

- **`TrackingStatus` (`StrEnum`):** constants for the five observed values. Models keep the **raw string**.
- **`DeliveryEtaSource = Literal["tracking", "slot"]`:** named to avoid HA's `EtaSource` in `eta.py`.
- **`NextDelivery`:** the result of 3.3.

### Datetime helper (`helpers.py`, exported)

```python
def parse_datetime(value: Any) -> datetime | None:
    """Aware datetime from an API timestamp, or None (None, non-str, unparseable, naive)."""
```

### Models (`models.py`, "Delivery tracking" section)

Every model is a `@dataclass(slots=True)` with `from_api`. Parsing never raises: wrong types or a missing level give `None`.
Integers reject `bool`. Coordinates must be real numbers and not `bool`.

**Personal data:** `courier_name` and `courier_position` are declared with `field(repr=False)`, so
logging a model does not leak them. A test asserts this. Their docstrings say they must be redacted in logs
and diagnostics.

```python
@dataclass(slots=True)
class CourierPosition:
    latitude: float
    longitude: float
    recorded_at: datetime | None

@dataclass(slots=True)
class DeliveryProgress:
    """Live part of tracking (`progress`); None before the order is queued.
    Same keys as the SSE eventData, for later reuse. `generated_at` may be minutes old,
    and is frozen after DELIVERED — it is not the time of the request."""
    status: str | None
    generated_at: datetime | None
    estimated_arrival: datetime | None
    stops_before: int | None                       # 0 and None differ
    courier_location_stale: bool | None
    courier_position: CourierPosition | None = field(default=None, repr=False)

@dataclass(slots=True)
class DeliveryTracking:
    order_id: int | None
    slot_since: datetime | None
    slot_till: datetime | None
    slot_type: str | None
    early_delivery_available: bool | None
    early_delivery_requested: bool | None
    early_delivery_allowed_from: datetime | None
    progress: DeliveryProgress | None
    courier_name: str | None = field(default=None, repr=False)   # displayName; None until queued

    status -> str | None                 # progress.status
    estimated_arrival -> datetime | None # raw courier ETA; after DELIVERED: last ETA, not arrival time
    stops_before -> int | None
    is_active -> bool                    # status is not None and != DELIVERED  (unknown values count as active)
    has_arrived -> bool                  # ARRIVED / HANDING_OVER
    is_delivered -> bool                 # DELIVERED
    arrival_floor -> datetime | None     # see below
```

Left out on purpose:
- `destination` (the customer's location; consumers know their own address, and it can be added later
  but never removed). *0.4.0 only: parsed since 0.5.0.*
- the phone number and photo
- the `courierMovement` and `routeToStop` polylines
- any `raw` field

**`arrival_floor`** is the earliest time the shop lets the courier arrive. It is `early_delivery_allowed_from`
when early delivery has been requested, otherwise `slot_since`, or `None` if unknown. It is plain data, and the
heuristic is applied in 3.3 only.

```python
@dataclass(slots=True)
class UpcomingOrder:
    id: int
    slot_id: int | None
    slot_type: str | None
    slot_since: datetime | None
    slot_till: datetime | None
    order_time: datetime | None
    items_count: int | None              # order lines
    items_total_quantity: int | None     # units
    total_price: float | None
    currency: str | None
    available_actions: list[str] = field(default_factory=list)

    @classmethod
    def from_api(cls, data) -> UpcomingOrder | None   # None without an int id
    @classmethod
    def list_from_api(cls, data) -> list[UpcomingOrder]
        # parses a raw upcoming list (e.g. get_data()["next_order"]); skips bad entries;
        # sorted by slot_since in absolute time, orders without a slot last
```

Left out: `address`, `payment`, `itemImages`, `pblLink`, `invoiceAwaitingPayment`, `expressDeliveryPromise`.

```python
@dataclass(slots=True)
class NextDelivery:
    order: UpcomingOrder
    tracking: DeliveryTracking | None   # None: the order has no tracking (404)
    eta: datetime | None
    eta_source: DeliveryEtaSource | None
    eta_capped: bool                    # eta was raised to the arrival floor
    status: str | None

    @classmethod
    def resolve(cls, order: UpcomingOrder, tracking: DeliveryTracking | None) -> NextDelivery:
        """Pure: no I/O. Lets consumers that already hold the upcoming list and a
        tracking result (e.g. HA via get_data()) reuse the ETA rule without extra requests."""
```

**ETA rule in `resolve`** (a heuristic, documented as based on one delivery):

```
raw = tracking.estimated_arrival if tracking else None
if raw is not None:
    floor = tracking.arrival_floor
    if tracking.status == IN_QUEUE and floor is not None and raw < floor:
        eta, capped = floor, True            # shop won't deliver before the floor
    else:
        eta, capped = raw, False             # ON_THE_WAY and later: courier plan as is
    source = "tracking"
elif order.slot_since is not None:
    eta, source, capped = order.slot_since, "slot", False
else:
    eta, source, capped = None, None, False
```

The cap is applied **only while `IN_QUEUE`**, so the value never jumps backwards when the courier is
already on the way. `max()` only raises early ETAs, so it cannot hide a delay. The raw value is always
available as `tracking.estimated_arrival`.

### Endpoint (`endpoints.py`)

```python
@classmethod
def delivery_tracking(cls, order_id: int) -> str:
    return f"/api/v2/orders/{int(order_id)}/delivery-tracking"
```

### Service methods (`services/orders.py`)

A private `_fetch_delivery_tracking(order_id) -> tuple[Literal["ok", "not_found", "failed"], DeliveryTracking | None]` serves both public paths.

| Outcome | Return value | Log |
| --- | --- | --- |
| 200 with a dict body | `"ok"`, model | — |
| 404 | `"not_found"`, `None` | — (a normal answer) |
| any other status, `HTTP_ERRORS`, `ValueError` from `Response.json()` (invalid JSON is not in `HTTP_ERRORS`), non-dict body | `"failed"`, `None` | warning |

An authentication failure (`InvalidCredentialsError` / `APIRequestFailedError` from `_ensure_logged_in`)
propagates, as in every other read method.

- **3.1 `get_delivery_tracking(order_id)`** is public and returns the model or `None` for both
  `"not_found"` and `"failed"`, which keeps the library's read convention. The docstring says that callers
  who must tell the two apart should use `get_next_delivery()`.
- **3.2 `get_upcoming()`** makes one GET on `Endpoints.NEXT_ORDER`. A failure, invalid JSON or a non-list body
  gives `None`. Otherwise it returns `UpcomingOrder.list_from_api(body)`. `get_next()` is unchanged.
- **3.3 `get_next_delivery()`**:
  1. `orders = await self.get_upcoming()`. `None` raises `APIRequestFailedError("Cannot fetch upcoming orders")`;
     `[]` returns `None`.
  2. `outcome, tracking = await self._fetch_delivery_tracking(orders[0].id)`. `"failed"` raises
     `APIRequestFailedError("Cannot fetch delivery tracking")`.
  3. Return `NextDelivery.resolve(orders[0], tracking)`.

  The return value means:
  - `None`: there is no upcoming order.
  - A raised error: the state is unknown, so the caller should keep its previous state.
  - Only the soonest order is resolved. Consumers with concurrent orders combine 3.2 + 3.1 + `resolve` themselves.

  Raising is consistent with read methods already raising on auth failure.

### Exports, docs, version

- **`__init__.py`:** export `DeliveryTracking`, `DeliveryProgress`, `CourierPosition`, `UpcomingOrder`,
  `NextDelivery`, `TrackingStatus`, `DeliveryEtaSource`, `parse_datetime`.
- **README:**
  - three API-reference lines
  - a "Tracking a delivery" example
  - the ETA rule and `eta_capped`
  - `generated_at` caveats
  - the personal-data fields
  - "unofficial endpoint, verified on Rohlík.cz with one delivery; other shops may 404" and the never-observed list
- **Typed-models table:** the new models.
- **`__version__ = "0.4.0"`.** Release via PUBLISHING.md once CI (ruff, black, mypy, pytest) passes.

---

## Tests

### Fixtures — whitelist, hand-written

`tests/fixtures/delivery_tracking/*.json` are **written by hand** using only the keys the models read.
Each one also has the keys that must be proven dropped (`phoneNumber`, `photoUrl`, `destination`,
`courierMovement`, `routeToStop`; `destination` is parsed since 0.5.0). The values are constants:

| Field | Value |
| --- | --- |
| order IDs | `1000000001`, `1000000002` |
| coordinates | `50.0`, `14.0` |
| courier | `"Courier"`, `"+420000000000"` |
| polylines | `"x"` |

Timestamps and statuses follow the observed timeline. Nothing is copied from the capture.

A one-off local check, **not committed**, greps the fixture directory for the real order ID, phone
number and coordinate prefixes. The real values are read from the private capture outside the repo, and the check runs before the
fixtures are committed. `tests/` is not packaged (MANIFEST.in).

| Fixture | State |
| --- | --- |
| `before_queue.json` | `progress: null`, `courier: null`, early delivery available |
| `in_queue_no_eta.json` | IN_QUEUE, 11 stops, ETA null |
| `in_queue_eta.json` | IN_QUEUE, ETA before the slot, early delivery **not** requested |
| `in_queue_early.json` | IN_QUEUE, ETA before the slot, early delivery requested (`allowedFrom`) |
| `on_the_way.json` | ETA before the slot, position, movement, route |
| `arrived.json`, `handing_over.json` | |
| `delivered.json` | stops null, position null, ETA kept, early delivery unavailable |
| `not_found.json` | 404 envelope |
| `upcoming_one.json`, `upcoming_two.json` (one `Z`, one `+0100`, out of order), `upcoming_empty.json` | |

### Cases

- **`parse_datetime`:**
  - `Z`, ms, 9 fractional digits, `+0100`, `+01:00` parse
  - naive, garbage and non-str give `None`
- **`DeliveryTracking.from_api`** (each fixture):
  - fields and properties
  - `before_queue` has `progress is None` and `courier_name is None`
  - an unknown status is kept, and `is_active` is **True**
  - bool or str `stopsBefore` gives `None`
  - bool or str coordinates give no position
  - the phone number is not in `dataclasses.asdict(model)`
  - `courier_name` and the coordinates are not in `repr(model)`
- **`arrival_floor`:** requested gives `allowed_from`, otherwise `slot_since`, and `None` when the slot is missing.
- **`NextDelivery.resolve`:**
  - IN_QUEUE with the ETA before the floor is capped, with `eta_capped=True`
  - IN_QUEUE with the ETA after the floor is the raw value
  - `on_the_way` with the ETA before the slot is **not** capped
  - `arrived`, `delivered` are raw
  - a tracking result without an ETA falls back to the slot
  - no tracking falls back to the slot
  - no slot and no tracking give `None`
- **`UpcomingOrder`:**
  - `from_api` with the full item, a missing slot, and a missing or bool ID (gives `None`)
  - `list_from_api` with a non-list input gives `[]`
  - sorting across `Z` and `+0100`
- **Service:**
  - `get_delivery_tracking`:
    - 200 gives the model
    - 404 gives `None` and logs no warning (caplog)
    - 500 gives `None` with a warning
    - `ClientError` and timeout give `None`
    - invalid JSON (`ValueError`) and a non-dict body give `None`
    - an auth error propagates
  - `get_upcoming`:
    - a list is parsed
    - `[]` gives `[]`
    - a failure, invalid JSON or a non-list body give `None`
  - `get_next_delivery`:
    - no orders give `None`
    - an upcoming failure raises
    - a tracking failure raises
    - a tracking 404 gives `eta_source="slot"`
    - the soonest of two orders is picked
    - exactly two GETs are made, with the expected paths
- **Endpoint builder:** the path and `int()` coercion.

**Live check (manual, before release):** an opt-in local script runs `get_next_delivery()` during a real
delivery and prints redacted fields. If possible, also check a delivery **without** an early-delivery request,
the case the heuristic most depends on.

---

## Steps

1. `parse_datetime` + tests.
2. Hand-written fixtures + the local leak check (not committed).
3. Models + `TrackingStatus` + model tests.
4. Endpoint builder, `_fetch_delivery_tracking`, `get_delivery_tracking` + tests.
5. `UpcomingOrder.list_from_api`, `get_upcoming` + tests.
6. `NextDelivery.resolve`, `get_next_delivery` + tests.
7. Exports, README, version 0.4.0; ruff, black, mypy, pytest.
8. Live check on the next delivery, then release.

## Decisions taken in review

| Question | Decision |
| --- | --- |
| Raise in 3.3 when upcoming fails? | Yes, and also when tracking fails (B2). `None` means only "no upcoming order" |
| Default `eta`? | The courier ETA, raised to the floor only while `IN_QUEUE`, flagged by `eta_capped`. The raw value stays on `tracking.estimated_arrival` |
| Expose `destination`? | No, not in 0.4.0; added in 0.5.0 |
| Nested `progress`? | Yes. Convenience properties on `DeliveryTracking` keep access flat |
| Should 3.3 live in the library? | Yes, as a pure `resolve()` plus a thin wrapper, so HA can use the rule without a duplicate upcoming request |

---

## Revision 3 — changes made during code review

These supersede the sections above where they differ.

1. **`get_delivery_tracking(order_id, *, raise_on_error=False)`.**
   - With `raise_on_error=True` a failed request raises `APIRequestFailedError` (chained to the cause),
     so `None` means only "no tracking" (404).
   - This replaces the advice to use `get_next_delivery()` to tell the two apart. `get_next_delivery()` uses it internally.
2. **Malformed 200 responses fail.** A 200 response without an integer `orderId` (e.g. an error envelope) counts as a failure, not as empty tracking.
3. **The ETA can move earlier.** The cap applies only while `IN_QUEUE` (unchanged), so the ETA **can move earlier** at
   `IN_QUEUE → ON_THE_WAY` when early delivery was not requested. `eta_capped` turns False at that point.
   This is documented and tested. The earlier claim that the value "never jumps backwards" was wrong.
4. **`NextDelivery.resolve` checks the order.**
   - It raises `ValueError` if the tracking belongs to another order. `get_next_delivery` reports that as `APIRequestFailedError`.
   - Without an order slot it falls back to the tracking's slot.
   - An estimate equal to the floor is not capped.
5. **Number parsing:** non-finite or overflowing numbers become `None` (parsing never raises).
6. **`Endpoints.delivery_tracking` validates the ID.** It accepts an int or a string of digits, and rejects bool, floats, negatives and other strings.
   The URL is built before the request, so an invalid ID raises instead of looking like a failed request.
7. **Personal data:** `CourierPosition` also hides its coordinates in `repr`.
8. **`get_next_delivery()` rarely reports `DELIVERED`.** The order leaves the upcoming list within about a second, so the README tells
   consumers to poll `get_delivery_tracking(order_id)` for the final state.
9. **No README models table.** The README has no typed-models table, so none was added. The models are documented in "Tracking a delivery".
