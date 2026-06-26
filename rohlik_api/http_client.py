"""HTTP client for Rohlik.cz API."""

from __future__ import annotations

import logging
from importlib.metadata import PackageNotFoundError, version
from typing import Any

import httpx

from .endpoints import BASE_URL

_LOGGER = logging.getLogger(__name__)

try:
    _VERSION = version("rohlik-api")
except PackageNotFoundError:  # pragma: no cover - package not installed
    _VERSION = "0.0.0"


class HttpClient:
    """Async HTTP client with HTTP/2 support for Rohlik.cz API."""

    DEFAULT_USER_AGENT = f"rohlik-api-python/{_VERSION}"

    def __init__(
        self,
        base_url: str = BASE_URL,
        timeout: float = 30.0,
        headers: dict[str, str] | None = None,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout

        self._headers = {
            "User-Agent": self.DEFAULT_USER_AGENT,
            "Accept": "application/json",
        }
        if headers:
            self._headers.update(headers)

        self._client: httpx.AsyncClient | None = None

    @property
    def client(self) -> httpx.AsyncClient:
        """Get or create the async HTTP client."""
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(
                base_url=self.base_url,
                timeout=self.timeout,
                headers=self._headers,
                http2=True,
                follow_redirects=True,
            )
        return self._client

    @property
    def is_closed(self) -> bool:
        """Check if the client is closed."""
        return self._client is None or self._client.is_closed

    async def close(self) -> None:
        """Close the HTTP client and release resources."""
        if self._client is not None and not self._client.is_closed:
            await self._client.aclose()
            self._client = None

    async def get(
        self,
        endpoint: str,
        params: dict[str, Any] | None = None,
        headers: dict[str, str] | None = None,
    ) -> httpx.Response:
        """Make a GET request."""
        return await self.client.get(endpoint, params=params, headers=headers)

    async def post(
        self,
        endpoint: str,
        data: dict[str, Any] | None = None,
        json: dict[str, Any] | None = None,
        headers: dict[str, str] | None = None,
    ) -> httpx.Response:
        """Make a POST request."""
        return await self.client.post(endpoint, data=data, json=json, headers=headers)

    async def delete(
        self,
        endpoint: str,
        params: dict[str, Any] | None = None,
        headers: dict[str, str] | None = None,
    ) -> httpx.Response:
        """Make a DELETE request."""
        return await self.client.delete(endpoint, params=params, headers=headers)

    async def __aenter__(self) -> HttpClient:
        """Async context manager entry."""
        return self

    async def __aexit__(self, exc_type: object, exc_val: object, exc_tb: object) -> None:
        """Async context manager exit."""
        await self.close()
