"""Rohlik.cz API Client implementation."""

from __future__ import annotations

import logging
from types import TracebackType
from typing import Any

import httpx

from .auth import AuthManager
from .endpoints import BASE_URL
from .errors import APIRequestFailedError
from .http_client import HttpClient
from .services import (
    AccountService,
    CartService,
    DeliveryService,
    OrderService,
    ProductService,
    RecipeService,
)

_LOGGER = logging.getLogger(__name__)


class RohlikAPI:
    """Async client for interacting with the Rohlik.cz API.

    The client uses httpx with HTTP/2 support and exposes a service-based API
    for all operations. When used as an async context manager with
    ``auto_login=True`` (the default), it logs in on entry and logs out on exit.

    Args:
        username: Email address used for Rohlik.cz login (required).
        password: Password for the Rohlik.cz account (required).
        base_url: Base URL for the Rohlik.cz API. Defaults to https://www.rohlik.cz
        timeout: Request timeout in seconds. Defaults to 30.0.
        headers: Optional custom headers to include in all requests.
        auto_login: If True (default), log in automatically when used as a
            context manager.

    Attributes:
        cart (CartService): Cart operations (get_content, add_items, delete_item).
        products (ProductService): Product search and details.
        orders (OrderService): Order operations (get_next, get_last, get_delivered).
        delivery (DeliveryService): Delivery info and timeslots.
        account (AccountService): Account data (premium, bags, shopping lists).
        recipes (RecipeService): Recipe search and ingredients (Rohlík Chef).

    Example:
        >>> async with RohlikAPI("user@example.com", "password") as client:
        ...     cart = await client.cart.get_content()
        ...     print(cart["total_price"])
    """

    def __init__(
        self,
        username: str,
        password: str,
        base_url: str = BASE_URL,
        timeout: float = 30.0,
        headers: dict[str, str] | None = None,
        auto_login: bool = True,
    ) -> None:
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
        self._recipes = RecipeService(self._http, self._auth)

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
    def recipes(self) -> RecipeService:
        """Access recipe operations (Rohlík Chef)."""
        return self._recipes

    @property
    def client(self) -> httpx.AsyncClient:
        """Get or create the underlying async HTTP client."""
        return self._http.client

    @property
    def is_logged_in(self) -> bool:
        """Check if the client is currently logged in."""
        return self._auth.is_logged_in

    @property
    def user_id(self) -> int | None:
        """The authenticated user's ID, or None if not logged in."""
        return self._auth.user_id

    @property
    def address_id(self) -> int | None:
        """The authenticated user's delivery address ID, or None if not logged in."""
        return self._auth.address_id

    # -------------------------------------------------------------------------
    # Authentication
    # -------------------------------------------------------------------------

    async def login(self) -> dict[str, Any]:
        """Authenticate with the Rohlik.cz service.

        Returns:
            The JSON response containing authentication data.

        Raises:
            InvalidCredentialsError: If the credentials are invalid.
            APIRequestFailedError: If the request fails.
        """
        return await self._auth.login()

    async def logout(self) -> None:
        """Log out from the Rohlik.cz service.

        Raises:
            RohlikAPIError: If logout fails.
            APIRequestFailedError: If the request fails.
        """
        await self._auth.logout()

    # -------------------------------------------------------------------------
    # Context Manager
    # -------------------------------------------------------------------------

    async def __aenter__(self) -> RohlikAPI:
        """Enter the context manager, logging in if ``auto_login`` is True."""
        if self._auto_login:
            await self._auth.login()
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: TracebackType | None,
    ) -> None:
        """Exit the context manager, logging out and releasing resources."""
        await self.close()

    async def close(self) -> None:
        """Close the HTTP client and release resources. Logs out if logged in."""
        if self._auth.is_logged_in:
            try:
                await self._auth.logout()
            except Exception as err:  # noqa: BLE001 - best-effort logout on close
                _LOGGER.error("Error during logout on close: %s", err)

        await self._http.close()

    # -------------------------------------------------------------------------
    # Aggregated data retrieval
    # -------------------------------------------------------------------------

    async def get_data(self) -> dict[str, Any]:
        """Retrieve account data from Rohlik.cz in a single aggregated call.

        Returns:
            A dictionary containing delivery info, orders, cart contents,
            premium profile, announcements and more.

        Raises:
            APIRequestFailedError: If the underlying requests fail.
        """
        result: dict[str, Any] = {}

        result["login"] = await self._auth.login()

        try:
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
            raise APIRequestFailedError(
                f"Cannot connect to website! Check your internet connection "
                f"and try again: {err}"
            ) from err
