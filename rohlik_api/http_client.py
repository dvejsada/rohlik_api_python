"""HTTP client for Rohlik.cz API."""

import logging
from typing import Optional, Dict, Any

import httpx

from .endpoints import BASE_URL

_LOGGER = logging.getLogger(__name__)


class HttpClient:
    """Async HTTP client with HTTP/2 support for Rohlik.cz API."""

    DEFAULT_USER_AGENT = "rohlik-api-python/0.1.0"

    def __init__(
        self,
        base_url: str = BASE_URL,
        timeout: float = 30.0,
        headers: Optional[Dict[str, str]] = None,
    ):
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout

        self._headers = {
            "User-Agent": self.DEFAULT_USER_AGENT,
            "Accept": "application/json",
        }
        if headers:
            self._headers.update(headers)

        self._client: Optional[httpx.AsyncClient] = None

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
        params: Optional[Dict[str, Any]] = None,
        headers: Optional[Dict[str, str]] = None,
    ) -> httpx.Response:
        """Make a GET request."""
        return await self.client.get(endpoint, params=params, headers=headers)

    async def post(
        self,
        endpoint: str,
        data: Optional[Dict[str, Any]] = None,
        json: Optional[Dict[str, Any]] = None,
        headers: Optional[Dict[str, str]] = None,
    ) -> httpx.Response:
        """Make a POST request."""
        return await self.client.post(endpoint, data=data, json=json, headers=headers)

    async def delete(
        self,
        endpoint: str,
        params: Optional[Dict[str, Any]] = None,
        headers: Optional[Dict[str, str]] = None,
    ) -> httpx.Response:
        """Make a DELETE request."""
        return await self.client.delete(endpoint, params=params, headers=headers)

    async def __aenter__(self):
        """Async context manager entry."""
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self.close()
