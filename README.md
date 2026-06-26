# Rohlik API Python Client

An async Python client library for interacting with the Rohlik.cz API using httpx with HTTP/2 support.

## Features

- 🚀 HTTP/2 support for improved performance
- 🔐 Secure authentication with automatic session management
- 🎯 Clean service-based API architecture
- 🧩 Typed dataclass models for all parsed responses (fully type-hinted, `py.typed`)
- 🔄 Async context manager support
- 🍳 Recipe search and ingredient products (Rohlík Chef)
- 📦 Product details, composition, and AI summaries

## Requirements

- Python 3.13+
- [httpx](https://www.python-httpx.org/) with HTTP/2 support (installed automatically)

> **Disclaimer:** This is an unofficial client for the non-public Rohlik.cz API
> and is not affiliated with or endorsed by Rohlik.cz. The API may change without
> notice.

## Installation

```bash
pip install rohlik-api
```

## Quick Start

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

## Typed Models

Service methods that parse responses return typed dataclasses (importable from
`rohlik_api`) rather than raw dictionaries, so editors and type checkers know the
shape of the data:

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

## Configuration

```python
from rohlik_api import RohlikAPI

client = RohlikAPI(
    username="your_email@example.com",
    password="your_password",
    base_url="https://www.rohlik.cz",  # Optional
    timeout=30.0,                       # Optional
    headers={"Custom-Header": "Value"}, # Optional
    auto_login=True                     # Optional, default True
)
```

## Services

The client provides access to functionality through service properties:

| Service | Property | Description |
|---------|----------|-------------|
| Cart | `client.cart` | Shopping cart operations |
| Products | `client.products` | Product search and details |
| Orders | `client.orders` | Order history |
| Delivery | `client.delivery` | Delivery info and timeslots |
| Account | `client.account` | Account data and shopping lists |
| Recipes | `client.recipes` | Recipe search and ingredients (Rohlík Chef) |

## API Reference

### Cart Service (`client.cart`)

```python
# Get cart contents
cart = await client.cart.get_content()
# -> Cart(total_price=199.90, total_items=3, can_make_order=True, products=[CartItem, ...])

# Add items to cart
added = await client.cart.add_items([
    {"product_id": 123456, "quantity": 2},
    {"product_id": 789012, "quantity": 1}
])
# -> [123456, 789012]   (list of product IDs successfully added)

# Delete item from cart (raises APIRequestFailedError on failure)
await client.cart.delete_item(order_field_id="abc123")
```

### Products Service (`client.products`)

```python
# Search for products -> SearchResults | None (None only on request failure)
results = await client.products.search("mléko", limit=10, favourite=False)
for product in results.results:  # ProductSearchResult: id, name, price, brand, amount
    print(product.name, product.price)

# Get AI-generated product summary -> AISummary | None
summary = await client.products.get_ai_summary(product_id=1384964)
# AISummary(product_id=1384964, rating=..., title="AI Souhrn", content="...")

# Get product composition -> ProductComposition | None
composition = await client.products.get_composition(product_id=1425155)
# ProductComposition(product_id, nutritional_values=[NutritionalValue, ...],
#                    ingredients="...", allergens=Allergens(contained, possibly_contained))

# Get product price -> ProductPrice | None
price = await client.products.get_price(product_id=1425155)
# ProductPrice(product_id=1425155, price=40.9, currency="CZK", price_per_unit=340.83, sales=[])
```

### Orders Service (`client.orders`)

```python
# Get next (upcoming) order
next_order = await client.orders.get_next()

# Get last delivered order
last_order = await client.orders.get_last()

# Get delivered orders with pagination
orders = await client.orders.get_delivered(limit=50, offset=0)
```

### Delivery Service (`client.delivery`)

```python
# Get delivery information
delivery = await client.delivery.get_info()

# Get current timeslot reservation
timeslot = await client.delivery.get_timeslot_reservation()

# Get next available delivery slots
slots = await client.delivery.get_next_slots()

# Get delivery announcements
announcements = await client.delivery.get_announcements()
```

### Account Service (`client.account`)

```python
# Get premium profile
premium = await client.account.get_premium_profile()

# Get reusable bags info
bags = await client.account.get_bags_info()

# Get announcements
announcements = await client.account.get_announcements()

# Get shopping list by ID -> ShoppingList
shopping_list = await client.account.get_shopping_list("list_id_here")
# ShoppingList(name="My List", products_in_list=[...])
```

### Recipes Service (`client.recipes`)

```python
# Search for recipes
recipes = await client.recipes.search("rajská", limit=10, offset=0)
# -> RecipeSearchResults(recipes=[RecipeSummary, ...], total_hits=4)

# Get recipe details -> RecipeDetail | None
recipe = await client.recipes.get_detail(recipe_id=59)
# RecipeDetail(id=59, name="...", ingredients=[IngredientGroup, ...],
#              directions=[DirectionSection, ...], author=RecipeAuthor, ...)

# Get products for ingredients -> IngredientProducts | None
products = await client.recipes.get_ingredient_products(ingredient_ids=[102, 56], limit=5)
# IngredientProducts(ingredients=[IngredientProductGroup(ingredient_id, products, total_hits)])
```

### Aggregated Data

```python
# Get all account data in a single operation
all_data = await client.get_data()
# Returns dict with: login, delivery, next_order, last_order, cart, premium_profile, etc.
```

## Error Handling

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

Note on the error contract:

- **Write/critical operations** (login, `cart.get_content`, `cart.delete_item`,
  `account.get_shopping_list`) **raise** `APIRequestFailedError` on failure.
- **Read/optional fetches** (most `orders`, `delivery`, `account`, `products`,
  and `recipes` getters) **return `None`** on failure so an aggregate fetch can
  continue gracefully.

## Advanced Usage

### Manual Session Management

```python
from rohlik_api import RohlikAPI

async def main():
    client = RohlikAPI(
        username="email@example.com",
        password="password",
        auto_login=False  # Disable auto-login
    )
    try:
        await client.login()
        cart = await client.cart.get_content()
        await client.logout()
    finally:
        await client.close()
```

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

## License

MIT License - see LICENSE file for details.

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request. Make sure
`pytest`, `ruff`, `black` and `mypy` all pass before opening one.
