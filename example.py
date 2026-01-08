"""Example usage of the Rohlik API client."""

import asyncio
from rohlik_api import RohlikAPI, InvalidCredentialsError, APIRequestFailedError


async def main():
    """Demonstrate basic usage of the Rohlik API client."""
    print("Rohlik API Client Example")
    print("-" * 50)
    
    # Replace with your actual credentials
    USERNAME = "your_email@example.com"
    PASSWORD = "your_password"

    # Example 1: Using async context manager (recommended)
    # The client maintains a persistent session - login once, use many times
    print("\nExample 1: Using async context manager with persistent session")
    async with RohlikAPI(username=USERNAME, password=PASSWORD) as client:
        print(f"Client initialized with base URL: {client.base_url}")
        print(f"Is logged in: {client.is_logged_in}")  # False initially

        # Note: Uncomment the following to test with real credentials
        # try:
        #     # Login once - session persists for all subsequent calls
        #     await client.login()
        #     print(f"Is logged in: {client.is_logged_in}")  # True after login
        #
        #     # Make multiple API calls without re-authenticating
        #     cart = await client.get_cart_content()
        #     print(f"Cart: {cart}")
        #
        #     delivery = await client.get_delivery_info()
        #     print(f"Delivery: {delivery}")
        #
        #     # Search products
        #     results = await client.search_product("mleko", limit=5)
        #     print(f"Search results: {results}")
        #
        # except InvalidCredentialsError as e:
        #     print(f"Invalid credentials: {e}")
        # except APIRequestFailedError as e:
        #     print(f"API request failed: {e}")

        # Logout is called automatically when exiting the context manager

    # Example 2: Get all data at once
    print("\nExample 2: Get all account data")
    async with RohlikAPI(username=USERNAME, password=PASSWORD) as client:
        # Note: Uncomment to test with real credentials
        # try:
        #     # get_data() handles login automatically
        #     data = await client.get_data()
        #     print(f"Login: {data.get('login')}")
        #     print(f"Cart: {data.get('cart')}")
        #     print(f"Delivery: {data.get('delivery')}")
        # except Exception as e:
        #     print(f"Error: {e}")
        print("get_data() ready (requires valid credentials)")

    # Example 3: Manual session management
    print("\nExample 3: Manual session management")
    client = RohlikAPI(username=USERNAME, password=PASSWORD)
    try:
        # Note: Uncomment to test with real credentials
        # await client.login()
        # print(f"Logged in: {client.is_logged_in}")
        #
        # # Do multiple operations...
        # cart = await client.get_cart_content()
        # orders = await client.get_delivered_orders(limit=5)
        #
        # # Explicit logout when done
        # await client.logout()
        # print(f"Logged out: {not client.is_logged_in}")
        print("Manual session management ready (requires valid credentials)")
    finally:
        await client.close()

    print("\n" + "-" * 50)
    print("All examples completed!")
    print("To use this API client, replace USERNAME and PASSWORD with your actual Rohlik.cz credentials.")


if __name__ == "__main__":
    asyncio.run(main())
