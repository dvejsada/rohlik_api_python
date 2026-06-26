"""Example usage of the Rohlik API client.

Replace USERNAME and PASSWORD with your real Rohlik.cz credentials and run:

    python example.py

The network calls are commented out so the file runs without credentials.
Uncomment the blocks you want to exercise once you have set your credentials.
"""

import asyncio

from rohlik_api import APIRequestFailedError, InvalidCredentialsError, RohlikAPI

USERNAME = "your_email@example.com"
PASSWORD = "your_password"


async def main() -> None:
    """Demonstrate the service-based API of the Rohlik client."""
    # The recommended pattern: an async context manager with auto-login.
    # On entry it logs in; on exit it logs out and releases resources.
    async with RohlikAPI(username=USERNAME, password=PASSWORD) as client:
        print(f"Logged in: {client.is_logged_in}")
        print(f"User ID: {client.user_id}, Address ID: {client.address_id}")

        # --- Products ------------------------------------------------------
        results = await client.products.search("mleko", limit=5)
        if results:
            for product in results["search_results"]:
                print(f"  {product['name']} - {product['price']}")

        # composition = await client.products.get_composition(product_id=1425155)
        # price = await client.products.get_price(product_id=1425155)
        # summary = await client.products.get_ai_summary(product_id=1384964)

        # --- Cart ----------------------------------------------------------
        cart = await client.cart.get_content()
        print(f"Cart total: {cart['total_price']} ({cart['total_items']} items)")

        # await client.cart.add_items([{"product_id": 1234567, "quantity": 2}])
        # if cart["products"]:
        #     await client.cart.delete_item(cart["products"][0]["cart_item_id"])

        # --- Delivery & orders --------------------------------------------
        # delivery = await client.delivery.get_info()
        # slots = await client.delivery.get_next_slots()
        # next_order = await client.orders.get_next()
        # history = await client.orders.get_delivered(limit=10)

        # --- Account -------------------------------------------------------
        # premium = await client.account.get_premium_profile()
        # bags = await client.account.get_bags_info()
        # shopping_list = await client.account.get_shopping_list("list-id")

        # --- Recipes (Rohlík Chef) ----------------------------------------
        recipes = await client.recipes.search("rajská", limit=5)
        if recipes:
            print(f"Found {recipes['total_hits']} recipes")
        # detail = await client.recipes.get_detail(recipe_id=59)
        # products = await client.recipes.get_ingredient_products([102, 56], limit=5)

        # --- Aggregated snapshot ------------------------------------------
        # all_data = await client.get_data()


async def manual_session() -> None:
    """Demonstrate manual session management without the context manager."""
    client = RohlikAPI(username=USERNAME, password=PASSWORD, auto_login=False)
    try:
        await client.login()
        cart = await client.cart.get_content()
        print(f"Cart total: {cart['total_price']}")
        await client.logout()
    finally:
        await client.close()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except InvalidCredentialsError:
        print("Invalid credentials - set USERNAME and PASSWORD in example.py")
    except APIRequestFailedError as err:
        print(f"Request failed: {err}")
