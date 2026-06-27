"""HTTP client for the Rohlik.cz API."""

from __future__ import annotations

import json
import logging
from importlib.metadata import PackageNotFoundError, version
from typing import Any

import aiohttp

from .endpoints import BASE_URL

_LOGGER = logging.getLogger(__name__)

try:
    _VERSION = version("rohlik-api")
except PackageNotFoundError:  # pragma: no cover - package not installed
    _VERSION = "0.0.0"

# Transport-level errors that callers treat as a failed request. aiohttp raises
# ``asyncio.TimeoutError`` (an alias of the builtin ``TimeoutError``) on
# timeouts, which is not a subclass of ``ClientError``, so it must be listed
# explicitly alongside it.
HTTP_ERRORS: tuple[type[Exception], ...] = (aiohttp.ClientError, TimeoutError)


class Response:
    """Lightweight wrapper around an aiohttp response.

    The body is buffered when the response is created, so :meth:`json` and
    :meth:`raise_for_status` are synchronous and can be called after the
    underlying connection has been released back to the pool. This keeps the
    service layer decoupled from aiohttp's streaming semantics.
    """

    __slots__ = ("status", "_body", "_response")

    def __init__(self, status: int, body: bytes, response: aiohttp.ClientResponse) -> None:
        self.status = status
        self._body = body
        self._response = response

    def json(self) -> Any:
        """Decode the response body as JSON, ignoring the content type."""
        return json.loads(self._body)

    def raise_for_status(self) -> None:
        """Raise :class:`aiohttp.ClientResponseError` for a 4xx/5xx status."""
        self._response.raise_for_status()


class HttpClient:
    """Async HTTP client for the Rohlik.cz API, built on aiohttp.

    By default the client creates and owns its own :class:`aiohttp.ClientSession`.
    A session may instead be injected (for example Home Assistant's shared
    session obtained via ``homeassistant.helpers.aiohttp_client``); an injected
    session is never closed by this client, leaving its lifecycle to the owner.

    Args:
        base_url: Base URL for the Rohlik.cz API.
        timeout: Request timeout in seconds.
        headers: Optional custom headers added to every request.
        session: Optional externally managed aiohttp session to reuse.
    """

    DEFAULT_USER_AGENT = f"rohlik-api-python/{_VERSION}"

    def __init__(
        self,
        base_url: str = BASE_URL,
        timeout: float = 30.0,
        headers: dict[str, str] | None = None,
        session: aiohttp.ClientSession | None = None,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self._timeout = aiohttp.ClientTimeout(total=timeout)

        self._headers = {
            "User-Agent": self.DEFAULT_USER_AGENT,
            "Accept": "application/json",
        }
        if headers:
            self._headers.update(headers)

        self._session = session
        self._owns_session = session is None

    @property
    def session(self) -> aiohttp.ClientSession:
        """Get or lazily create the underlying aiohttp session."""
        if self._session is None or self._session.closed:
            self._session = aiohttp.ClientSession()
            self._owns_session = True
        return self._session

    @property
    def is_closed(self) -> bool:
        """Check whether the underlying session is closed or absent."""
        return self._session is None or self._session.closed

    async def close(self) -> None:
        """Close the session and release resources.

        Only sessions created (owned) by this client are closed; an injected
        session is left untouched for its owner to manage.
        """
        if self._owns_session:
            if self._session is not None and not self._session.closed:
                await self._session.close()
            self._session = None

    def _build_url(self, endpoint: str) -> str:
        """Resolve an endpoint path against the base URL."""
        if endpoint.startswith(("http://", "https://")):
            return endpoint
        return f"{self.base_url}{endpoint}"

    def _merge_headers(self, headers: dict[str, str] | None) -> dict[str, str]:
        """Combine the default headers with any per-request overrides."""
        if not headers:
            return self._headers
        merged = dict(self._headers)
        merged.update(headers)
        return merged

    @staticmethod
    def _prepare_params(params: dict[str, Any] | None) -> dict[str, str] | None:
        """Coerce query parameters into the string values aiohttp accepts.

        aiohttp rejects ``bool``, ``None`` and nested structures in query
        params, so booleans become ``"true"``/``"false"``, ``None`` values are
        dropped and dicts/lists are JSON-encoded.
        """
        if not params:
            return None
        prepared: dict[str, str] = {}
        for key, value in params.items():
            if value is None:
                continue
            if isinstance(value, bool):
                prepared[key] = "true" if value else "false"
            elif isinstance(value, (dict, list)):
                prepared[key] = json.dumps(value, separators=(",", ":"))
            else:
                prepared[key] = str(value)
        return prepared

    async def _request(
        self,
        method: str,
        endpoint: str,
        *,
        params: dict[str, Any] | None = None,
        data: dict[str, Any] | None = None,
        json_data: dict[str, Any] | None = None,
        headers: dict[str, str] | None = None,
    ) -> Response:
        """Perform a request and return a fully buffered :class:`Response`."""
        response = await self.session.request(
            method,
            self._build_url(endpoint),
            params=self._prepare_params(params),
            data=data,
            json=json_data,
            headers=self._merge_headers(headers),
            timeout=self._timeout,
        )
        # Buffer the body so the connection is released regardless of how the
        # caller consumes the response, and so ``Response.json`` works later.
        body = await response.read()
        return Response(response.status, body, response)

    async def get(
        self,
        endpoint: str,
        params: dict[str, Any] | None = None,
        headers: dict[str, str] | None = None,
    ) -> Response:
        """Make a GET request."""
        return await self._request("GET", endpoint, params=params, headers=headers)

    async def post(
        self,
        endpoint: str,
        data: dict[str, Any] | None = None,
        json: dict[str, Any] | None = None,
        headers: dict[str, str] | None = None,
    ) -> Response:
        """Make a POST request."""
        return await self._request("POST", endpoint, data=data, json_data=json, headers=headers)

    async def delete(
        self,
        endpoint: str,
        params: dict[str, Any] | None = None,
        headers: dict[str, str] | None = None,
    ) -> Response:
        """Make a DELETE request."""
        return await self._request("DELETE", endpoint, params=params, headers=headers)

    async def __aenter__(self) -> HttpClient:
        """Async context manager entry."""
        return self

    async def __aexit__(self, exc_type: object, exc_val: object, exc_tb: object) -> None:
        """Async context manager exit."""
        await self.close()
