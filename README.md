# 🛒 Rohlik API Python Client

An async, fully typed Python client for the [Rohlik.cz](https://www.rohlik.cz)
online grocery service and its sister shops [Knuspr.de](https://www.knuspr.de),
[Gurkerl.at](https://www.gurkerl.at), [Kifli.hu](https://www.kifli.hu) and
[Sezamo.ro](https://www.sezamo.ro) — search products, manage your cart, browse
recipes (Rohlík Chef), and read your orders and deliveries, all from Python.

> ## ⚠️ Unofficial — personal use only
>
> This is an **unofficial** client for Rohlik.cz's **non-public** API. It is
> **not affiliated with, authorized by, or endorsed by Rohlik.cz / Rohlik Group**.
>
> - Intended for **personal, non-commercial use with your own account** only.
> - The private API can change or break **at any time, without notice**.
> - Your use may be subject to **Rohlik.cz's Terms of Service** — review them and
>   behave responsibly (don't hammer the API or use it commercially).
> - Provided "as is", with **no warranty**. **Use at your own risk.**

## Table of contents

- [Features](#features)
- [Related projects](#related-projects)
- [Requirements](#requirements)
- [Installation](#installation)
- [Quick start](#quick-start)
- [Credentials & security](#credentials--security)
- [Typed models](#typed-models)
- [Services](#services)
- [API reference](#api-reference)
- [Tracking a delivery](#tracking-a-delivery)
- [Error handling](#error-handling)
- [Advanced usage](#advanced-usage)
- [Development](#development)
- [Disclaimer](#disclaimer)
- [License](#license)

## Features

- 🚀 Built on aiohttp; bring your own session (e.g. Home Assistant's shared session)
- 🔐 Automatic login/logout, plus transparent re-authentication when a session expires (HTTP 401)
- 🎯 Clean, service-based API (`client.cart`, `client.products`, …)
- 🧩 Fully typed dataclass models for parsed responses (`py.typed`)
- 🔄 Works as an async context manager
- 🍳 Recipe search and ingredient shopping (Rohlík Chef)
- 📦 Product details, composition/nutrition, prices, and AI summaries
- 🚚 Live delivery tracking: status, courier ETA, stops ahead and courier position
- 🌍 Works with every Rohlík Group shop: Rohlík.cz, Knuspr.de, Gurkerl.at, Kifli.hu and Sezamo.ro
  ([other shops](#other-shops))

## Related projects

Built on top of this library — handy if you'd rather not write Python:

- 🤖 **[rohlik-mcp](https://github.com/dvejsada/rohlik-mcp)** — a
  [Model Context Protocol](https://modelcontextprotocol.io/) server that exposes
  Rohlik.cz to AI assistants like Claude. Search products, manage your cart, plan
  meals from recipes, and check orders and deliveries in plain language.
- 🏠 **[HA-RohlikCZ](https://github.com/dvejsada/HA-RohlikCZ)** — a
  [Home Assistant](https://www.home-assistant.io/) integration that brings your
  Rohlik.cz cart, orders and deliveries into your smart home.

## Requirements

- Python 3.13+
- [aiohttp](https://docs.aiohttp.org/) (installed automatically)

## Installation

```bash
pip install rohlik-api
```

## Quick start

```python
import asyncio
from rohlik_api import RohlikAPI

async def main():
    async with RohlikAPI(username="your_email@example.com", password="your_password") as client:
        # Search for products (returns a SearchResults model)
        results = await client.products.search("mleko", limit=5)
        for product in results.results:
            print(f"{product.name} - {product.price}")

        # Get cart contents (returns a Cart model)
        cart = await client.cart.get_content()
        print(f"Cart total: {cart.total_price} ({cart.total_items} items)")

        # Search recipes (returns a RecipeSearchResults model)
        recipes = await client.recipes.search("rajská", limit=5)
        print(f"Found {recipes.total_hits} recipes")

asyncio.run(main())
```

The async context manager logs you in on entry and logs out + closes the
connection on exit.

## Credentials & security

The client authenticates with your normal shop account **email and password**.

- **Never hard-code credentials** in source you commit. Prefer environment
  variables or a secrets manager:

  ```python
  import os
  from rohlik_api import RohlikAPI

  client = RohlikAPI(
      username=os.environ["ROHLIK_USERNAME"],
      password=os.environ["ROHLIK_PASSWORD"],
  )
  ```

- Credentials are only ever sent over HTTPS to the shop you target (Rohlik.cz
  unless you pass another `base_url`). This library does not store or transmit
  them anywhere else.
- Use a dedicated account if you're uncomfortable automating your primary one.

## Typed models

Service methods that parse responses return typed dataclasses (importable from
`rohlik_api`) rather than raw dictionaries, so your editor and type checker know
the shape of the data:

```python
from dataclasses import asdict
from rohlik_api import Cart, SearchResults

cart = await client.cart.get_content()   # -> Cart
cart.total_price                         # float
cart.products[0].name                    # str

# Convert any model to a plain dict (e.g. for JSON / Home Assistant / MCP):
asdict(cart)
```

Raw passthrough endpoints (`orders.*` apart from the delivery-tracking methods, `delivery.*`, `account.get_premium_profile`,
`account.get_bags_info`, `account.get_announcements`, and `get_data`) return the
decoded JSON as `dict` / `list`, since they are not reshaped by the client.

## Services

Functionality is grouped into services, accessed as properties on the client:

| Service  | Property           | Description                                   |
| -------- | ------------------ | --------------------------------------------- |
| Cart     | `client.cart`      | Shopping cart operations                      |
| Products | `client.products`  | Product search and details                    |
| Orders   | `client.orders`    | Order history                                 |
| Delivery | `client.delivery`  | Delivery info and timeslots                   |
| Account  | `client.account`   | Account data and shopping lists               |
| Recipes  | `client.recipes`   | Recipe search and ingredients (Rohlík Chef)   |

## API reference

### Cart service (`client.cart`)

```python
# Get cart contents
cart = await client.cart.get_content()
# CartItem has id, cart_item_id, name, quantity, price, category_name, brand, currency, image
# -> Cart(total_price=199.90, total_items=3, can_make_order=True, products=[CartItem, ...],
#         minimum_order_price=..., currency="CZK")
# can_make_order also requires checkout details (e.g. a delivery slot); to check
# the minimum order value, compare total_price with minimum_order_price.

# Add items to cart
added = await client.cart.add_items([
    {"product_id": 123456, "quantity": 2},
    {"product_id": 789012, "quantity": 1},
])
# -> [123456, 789012]   (list of product IDs successfully added)

# Delete item from cart (raises APIRequestFailedError on failure)
await client.cart.delete_item(order_field_id="abc123")
```

### Products service (`client.products`)

```python
# Search for products -> SearchResults | None (None only on request failure)
results = await client.products.search("mléko", limit=10, favourite=False)
for product in results.results:  # ProductSearchResult: id, name, price, brand, amount, image
    print(product.name, product.price, product.image)
# image is the full CDN URL of the product picture (built from the API's imgPath
# and the shop's Site.cdn_url), or None when the API sends no picture.

# AI-generated product summary -> AISummary | None
summary = await client.products.get_ai_summary(product_id=1384964)

# Composition / nutrition / allergens -> ProductComposition | None
composition = await client.products.get_composition(product_id=1425155)

# Current price -> ProductPrice | None
price = await client.products.get_price(product_id=1425155)

# Raw product detail (brand, attributes, …) -> dict | None (None on 404)
detail = await client.products.get_detail(product_id=1425155)

# Category hierarchy -> list[dict] | None (None if discontinued / 404)
categories = await client.products.get_categories(product_id=1425155)

# Basic data for many products in one request -> list[ProductCard] | None
# (same order as the IDs; IDs the API did not return are skipped)
cards = await client.products.get_cards([1425155, 1384964])

# This week's deals ("Akce týdne") as ProductCards -> list[ProductCard] | None
deals = await client.products.get_week_sales(size=30)
for card in deals or []:
    print(card.name, card.price, card.original_price, card.on_sale)

# Your favourite products ("Oblíbené"), with image -> list[ProductCard] | None
# Pages through the favourites list (sponsored entries are skipped), then loads
# the cards in chunks of 50. get_favourite_ids() returns only the IDs.
favourites = await client.products.get_favourites()
for card in favourites or []:
    print(card.id, card.name, card.amount, card.image, card.in_stock)
```

### Orders service (`client.orders`)

```python
next_order = await client.orders.get_next()                       # upcoming order
last_order = await client.orders.get_last()                       # last delivered order
orders = await client.orders.get_delivered(limit=50, offset=0)    # one history page
all_orders = await client.orders.get_all_delivered()              # every page, paginated
detail = await client.orders.get_detail(order_id=12345678)        # full order incl. items

# Typed upcoming orders, soonest slot first -> list[UpcomingOrder] | None
upcoming = await client.orders.get_upcoming()

# Live delivery tracking for one order -> DeliveryTracking | None
tracking = await client.orders.get_delivery_tracking(order_id=12345678)

# Soonest upcoming order + its tracking + resolved ETA -> NextDelivery | None (raises on failure)
nxt = await client.orders.get_next_delivery()

# Line items of one order (upcoming or delivered) -> list[OrderItem] | None
# OrderItem: id (product), name, quantity, price, unit_price, textual_amount,
# currency, image. Uses the same request as get_detail.
items = await client.orders.get_items(order_id=12345678)
```

See [Tracking a delivery](#tracking-a-delivery) for what these return.

### Delivery service (`client.delivery`)

```python
delivery = await client.delivery.get_info()                    # first available delivery
timeslot = await client.delivery.get_timeslot_reservation()    # reserved slot, if any
slots = await client.delivery.get_next_slots()                 # upcoming slots for your address
windows = await client.delivery.get_slots()                    # every window as DeliverySlot
announcements = await client.delivery.get_announcements()      # e.g. courier ETA messages
addresses = await client.delivery.get_addresses()              # saved delivery addresses
address_id = await client.delivery.get_active_address_id()     # address used for slots
```

`get_next_slots()` needs a delivery address. The login response does not always
include one, so the client falls back to your saved addresses (preferring the one
you are currently delivered to) and caches the result.

`get_slots()` parses the same response into a sorted `list[DeliverySlot]`: every
one-hour window (`type` `"VIRTUAL"`, `minutes` 60) and, where the shop offers them,
the 15-minute windows (`"ON_TIME"`, `minutes` 15, usually `premium`). Fully booked
windows are included with `free_percent` 0 (`available` is False).

### Account service (`client.account`)

```python
premium = await client.account.get_premium_profile()
bags = await client.account.get_bags_info()
announcements = await client.account.get_announcements()

# Shopping list by ID -> ShoppingList
shopping_list = await client.account.get_shopping_list("list_id_here")
# ShoppingList(name="My List", products_in_list=[...])
```

### Recipes service (`client.recipes`) — Rohlík Chef

```python
# Search recipes -> RecipeSearchResults(recipes=[RecipeSummary, ...], total_hits=4)
recipes = await client.recipes.search("rajská", limit=10, offset=0)

# Recipe details -> RecipeDetail | None
recipe = await client.recipes.get_detail(recipe_id=59)

# Products for ingredients -> IngredientProducts | None
products = await client.recipes.get_ingredient_products(ingredient_ids=[102, 56], limit=5)
```

### Aggregated data

```python
# Fetch delivery, orders, cart, premium profile, announcements, etc. in one call
all_data = await client.get_data()
```

## Tracking a delivery

> [!NOTE]
> Delivery tracking uses an unofficial endpoint (`/api/v2/orders/{id}/delivery-tracking`)
> verified on Rohlík.cz during a single delivery; other shops are unverified. If a shop answers
> 404, `get_delivery_tracking` returns `None` and `get_next_delivery` falls back to the slot start;
> any other failure makes `get_next_delivery` raise. Behaviour for delayed or cancelled orders, several concurrent orders, express
> slots, and deliveries without an early-delivery request has not been observed yet.

```python
from rohlik_api import TrackingStatus

nxt = await client.orders.get_next_delivery()
if nxt is None:
    print("No upcoming order")
else:
    print(nxt.order.id, nxt.order.slot_since, nxt.order.items_total_quantity)
    print(nxt.status)                    # "IN_QUEUE", "ON_THE_WAY", "ARRIVED", ... or None
    print(nxt.eta, nxt.eta_source)       # aware datetime, "tracking" or "slot"
    if nxt.tracking:
        print(nxt.tracking.stops_before)       # stops before yours; 0 = you are next
        print(nxt.tracking.estimated_arrival)  # the courier estimate, uncapped
        if nxt.tracking.has_arrived:           # ARRIVED / HANDING_OVER
            print("The courier is at the door")
```

**Lifecycle.** `progress` (and so `status`) is `None` until the order is queued for a courier.
Then the status moves `IN_QUEUE` → `ON_THE_WAY` → `ARRIVED` → `HANDING_OVER` → `DELIVERED`
(see `TrackingStatus`; unknown values are kept as strings and count as active).
`estimated_arrival` can be missing early in the queue and keeps its last value after delivery,
so it is not the actual arrival time. `stops_before` is `0` when the courier is heading to you
and `None` once delivered. The courier position is reported from `ON_THE_WAY` through
`HANDING_OVER`.

The shop removes an order from the upcoming list within about a second of delivery, so
`get_next_delivery()` rarely reports `DELIVERED`: it returns `None` (or the next order). To observe
the final state, keep polling `get_delivery_tracking(order_id)` for the order you were tracking.

**ETA rule.** `NextDelivery.eta` is the courier estimate, except that while the order is still
`IN_QUEUE` it is never earlier than `DeliveryTracking.arrival_floor`. That is the slot start, or the
early-delivery start if the customer allowed early delivery, matching what the shop itself
shows. `eta_capped` tells when that happened. Once the courier is on the way the estimate is used
as served, so the ETA can move earlier at that moment (`eta_capped` turns `False`). Without an
estimate the slot start is used (`eta_source == "slot"`). This rule is a heuristic based on one
observed delivery.

If you already have the raw upcoming-orders list (for example `get_data()["next_order"]`) and a
tracking result, apply the same rule without extra requests:

```python
from rohlik_api import NextDelivery, UpcomingOrder

raw = data["next_order"]          # None if that request failed: keep your previous state
if raw is not None and (orders := UpcomingOrder.list_from_api(raw)):
    # raise_on_error=True: None then means only "no tracking for this order" (404)
    tracking = await client.orders.get_delivery_tracking(orders[0].id, raise_on_error=True)
    nxt = NextDelivery.resolve(orders[0], tracking)
```

`resolve` raises `ValueError` if the tracking belongs to a different order than the one passed,
for example a tracking result kept from a previous order after the upcoming list moved on.
(`get_next_delivery` reports that case as `APIRequestFailedError`.)

**Errors.** `get_delivery_tracking` and `get_upcoming` follow the usual read convention and return
`None` on failure (a 404, meaning the order has no tracking, is not logged as a warning). Pass
`raise_on_error=True` to `get_delivery_tracking` to get `APIRequestFailedError` on a failure
instead, so that `None` means only "no tracking". `get_next_delivery` always **raises** when either
request fails, so that a failure is never mistaken for "no upcoming order"; it returns `None` only
when there is no upcoming order.

**Freshness.** `DeliveryProgress.generated_at` is when the shop generated the snapshot. It can be
several minutes old while queued and stops changing after delivery. Polling about once a minute
was enough to catch every status change in the observed delivery.

**Courier on a map.** `DeliveryTracking.courier_position` is the courier's last reported location
(`latitude`, `longitude`, `recorded_at`), or `None`. In observed data the shop reports it from
`ON_THE_WAY` through `HANDING_OVER`. `DeliveryTracking.destination` is the delivery address as
coordinates, and `DeliveryTracking.courier_distance` the straight-line distance between the two in
metres (`None` unless both are known). It is not the driving distance. Out-of-range coordinates and
the `(0, 0)` placeholder are treated as missing. The position only changes as often as you poll,
and neither property checks staleness: when `progress.courier_location_stale` is `True` the shop
itself treats the position as outdated. `CourierPosition.distance_to()` accepts any object with
`latitude` and `longitude` (`GeoPoint`), for example your own home point.

```python
t = await client.orders.get_delivery_tracking(order_id)
if t and (pos := t.courier_position) and not t.progress.courier_location_stale:
    print(pos.latitude, pos.longitude, pos.recorded_at)
    if t.courier_distance is not None:
        print(f"{t.courier_distance / 1000:.1f} km away")
```

**Personal data.** `DeliveryTracking.courier_name`, `DeliveryProgress.courier_position` and
`DeliveryTracking.destination` are personal data (the courier's name and location, your address).
They are hidden from the models' `repr`, but `dataclasses.asdict` includes them, so redact them
before logging or sharing. The courier's phone number, photo and route geometry are not parsed at
all.

## Error handling

All errors derive from `RohlikAPIError`:

```python
from rohlik_api import RohlikAPI, InvalidCredentialsError, APIRequestFailedError

try:
    async with RohlikAPI(username="email@example.com", password="password") as client:
        cart = await client.cart.get_content()
except InvalidCredentialsError:
    print("Wrong username or password")
except APIRequestFailedError as err:
    print(f"Request failed: {err}")
```

**Error contract:**

- **Critical / mutating operations** (login, `cart.get_content`, `cart.delete_item`,
  `account.get_shopping_list`) **raise** `APIRequestFailedError` on failure.
  Login raises `InvalidCredentialsError` for a wrong email or password, and
  `RohlikAPIError` for any other status the shop reports.
- **Read / optional fetches** (most `orders`, `delivery`, `account`, `products`,
  and `recipes` getters) **return `None`** on failure, so an aggregate fetch can
  continue gracefully.
- **Batch operations** do not fail as a whole: `cart.add_items` returns only the
  IDs that were added (failures are logged), and `orders.get_all_delivered`
  returns the orders gathered so far if a page fails.
- `account.get_shopping_list` raises `ValueError` if called without an ID.

## Advanced usage

### Other shops

Rohlík Group runs the same API under several brands. `SITES` holds the known
shops (base URL, currency, timezone), keyed by country code:

| Code | Shop | Currency |
|------|------|----------|
| `cz` | Rohlík.cz (default) | CZK |
| `de` | Knuspr.de | EUR |
| `at` | Gurkerl.at | EUR |
| `hu` | Kifli.hu | HUF |
| `ro` | Sezamo.ro | RON |

```python
from rohlik_api import SITES, RohlikAPI

site = SITES["de"]
async with RohlikAPI("email@example.com", "password", base_url=site.base_url) as client:
    cart = await client.cart.get_content()
    print(cart.total_price, cart.currency or site.currency)  # e.g. 11.99 EUR
```

`Cart.currency` comes from the cart's items, so it is `None` for an empty cart
(or if no item reports one); fall back to `site.currency` then. Delivery
announcements and other texts come back in the shop's language.

### Configuration

```python
client = RohlikAPI(
    username="your_email@example.com",
    password="your_password",
    base_url="https://www.rohlik.cz",  # optional; e.g. SITES["de"].base_url
    timeout=30.0,                       # optional
    headers={"Custom-Header": "Value"}, # optional
    auto_login=True,                    # optional, default True
)
```

### Manual session management

```python
from rohlik_api import RohlikAPI

async def main():
    client = RohlikAPI(
        username="email@example.com",
        password="password",
        auto_login=False,  # disable auto-login
    )
    try:
        await client.login()
        print(client.is_logged_in, client.user_id, client.address_id)
        cart = await client.cart.get_content()
        await client.logout()
    finally:
        await client.close()
```

### Reusing an existing aiohttp session

The client is built on [aiohttp](https://docs.aiohttp.org/). By default it
creates and owns its own `ClientSession`, but you can inject an externally
managed session instead — useful inside a Home Assistant integration, where
the recommended pattern is to share a single session per instance. An injected
session is **never** closed by the client; its lifecycle stays with the owner.

```python
import aiohttp
from rohlik_api import RohlikAPI

async def main(session: aiohttp.ClientSession):
    client = RohlikAPI(
        username="email@example.com",
        password="password",
        session=session,  # reuse the caller's session
    )
    async with client:
        cart = await client.cart.get_content()
    # `session` is left open for the caller to close.
```

Inside a Home Assistant integration you would pass the shared session, for
example `RohlikAPI(..., session=async_get_clientsession(hass))`.

## Development

```bash
# Install with development dependencies
pip install -e ".[dev]"

# Run the test suite
pytest

# Lint, format check and type check
ruff check .
black --check .
mypy rohlik_api
```

Please make sure `pytest`, `ruff`, `black` and `mypy` all pass before opening a
pull request.

## Disclaimer

This project is an **independent, unofficial** client. It is **not affiliated
with, authorized by, or endorsed by Rohlik.cz, Rohlik Group, or any of its
subsidiaries**. "Rohlik", "Rohlik.cz" and "Rohlík Chef" are trademarks of their
respective owners.

It talks to a **private, undocumented API** that may change or stop working at
any time. It is provided for **personal, non-commercial use** only, and comes
with **no warranty of any kind**. You are responsible for complying with
Rohlik.cz's Terms of Service and applicable law. **Use at your own risk.**

## License

[MIT](LICENSE) © Daniel Vejsada
