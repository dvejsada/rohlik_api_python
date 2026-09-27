"""Rohlik.cz API Client implementation."""

from __future__ import annotations

import logging
from types import TracebackType
from typing import Any

import aiohttp

from .auth import AuthManager
from .endpoints import BASE_URL
from .errors import APIRequestFailedError
from .http_client import HTTP_ERRORS, HttpClient
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
    """Async client for interacting with the Rohlík Group API.

    Talks to Rohlík.cz by default; pass another shop's ``base_url`` (see
    :data:`~rohlik_api.SITES`) for Knuspr.de, Gurkerl.at, Kifli.hu or Sezamo.ro.

    The client is built on aiohttp and exposes a service-based API for all
    operations. When used as an async context manager with ``auto_login=True``
    (the default), it logs in on entry and logs out on exit.

    Args:
        username: Email address used for the shop login (required).
        password: Password for the shop account (required).
        base_url: Base URL of the shop's API, e.g. ``SITES["de"].base_url``.
            Defaults to https://www.rohlik.cz
        timeout: Request timeout in seconds. Defaults to 30.0.
        headers: Optional custom headers to include in all requests.
        auto_login: If True (default), log in automatically when used as a
            context manager.
        session: Optional externally managed :class:`aiohttp.ClientSession` to
            reuse (for example Home Assistant's shared session). When provided,
            the session is not closed by this client.

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
        ...     print(cart.total_price, cart.total_items)
        ...     for item in cart.products:
        ...         print(item.name, item.quantity, item.price)
    """

    def __init__(
        self,
        username: str,
        password: str,
        base_url: str = BASE_URL,
        timeout: float = 30.0,
        headers: dict[str, str] | None = None,
        auto_login: bool = True,
        session: aiohttp.ClientSession | None = None,
    ) -> None:
        # Credential validation is owned by AuthManager (constructed below),
        # which raises ValueError on empty username/password.
        self._auto_login = auto_login
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout

        # Initialize HTTP client
        self._http = HttpClient(
            base_url=base_url,
            timeout=timeout,
            headers=headers,
            session=session,
        )

        # Initialize auth manager
        self._auth = AuthManager(
            http_client=self._http,
            username=username,
            password=password,
        )

        # Wire up transparent re-authentication: when any request hits HTTP 401
        # (expired session), the HTTP client re-logs in and retries once.
        self._http.set_unauthorized_handler(self._auth.relogin)

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
    def session(self) -> aiohttp.ClientSession:
        """Get or create the underlying aiohttp session."""
        return self._http.session

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
                _LOGGER.warning("Error during logout on close: %s", err)

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

        except HTTP_ERRORS as err:
            raise APIRequestFailedError(
                f"Cannot connect to website! Check your internet connection "
                f"and try again: {err}"
            ) from err
