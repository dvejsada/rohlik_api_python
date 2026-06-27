"""HTTP client for the Rohlik.cz API."""

from __future__ import annotations

import asyncio
import json
import logging
from collections.abc import Awaitable, Callable
from importlib.metadata import PackageNotFoundError, version
from typing import Any

import aiohttp

from .endpoints import BASE_URL, Endpoints

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
        on_unauthorized: Optional async callback invoked when a request returns
            HTTP 401 (an expired session). After it runs, the request is retried
            once. Login/logout requests are exempt to avoid recursion.
    """

    DEFAULT_USER_AGENT = f"rohlik-api-python/{_VERSION}"

    # Endpoints that must never trigger the re-auth retry (the callback logs in
    # via the login endpoint, so retrying it would recurse).
    _NO_REAUTH_ENDPOINTS = (Endpoints.LOGIN, Endpoints.LOGOUT)

    def __init__(
        self,
        base_url: str = BASE_URL,
        timeout: float = 30.0,
        headers: dict[str, str] | None = None,
        session: aiohttp.ClientSession | None = None,
        on_unauthorized: Callable[[], Awaitable[Any]] | None = None,
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

        self._on_unauthorized = on_unauthorized
        self._reauth_lock = asyncio.Lock()
        # Bumped each time a re-auth completes, so coroutines that queued on the
        # lock behind an in-flight re-auth can skip a redundant second login.
        self._reauth_generation = 0

    def set_unauthorized_handler(self, handler: Callable[[], Awaitable[Any]] | None) -> None:
        """Register the callback used to re-authenticate on an HTTP 401."""
        self._on_unauthorized = handler

    @property
    def session(self) -> aiohttp.ClientSession:
        """Get or lazily create the underlying aiohttp session.

        Only sessions this client owns are (re)created. An injected session that
        has been closed by its owner is returned as-is, so the next request
        surfaces aiohttp's "Session is closed" error instead of silently
        spawning a new session that bypasses the owner's connector/SSL config.
        """
        if self._owns_session and (self._session is None or self._session.closed):
            self._session = aiohttp.ClientSession()
        if self._session is None:  # pragma: no cover - unreachable by construction
            # Owned sessions are created above; injected ones are set in
            # __init__. A plain ``raise`` (rather than ``assert``) keeps the
            # invariant enforced even under ``python -O``.
            raise RuntimeError("HTTP session is unexpectedly missing")
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
        """Perform a request and return a fully buffered :class:`Response`.

        On an HTTP 401 the registered re-auth callback (if any) is invoked once
        and the request is retried, transparently recovering from an expired
        session on a long-lived client. If the callback raises (re-auth itself
        failed), the error propagates to the caller and the request is not
        retried; a subsequent request will attempt re-auth again.
        """
        url = self._build_url(endpoint)
        prepared_params = self._prepare_params(params)
        merged_headers = self._merge_headers(headers)

        async def _send() -> tuple[int, bytes, aiohttp.ClientResponse]:
            # ``async with`` guarantees the connection is released on every
            # path, including if ``read()`` raises mid-response. Buffering the
            # body here also lets ``Response.json`` work after release.
            async with self.session.request(
                method,
                url,
                params=prepared_params,
                data=data,
                json=json_data,
                headers=merged_headers,
                timeout=self._timeout,
            ) as response:
                body = await response.read()
                return response.status, body, response

        status, body, response = await _send()

        if (
            status == 401
            and self._on_unauthorized is not None
            and endpoint not in self._NO_REAUTH_ENDPOINTS
        ):
            # Serialize re-auth, and use a generation counter so that several
            # requests that all hit a 401 at once trigger only one login: the
            # first through the lock re-authenticates, the rest see the bumped
            # generation and just retry.
            seen_generation = self._reauth_generation
            async with self._reauth_lock:
                if self._reauth_generation == seen_generation:
                    await self._on_unauthorized()
                    self._reauth_generation += 1
            status, body, response = await _send()

        return Response(status, body, response)

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
