"""API endpoint definitions for Rohlik.cz."""

from __future__ import annotations

from urllib.parse import quote

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

    # Delivery
    DELIVERY = "/services/frontend-service/first-delivery?reasonableDeliveryTime=true"
    TIMESLOT_RESERVATION = "/services/frontend-service/v1/timeslot-reservation"
    DELIVERY_ANNOUNCEMENTS = "/services/frontend-service/announcements/delivery"
    DELIVERY_ADDRESS_LIST = "/services/frontend-service/delivery-address/list"

    # Orders
    NEXT_ORDER = "/api/v3/orders/upcoming"
    LAST_ORDER = "/api/v3/orders/delivered?offset=0&limit=1"

    # Account
    PREMIUM_PROFILE = "/services/frontend-service/premium/profile"
    BAGS = "/api/v1/reusable-bags/user-info"
    ANNOUNCEMENTS = "/services/frontend-service/announcements/top"

    # Recipes
    INGREDIENT_PRODUCTS = "/services/frontend-service/v1/chef/ingredients/products"

    # -------------------------------------------------------------------------
    # Builder methods for dynamic endpoints
    # -------------------------------------------------------------------------

    @classmethod
    def recipe_search(cls, query: str, limit: int = 10, offset: int = 0) -> str:
        """Build recipe search endpoint URL."""
        encoded_query = quote(query)
        return (
            f"/services/frontend-service/recipe/search/{encoded_query}"
            f"?offset={offset}&limit={limit}"
        )

    @classmethod
    def recipe_detail(cls, recipe_id: int) -> str:
        """Build recipe detail endpoint URL."""
        return f"/services/frontend-service/recipe/{recipe_id}"

    @classmethod
    def order_detail(cls, order_id: int) -> str:
        """Build order detail endpoint URL (full order including items)."""
        return f"/api/v3/orders/{order_id}"

    @classmethod
    def product_detail(cls, product_id: int) -> str:
        """Build product detail endpoint URL."""
        return f"/api/v1/products/{product_id}"

    @classmethod
    def product_categories(cls, product_id: int) -> str:
        """Build product category-hierarchy endpoint URL."""
        return f"/api/v1/products/{product_id}/categories"

    @classmethod
    def product_ai_summary(cls, product_id: int) -> str:
        """Build product AI summary endpoint URL."""
        return f"/api/v1/products/{product_id}/ai-summary"

    @classmethod
    def product_composition(cls, product_id: int) -> str:
        """Build product composition endpoint URL."""
        return f"/api/v1/products/{product_id}/composition"

    @classmethod
    def product_price(cls, product_id: int) -> str:
        """Build product price endpoint URL."""
        return f"/api/v1/products/{product_id}/prices"

    @classmethod
    def product_cards(cls, product_ids: list[int], category_type: str = "normal") -> str:
        """Build the bulk product-card endpoint URL for several products."""
        params = "&".join(f"products={int(pid)}" for pid in product_ids)
        return f"/api/v1/products/card?{params}&categoryType={category_type}"

    @classmethod
    def week_sales(cls, page: int = 0, size: int = 30, sort: str = "recommended") -> str:
        """Build the 'deals of the week' (Akce týdne) component URL."""
        return (
            f"/api/v1/categories/sales/components/week-sales"
            f"?page={page}&size={size}&sort={sort}"
        )

    @classmethod
    def shopping_list(cls, shopping_list_id: str) -> str:
        """Build shopping list endpoint URL."""
        return f"/api/v1/shopping-lists/id/{shopping_list_id}"

    @classmethod
    def delivered_orders(cls, limit: int = 50, offset: int = 0) -> str:
        """Build delivered orders endpoint URL with pagination."""
        return f"/api/v3/orders/delivered?offset={offset}&limit={limit}"

    @classmethod
    def timeslots(cls, user_id: int, address_id: int) -> str:
        """Build timeslots endpoint URL with user and address IDs."""
        return (
            f"/services/frontend-service/timeslots-api/0"
            f"?userId={user_id}&addressId={address_id}&reasonableDeliveryTime=true"
        )
