"""Rohlik.cz API Client implementation."""

import logging
from typing import Optional, Dict, Any

import httpx

from .http_client import HttpClient
from .auth import AuthManager
from .endpoints import BASE_URL
from .errors import APIRequestFailedError
from .services import (
    CartService,
    ProductService,
    OrderService,
    DeliveryService,
    AccountService,
)

_LOGGER = logging.getLogger(__name__)


class RohlikAPI:
    """Async client for interacting with Rohlik.cz API.

    This client uses httpx with HTTP/2 support for optimal performance
    when communicating with the Rohlik.cz API endpoints. The client provides
    a clean service-based API for all operations.

    When used as an async context manager with auto_login=True (default),
    the client automatically logs in on entry and logs out on exit.

    Args:
        username: Email address used for Rohlik.cz login (required)
        password: Password for Rohlik.cz account (required)
        base_url: Base URL for the Rohlik.cz API. Defaults to https://www.rohlik.cz
        timeout: Request timeout in seconds. Defaults to 30.0
        headers: Optional custom headers to include in all requests
        auto_login: If True (default), automatically login when using context manager

    Attributes:
        cart (CartService): Service for cart operations (get_content, add_items, delete_item)
        products (ProductService): Service for product search
        orders (OrderService): Service for order operations (get_next, get_last, get_delivered)
        delivery (DeliveryService): Service for delivery info and timeslots
        account (AccountService): Service for account data (premium, bags, shopping lists)

    Example:
        Basic usage with context manager:

        >>> async with RohlikAPI("user@example.com", "password") as client:
        ...     cart = await client.cart.get_content()
        ...     print(f"Cart total: {cart['total_price']}")

        Full example with all services:

        >>> async with RohlikAPI("user@example.com", "password") as client:
        ...     # Cart operations
        ...     cart = await client.cart.get_content()
        ...     await client.cart.add_items([{"product_id": 123, "quantity": 2}])
        ...
        ...     # Search products
        ...     results = await client.products.search("milk")
        ...
        ...     # Order history
        ...     orders = await client.orders.get_delivered(limit=10)
        ...
        ...     # Delivery info
        ...     slots = await client.delivery.get_next_slots()
        ...
        ...     # Account info
        ...     premium = await client.account.get_premium_profile()
    """

    def __init__(
        self,
        username: str,
        password: str,
        base_url: str = BASE_URL,
        timeout: float = 30.0,
        headers: Optional[Dict[str, str]] = None,
        auto_login: bool = True,
    ):
        """Initialize the Rohlik API client.

        Args:
            username: Email address used for Rohlik.cz login (required)
            password: Password for Rohlik.cz account (required)
            base_url: Base URL for the Rohlik.cz API
            timeout: Request timeout in seconds
            headers: Optional custom headers to include in all requests
            auto_login: If True, automatically login when using context manager
        """
        if not username or not password:
            raise ValueError("Username and password are required")

        self._auto_login = auto_login
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        
        # Initialize HTTP client
        self._http = HttpClient(
            base_url=base_url,
            timeout=timeout,
            headers=headers,
        )

        # Initialize auth manager
        self._auth = AuthManager(
            http_client=self._http,
            username=username,
            password=password,
        )

        # Initialize services
        self._cart = CartService(self._http, self._auth)
        self._products = ProductService(self._http, self._auth)
        self._orders = OrderService(self._http, self._auth)
        self._delivery = DeliveryService(self._http, self._auth)
        self._account = AccountService(self._http, self._auth)

    # -------------------------------------------------------------------------
    # Service Properties
    # -------------------------------------------------------------------------

    @property
    def cart(self) -> CartService:
        """Access cart operations."""
        return self._cart

    @property
    def products(self) -> ProductService:
        """Access product operations."""
        return self._products

    @property
    def orders(self) -> OrderService:
        """Access order operations."""
        return self._orders

    @property
    def delivery(self) -> DeliveryService:
        """Access delivery operations."""
        return self._delivery

    @property
    def account(self) -> AccountService:
        """Access account operations."""
        return self._account

    @property
    def client(self) -> httpx.AsyncClient:
        """Get or create the async HTTP client."""
        return self._http.client

    @property
    def is_logged_in(self) -> bool:
        """Check if the client is currently logged in."""
        return self._auth.is_logged_in


    # -------------------------------------------------------------------------
    # Context Manager
    # -------------------------------------------------------------------------

    async def __aenter__(self):
        """Async context manager entry - logs in automatically if auto_login is True."""
        if self._auto_login:
            await self._auth.login()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit - logout and close."""
        await self.close()

    async def close(self):
        """Close the HTTP client and release resources. Logs out if logged in."""
        if self._auth.is_logged_in:
            try:
                await self._auth.logout()
            except Exception as err:
                _LOGGER.error(f"Error during logout on close: {err}")

        await self._http.close()


    # -------------------------------------------------------------------------
    # Data Retrieval Methods
    # -------------------------------------------------------------------------

    async def get_data(self) -> Dict[str, Any]:
        """Retrieve all account data from Rohlik.cz in a single operation.

        Returns:
            dict: Dictionary containing all account data including delivery info,
                  orders, premium profile, cart contents, etc.
        """
        result: Dict[str, Any] = {}

        result["login"] = await self._auth.login()

        try:
            # Fetch all data using services
            result["delivery"] = await self._delivery.get_info()
            result["next_order"] = await self._orders.get_next()
            result["last_order"] = await self._orders.get_last()
            result["delivered_orders"] = await self._orders.get_delivered()
            result["announcements"] = await self._account.get_announcements()
            result["bags"] = await self._account.get_bags_info()
            result["timeslot"] = await self._delivery.get_timeslot_reservation()
            result["premium_profile"] = await self._account.get_premium_profile()
            result["delivery_announcements"] = await self._delivery.get_announcements()
            result["next_delivery_slot"] = await self._delivery.get_next_slots()
            result["cart"] = await self._cart.get_content()

            return result

        except httpx.HTTPError as err:
            raise APIRequestFailedError(f"Cannot connect to website! Check your internet connection and try again: {err}")

