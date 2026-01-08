"""Example usage of the Rohlik API client."""

import asyncio
from rohlik_api import RohlikAPI, InvalidCredentialsError, APIRequestFailedError


async def main():
    """Demonstrate basic usage of the Rohlik API client."""
    print("Rohlik API Client Example")
    print("=" * 60)

    # Replace with your actual credentials
    USERNAME = "your_email@example.com"
    PASSWORD = "your_password"

    # -------------------------------------------------------------------------
    # Example 1: Using async context manager (recommended)
    # -------------------------------------------------------------------------
    print("\n[Example 1] Using async context manager with auto-login")
    print("-" * 60)

    # For demo purposes, we disable auto_login. In real usage, omit auto_login=False
    async with RohlikAPI(username=USERNAME, password=PASSWORD, auto_login=False) as client:
        print(f"Client initialized with base URL: {client.base_url}")
        print(f"Is logged in: {client.is_logged_in}")  # False because auto_login=False

        # With real credentials, use auto_login=True (default):
        # async with RohlikAPI(username=USERNAME, password=PASSWORD) as client:
        #     # client.is_logged_in is True - auto-login happened!
        #
        #     # Get cart contents
        #     cart = await client.get_cart_content()
        #     print(f"Cart total: {cart['total_price']} CZK")
        #     print(f"Items in cart: {cart['total_items']}")
        #
        #     # Get delivery information
        #     delivery = await client.get_delivery_info()
        #     print(f"Delivery info: {delivery}")
        #
        #     # Search for products
        #     results = await client.search_product("mleko", limit=5)
        #     if results:
        #         print(f"Found {len(results['search_results'])} products:")
        #         for product in results['search_results']:
        #             print(f"  - {product['name']} ({product['price']})")

        print("(Requires valid credentials to run)")
        # Logout is called automatically when exiting the context manager

    # -------------------------------------------------------------------------
    # Example 2: Get all account data at once
    # -------------------------------------------------------------------------
    print("\n[Example 2] Get all account data at once")
    print("-" * 60)

    async with RohlikAPI(username=USERNAME, password=PASSWORD, auto_login=False) as client:
        # Uncomment to test with real credentials:
        # try:
        #     # get_data() fetches everything (login already done automatically)
        #     data = await client.get_data()
        #     print(f"Login status: {data.get('login', {}).get('status')}")
        #     print(f"Cart: {data.get('cart')}")
        #     print(f"Delivery: {data.get('delivery')}")
        #     print(f"Next order: {data.get('next_order')}")
        #     print(f"Premium profile: {data.get('premium_profile')}")
        # except Exception as e:
        #     print(f"Error: {e}")

        print("get_data() fetches all account data in one call")
        print("(Requires valid credentials to run)")

    # -------------------------------------------------------------------------
    # Example 3: Cart operations
    # -------------------------------------------------------------------------
    print("\n[Example 3] Cart operations")
    print("-" * 60)

    async with RohlikAPI(username=USERNAME, password=PASSWORD, auto_login=False) as client:
        # Uncomment to test with real credentials:
        # # Add products to cart
        # products_to_add = [
        #     {"product_id": 1234567, "quantity": 2},
        #     {"product_id": 7654321, "quantity": 1}
        # ]
        # result = await client.add_to_cart(products_to_add)
        # print(f"Added products: {result['added_products']}")
        #
        # # Get current cart
        # cart = await client.get_cart_content()
        # for product in cart['products']:
        #     print(f"  - {product['name']}: {product['quantity']}x ({product['price']} CZK)")
        #
        # # Delete item from cart (using cart_item_id from get_cart_content)
        # if cart['products']:
        #     item_to_delete = cart['products'][0]['cart_item_id']
        #     await client.delete_from_cart(item_to_delete)
        #     print(f"Deleted item: {item_to_delete}")

        print("Cart operations: add_to_cart(), get_cart_content(), delete_from_cart()")
        print("(Requires valid credentials to run)")

    # -------------------------------------------------------------------------
    # Example 4: Delivery and orders
    # -------------------------------------------------------------------------
    print("\n[Example 4] Delivery and orders")
    print("-" * 60)

    async with RohlikAPI(username=USERNAME, password=PASSWORD, auto_login=False) as client:
        # Uncomment to test with real credentials:
        # # Get delivery info
        # delivery = await client.get_delivery_info()
        # print(f"Delivery info: {delivery}")
        #
        # # Get timeslot reservation
        # timeslot = await client.get_timeslot_reservation()
        # print(f"Timeslot: {timeslot}")
        #
        # # Get next upcoming order
        # next_order = await client.get_next_order()
        # print(f"Next order: {next_order}")
        #
        # # Get last delivered order
        # last_order = await client.get_last_order()
        # print(f"Last order: {last_order}")
        #
        # # Get history of delivered orders
        # orders = await client.get_delivered_orders(limit=10)
        # print(f"Delivered orders count: {len(orders) if orders else 0}")

        print("Delivery methods: get_delivery_info(), get_timeslot_reservation()")
        print("Order methods: get_next_order(), get_last_order(), get_delivered_orders()")
        print("(Requires valid credentials to run)")

    # -------------------------------------------------------------------------
    # Example 5: Account information
    # -------------------------------------------------------------------------
    print("\n[Example 5] Account information")
    print("-" * 60)

    async with RohlikAPI(username=USERNAME, password=PASSWORD, auto_login=False) as client:
        # Uncomment to test with real credentials:
        # # Get premium profile (Rohlik Premium subscription)
        # premium = await client.get_premium_profile()
        # print(f"Premium profile: {premium}")
        #
        # # Get reusable bags info
        # bags = await client.get_bags_info()
        # print(f"Bags info: {bags}")
        #
        # # Get announcements
        # announcements = await client.get_announcements()
        # print(f"Announcements: {announcements}")
        #
        # # Get delivery announcements
        # delivery_announcements = await client.get_delivery_announcements()
        # print(f"Delivery announcements: {delivery_announcements}")

        print("Account methods: get_premium_profile(), get_bags_info()")
        print("Announcement methods: get_announcements(), get_delivery_announcements()")
        print("(Requires valid credentials to run)")

    # -------------------------------------------------------------------------
    # Example 6: Shopping lists
    # -------------------------------------------------------------------------
    print("\n[Example 6] Shopping lists")
    print("-" * 60)

    async with RohlikAPI(username=USERNAME, password=PASSWORD, auto_login=False) as client:
        # Uncomment to test with real credentials:
        # # Get a shopping list by ID
        # shopping_list = await client.get_shopping_list("your-shopping-list-id")
        # print(f"Shopping list: {shopping_list['name']}")
        # print(f"Products: {shopping_list['products_in_list']}")

        print("Shopping list methods: get_shopping_list(shopping_list_id)")
        print("(Requires valid credentials to run)")

    # -------------------------------------------------------------------------
    # Example 7: Manual session management (without context manager)
    # -------------------------------------------------------------------------
    print("\n[Example 7] Manual session management (without context manager)")
    print("-" * 60)

    client = RohlikAPI(username=USERNAME, password=PASSWORD, auto_login=False)
    try:
        # Uncomment to test with real credentials:
        # # When not using context manager, you must call login() manually
        # await client.login()
        # print(f"Logged in: {client.is_logged_in}")
        #
        # # Perform operations...
        # cart = await client.get_cart_content()
        #
        # # Explicit logout when done
        # await client.logout()
        # print(f"Logged out: {not client.is_logged_in}")

        print("Without context manager, call login() and logout() manually")
        print("(Requires valid credentials to run)")
    finally:
        await client.close()

    # -------------------------------------------------------------------------
    # Summary
    # -------------------------------------------------------------------------
    print("\n" + "=" * 60)
    print("All examples completed!")
    print("\nTo use this API client:")
    print("1. Replace USERNAME and PASSWORD with your Rohlik.cz credentials")
    print("2. Uncomment the example code sections you want to run")
    print("3. Run: python example.py")


if __name__ == "__main__":
    asyncio.run(main())
