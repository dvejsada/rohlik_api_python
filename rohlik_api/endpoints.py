"""API endpoint definitions for Rohlik.cz."""

BASE_URL = "https://www.rohlik.cz"


class Endpoints:
    """API endpoint paths for Rohlik.cz."""

    # Authentication
    LOGIN = "/services/frontend-service/login"
    LOGOUT = "/services/frontend-service/logout"

    # Cart
    CART = "/services/frontend-service/v2/cart"

    # Products
    SEARCH = "/services/frontend-service/search-metadata"

    # Shopping Lists
    SHOPPING_LIST = "/api/v1/shopping-lists/id/{shopping_list_id}"

    # Delivery
    DELIVERY = "/services/frontend-service/first-delivery?reasonableDeliveryTime=true"
    TIMESLOT_RESERVATION = "/services/frontend-service/v1/timeslot-reservation"
    TIMESLOTS_BASE = "/services/frontend-service/timeslots-api/"
    DELIVERY_ANNOUNCEMENTS = "/services/frontend-service/announcements/delivery"

    # Orders
    NEXT_ORDER = "/api/v3/orders/upcoming"
    LAST_ORDER = "/api/v3/orders/delivered?offset=0&limit=1"
    DELIVERED_ORDERS = "/api/v3/orders/delivered"

    # Account
    PREMIUM_PROFILE = "/services/frontend-service/premium/profile"
    BAGS = "/api/v1/reusable-bags/user-info"
    ANNOUNCEMENTS = "/services/frontend-service/announcements/top"

    # Recipes
    RECIPE_SEARCH = "/services/frontend-service/recipe/search/{query}"
    RECIPE_DETAIL = "/services/frontend-service/recipe/{recipe_id}"
    INGREDIENT_PRODUCTS = "/services/frontend-service/v1/chef/ingredients/products"

    @classmethod
    def recipe_search(cls, query: str, limit: int = 10, offset: int = 0) -> str:
        """Build recipe search endpoint URL."""
        from urllib.parse import quote
        encoded_query = quote(query)
        return f"/services/frontend-service/recipe/search/{encoded_query}?offset={offset}&limit={limit}"

    @classmethod
    def recipe_detail(cls, recipe_id: int) -> str:
        """Build recipe detail endpoint URL."""
        return f"/services/frontend-service/recipe/{recipe_id}"

    @classmethod
    def shopping_list(cls, shopping_list_id: str) -> str:
        """Build shopping list endpoint URL."""
        return cls.SHOPPING_LIST.format(shopping_list_id=shopping_list_id)

    @classmethod
    def delivered_orders(cls, limit: int = 50, offset: int = 0) -> str:
        """Build delivered orders endpoint URL with pagination."""
        return f"{cls.DELIVERED_ORDERS}?offset={offset}&limit={limit}"

    @classmethod
    def timeslots(cls, user_id: int, address_id: int) -> str:
        """Build timeslots endpoint URL with user and address IDs."""
        return f"{cls.TIMESLOTS_BASE}0?userId={user_id}&addressId={address_id}&reasonableDeliveryTime=true"
