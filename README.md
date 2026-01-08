# Rohlik API Python Client

An async Python client library for interacting with the Rohlik.cz API using httpx with HTTP/2 support.

## Features

- 🚀 HTTP/2 support for improved performance
- 🔐 Secure authentication with persistent sessions
- 🔒 Type hints for better IDE support
- 🎯 Simple and intuitive async API
- 🔄 Async context manager support
- 📦 Ready for PyPI distribution

## Installation

```bash
pip install rohlik-api
```

## Quick Start

```python
import asyncio
from rohlik_api import RohlikAPI

async def main():
    # Login happens automatically when entering the context manager
    async with RohlikAPI(username="your_email@example.com", password="your_password") as client:
        # No need to call login() - it's automatic!
        
        # Search for products
        results = await client.search_product("mleko", limit=5)
        print(f"Search results: {results}")
        
        # Get cart contents
        cart = await client.get_cart_content()
        print(f"Cart: {cart}")
        
        # Get delivery information
        delivery = await client.get_delivery_info()
        print(f"Delivery: {delivery}")
        
        # Logout is called automatically when exiting context manager

asyncio.run(main())
```

### Using Context Manager (Recommended)

```python
import asyncio
from rohlik_api import RohlikAPI

async def main():
    # Auto-login on enter, auto-logout on exit
    async with RohlikAPI(username="email@example.com", password="password") as client:
        cart = await client.get_cart_content()

asyncio.run(main())
```

### Manual Session Management

```python
import asyncio
from rohlik_api import RohlikAPI

async def main():
    client = RohlikAPI(username="email@example.com", password="password")
    try:
        # Without context manager, you must call login() manually
        await client.login()
        cart = await client.get_cart_content()
        await client.logout()
    finally:
        await client.close()

asyncio.run(main())
```

## Configuration

You can customize the client behavior:

```python
from rohlik_api import RohlikAPI

client = RohlikAPI(
    username="your_email@example.com",
    password="your_password",
    base_url="https://www.rohlik.cz",
    timeout=30.0,
    headers={
        "Custom-Header": "Value"
    }
)
```

## API Methods

### Authentication

- `login()` - Authenticate with Rohlik.cz
- `logout()` - Log out from the service
- `is_logged_in` - Property to check login status

### Products

- `search_product(product_name, limit=10, favourite=False)` - Search for products by name

### Cart

- `get_cart_content()` - Get current cart contents
- `add_to_cart(product_list)` - Add products to cart (list of `{product_id, quantity}`)
- `delete_from_cart(order_field_id)` - Remove item from cart

### Shopping Lists

- `get_shopping_list(shopping_list_id)` - Get shopping list by ID

### Delivery & Orders

- `get_delivery_info()` - Get first delivery information
- `get_next_order()` - Get upcoming order information
- `get_last_order()` - Get last delivered order
- `get_delivered_orders(limit=50, offset=0)` - Get list of delivered orders
- `get_timeslot_reservation()` - Get current timeslot reservation

### Account

- `get_premium_profile()` - Get premium profile information
- `get_bags_info()` - Get reusable bags user information
- `get_announcements()` - Get top announcements
- `get_delivery_announcements()` - Get delivery announcements
- `get_data()` - Get all account data in a single operation

## Error Handling

```python
from rohlik_api import RohlikAPI, InvalidCredentialsError, APIRequestFailedError

async def main():
    async with RohlikAPI(username="email@example.com", password="password") as client:
        try:
            await client.login()
            cart = await client.get_cart_content()
        except InvalidCredentialsError as e:
            print(f"Invalid credentials: {e}")
        except APIRequestFailedError as e:
            print(f"API request failed: {e}")
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
# Format code with black
black rohlik_api

# Lint with ruff
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

### 0.1.0 (2026-01-08)

- Initial release
- Async API client with HTTP/2 support
- Authentication with persistent sessions
- Product search, cart management, and delivery information
- Context manager support
