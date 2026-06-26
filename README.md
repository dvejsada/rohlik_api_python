# Rohlik API Python Client

An async Python client library for interacting with the Rohlik.cz API using httpx with HTTP/2 support.

## Features

- 🚀 HTTP/2 support for improved performance
- 🔐 Secure authentication with automatic session management
- 🎯 Clean service-based API architecture
- 🔄 Async context manager support
- 🍳 Recipe search and ingredient products (Rohlík Chef)
- 📦 Product details, composition, and AI summaries

## Requirements

- Python 3.11+
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
        # Search for products
        results = await client.products.search("mleko", limit=5)
        print(f"Search results: {results}")
        
        # Get cart contents
        cart = await client.cart.get_content()
        print(f"Cart: {cart}")
        
        # Get delivery information
        delivery = await client.delivery.get_info()
        print(f"Delivery: {delivery}")
        
        # Search recipes
        recipes = await client.recipes.search("rajská", limit=5)
        print(f"Recipes: {recipes}")

asyncio.run(main())
```

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
# Returns: {"total_price": 199.90, "total_items": 3, "can_make_order": True, "products": [...]}

# Add items to cart
result = await client.cart.add_items([
    {"product_id": 123456, "quantity": 2},
    {"product_id": 789012, "quantity": 1}
])
# Returns: {"added_products": [123456, 789012]}

# Delete item from cart
await client.cart.delete_item(order_field_id="abc123")
```

### Products Service (`client.products`)

```python
# Search for products
results = await client.products.search("mléko", limit=10, favourite=False)
# Returns: {"search_results": [{"id": 123, "name": "...", "price": "29.90 Kč", ...}]}

# Get AI-generated product summary
summary = await client.products.get_ai_summary(product_id=1384964)
# Returns: {"product_id": 1384964, "title": "AI Souhrn", "content": "..."}

# Get product composition (nutritional values, allergens)
composition = await client.products.get_composition(product_id=1425155)
# Returns: {"nutritional_values": [...], "ingredients": "...", "allergens": {...}}

# Get product price
price = await client.products.get_price(product_id=1425155)
# Returns: {"product_id": 1425155, "price": 40.9, "currency": "CZK", "price_per_unit": 340.83}
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

# Get shopping list by ID
shopping_list = await client.account.get_shopping_list("list_id_here")
# Returns: {"name": "My List", "products_in_list": [...]}
```

### Recipes Service (`client.recipes`)

```python
# Search for recipes
recipes = await client.recipes.search("rajská", limit=10, offset=0)
# Returns: {"recipes": [{"id": 59, "name": "Rajská omáčka", "image": "...", ...}], "total_hits": 4}

# Get recipe details
recipe = await client.recipes.get_detail(recipe_id=59)
# Returns: {"id": 59, "name": "...", "ingredients": [...], "directions": [...], ...}

# Get products for ingredients
products = await client.recipes.get_ingredient_products(ingredient_ids=[102, 56], limit=5)
# Returns: {"ingredients": [{"ingredient_id": 102, "products": [...], "total_hits": 3}]}
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
