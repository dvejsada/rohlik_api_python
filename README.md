# Rohlik API Python Client

A Python client library for interacting with the Rohlik.cz API using httpx with HTTP/2 support.

## Features

- 🚀 HTTP/2 support for improved performance
- 🔒 Type hints for better IDE support
- 🎯 Simple and intuitive API
- 🔄 Context manager support
- 📦 Ready for PyPI distribution

## Installation

```bash
pip install rohlik-api
```

## Quick Start

```python
from rohlik_api import RohlikAPI

# Create a client instance
client = RohlikAPI()

# Make API calls
try:
    # Get categories
    categories = client.get_categories()
    print(f"Found {len(categories)} categories")
    
    # Search for products
    products = client.get_products(search="mleko", limit=10)
    print(f"Found {len(products)} products")
    
    # Get specific product
    product = client.get_product(12345)
    print(f"Product: {product}")
finally:
    client.close()
```

### Using Context Manager

```python
from rohlik_api import RohlikAPI

with RohlikAPI() as client:
    categories = client.get_categories()
    products = client.get_products(search="mleko")
```

## Configuration

You can customize the client behavior:

```python
from rohlik_api import RohlikAPI

client = RohlikAPI(
    base_url="https://www.rohlik.cz",
    timeout=30.0,
    headers={
        "Custom-Header": "Value"
    }
)
```

## API Methods

### Basic HTTP Methods

- `get(endpoint, params=None, headers=None)` - Make GET request
- `post(endpoint, data=None, json=None, headers=None)` - Make POST request
- `put(endpoint, data=None, json=None, headers=None)` - Make PUT request
- `delete(endpoint, headers=None)` - Make DELETE request

### High-Level Methods

- `get_categories()` - Get list of product categories
- `get_products(category_id=None, search=None, limit=50, offset=0)` - Get products
- `get_product(product_id)` - Get specific product details

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
- Basic API client with HTTP/2 support
- Category and product retrieval methods
- Context manager support
