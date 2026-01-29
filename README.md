# Rohlik API Python Client

An async Python client library for interacting with the Rohlik.cz API using httpx with HTTP/2 support.

## Features

- 🚀 HTTP/2 support for improved performance
- 🔐 Secure authentication with automatic session management
- 🎯 Clean service-based API architecture
- 🔄 Async context manager support
- 🍳 Recipe search and ingredient products (Rohlík Chef)
- 📦 Product details, composition, and AI summaries

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

```python
from rohlik_api import RohlikAPI, InvalidCredentialsError, APIRequestFailedError, RohlikAPIError

async def main():
    try:
        async with RohlikAPI(username="email@example.com", password="password") as client:
            cart = await client.cart.get_content()
    except InvalidCredentialsError as e:
        print(f"Invalid credentials: {e}")
    except APIRequestFailedError as e:
        print(f"API request failed: {e}")
    except RohlikAPIError as e:
        print(f"General API error: {e}")
```

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
        await client._auth.login()
        cart = await client.cart.get_content()
        await client._auth.logout()
    finally:
        await client.close()
```

### Access Low-Level Components

```python
from rohlik_api import HttpClient, AuthManager, Endpoints

# Use Endpoints for URL building
url = Endpoints.product_price(1425155)
url = Endpoints.recipe_search("polévka", limit=5)
url = Endpoints.delivered_orders(limit=10, offset=0)
```

## Development

### Setup Development Environment

```bash
# Clone the repository
git clone https://github.com/dvejsada/rohlik_api_python.git
cd rohlik_api_python

# Install development dependencies
pip install -e ".[dev]"
```

### Running Tests

```bash
pytest
```

### Code Formatting

```bash
black rohlik_api
ruff check rohlik_api
```

## Requirements

- Python >= 3.8
- httpx[http2] >= 0.24.0

## License

MIT License - see LICENSE file for details.

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## Changelog

### 0.2.0 (2026-01-29)

- **Breaking Change**: Refactored to service-based architecture
- New services: `cart`, `products`, `orders`, `delivery`, `account`, `recipes`
- Added Recipe service for Rohlík Chef (search, details, ingredient products)
- Added Product details: AI summary, composition, price endpoints
- Removed legacy methods in favor of service-based API
- Improved code organization and maintainability

### 0.1.0 (2026-01-08)

- Initial release
- Async API client with HTTP/2 support
- Authentication with persistent sessions
- Product search, cart management, and delivery information
- Context manager support
