"""Authentication manager for Rohlik.cz API."""

import logging
from typing import Optional, Dict, Any

import httpx

from .http_client import HttpClient
from .endpoints import Endpoints
from .errors import InvalidCredentialsError, RohlikAPIError, APIRequestFailedError
from .helpers import mask_data

_LOGGER = logging.getLogger(__name__)


class AuthManager:
    """Manages authentication state for Rohlik.cz API.

    This class handles login, logout, and session management.

    Args:
        http_client: The HTTP client instance to use for requests
        username: Email address used for Rohlik.cz login
        password: Password for Rohlik.cz account
    """

    def __init__(
        self,
        http_client: HttpClient,
        username: str,
        password: str,
    ):
        if not username or not password:
            raise ValueError("Username and password are required")

        self._http = http_client
        self._username = username
        self._password = password

        self._is_logged_in: bool = False
        self._user_id: Optional[int] = None
        self._address_id: Optional[int] = None

    @property
    def is_logged_in(self) -> bool:
        """Check if currently logged in."""
        return self._is_logged_in

    @property
    def user_id(self) -> Optional[int]:
        """Get the current user ID."""
        return self._user_id

    @property
    def address_id(self) -> Optional[int]:
        """Get the current address ID."""
        return self._address_id

    async def login(self) -> Dict[str, Any]:
        """Authenticate with the Rohlik.cz service.

        If already logged in, returns cached response without making a new request.

        Returns:
            dict: The JSON response containing authentication data

        Raises:
            InvalidCredentialsError: If credentials are invalid
            APIRequestFailedError: If the login request fails
        """
        if self._is_logged_in:
            _LOGGER.debug("Already logged in, skipping login request")
            return {"status": 200, "message": "Already logged in"}

        login_data = {
            "email": self._username,
            "password": self._password,
            "name": ""
        }

        try:
            response = await self._http.post(Endpoints.LOGIN, json=login_data)
            login_response = response.json()

            if login_response.get("status") != 200:
                if login_response.get("status") == 401:
                    messages = login_response.get("messages", [])
                    error_msg = messages[0].get("content", "Invalid credentials") if messages else "Invalid credentials"
                    raise InvalidCredentialsError(error_msg)
                else:
                    messages = login_response.get("messages", [])
                    error_msg = messages[0].get("content", "Unknown error") if messages else "Unknown error"
                    raise RohlikAPIError(f"Unknown error occurred during login: {error_msg}")

            self._is_logged_in = True

            # Extract user and address IDs
            data = login_response.get("data", {})
            if not self._user_id:
                self._user_id = data.get("user", {}).get("id")

            if not self._address_id:
                try:
                    self._address_id = data.get("address", {}).get("id")
                except AttributeError:
                    _LOGGER.error(f"Address cannot be retrieved from login data. Login response: {mask_data(login_response)}")

            return login_response

        except httpx.HTTPError as err:
            raise APIRequestFailedError(
                f"Cannot connect to website! Check your internet connection and try again: {err}"
            )

    async def logout(self) -> None:
        """Log out from the Rohlik.cz service.

        Raises:
            RohlikAPIError: If logout fails
            APIRequestFailedError: If the request fails
        """
        if not self._is_logged_in:
            _LOGGER.debug("Not logged in, skipping logout request")
            return

        try:
            response = await self._http.post(Endpoints.LOGOUT)
            logout_response = response.json()

            if logout_response.get("status") != 200:
                raise RohlikAPIError(f"Unknown error occurred during logout: {logout_response}")

            self._is_logged_in = False

        except httpx.HTTPError as err:
            self._is_logged_in = False  # Reset state even on error
            raise APIRequestFailedError(
                f"Cannot connect to website! Check your internet connection and try again: {err}"
            )

    async def ensure_logged_in(self) -> None:
        """Ensure the client is logged in, login if not."""
        if not self._is_logged_in:
            await self.login()
