# 🛒 Rohlik API Python Client

An async, fully typed Python client for the [Rohlik.cz](https://www.rohlik.cz)
online grocery service — search products, manage your cart, browse recipes
(Rohlík Chef), and read your orders and deliveries, all from Python.

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
- 🌍 Works with every Rohlík Group shop: Rohlík.cz, Knuspr.de, Gurkerl.at, Kifli.hu and Sezamo.ro

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

The client authenticates with your normal Rohlik.cz **email and password**.

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

- Credentials are only ever sent to Rohlik.cz over HTTPS. This library does not
  store or transmit them anywhere else.
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

Raw passthrough endpoints (`orders.*`, `delivery.*`, `account.get_premium_profile`,
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
for product in results.results:  # ProductSearchResult: id, name, price, brand, amount
    print(product.name, product.price)

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
```

### Orders service (`client.orders`)

```python
next_order = await client.orders.get_next()                       # upcoming order
last_order = await client.orders.get_last()                       # last delivered order
orders = await client.orders.get_delivered(limit=50, offset=0)    # one history page
all_orders = await client.orders.get_all_delivered()              # every page, paginated
detail = await client.orders.get_detail(order_id=12345678)        # full order incl. items
```

### Delivery service (`client.delivery`)

```python
delivery = await client.delivery.get_info()
timeslot = await client.delivery.get_timeslot_reservation()
slots = await client.delivery.get_next_slots()
announcements = await client.delivery.get_announcements()
```

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
- **Read / optional fetches** (most `orders`, `delivery`, `account`, `products`,
  and `recipes` getters) **return `None`** on failure, so an aggregate fetch can
  continue gracefully.

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

`Cart.currency` comes from the cart's items, so it is `None` for an empty cart (or if no item reports one);
fall back to `site.currency` then. Delivery announcements and other texts come
back in the shop's language.

### Configuration

```python
client = RohlikAPI(
    username="your_email@example.com",
    password="your_password",
    base_url="https://www.rohlik.cz",  # optional
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
