"""Example usage of the Rohlik API client."""

from rohlik_api import RohlikAPI


def main():
    """Demonstrate basic usage of the Rohlik API client."""
    print("Rohlik API Client Example")
    print("-" * 50)
    
    # Example 1: Using context manager (recommended)
    print("\nExample 1: Using context manager")
    with RohlikAPI() as client:
        print(f"Client initialized with base URL: {client.base_url}")
        print("HTTP/2 support is enabled in the client")
    
    # Example 2: Manual client management
    print("\nExample 2: Manual client management")
    client = RohlikAPI(
        base_url="https://www.rohlik.cz",
        timeout=30.0
    )
    
    try:
        print(f"Client initialized successfully")
        print(f"Timeout: {client.timeout}s")
        
        # Note: The following methods will fail without proper API endpoints
        # They are provided as examples of how to use the client
        
        # Example API calls (commented out as they require actual API endpoints)
        # categories = client.get_categories()
        # print(f"Categories: {categories}")
        
        # products = client.get_products(search="mleko", limit=5)
        # print(f"Products: {products}")
        
        print("\nClient is ready to make API calls!")
        
    except Exception as e:
        print(f"Error: {e}")
    finally:
        client.close()
        print("\nClient closed successfully")
    
    # Example 3: Custom headers
    print("\nExample 3: Custom headers")
    custom_client = RohlikAPI(
        headers={
            "X-Custom-Header": "CustomValue",
            "Authorization": "Bearer token123",
        }
    )
    print(f"Custom headers set: {list(custom_client.client.headers.keys())}")
    custom_client.close()


if __name__ == "__main__":
    main()
