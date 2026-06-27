"""Tests for the HttpClient class."""

import asyncio
from unittest.mock import AsyncMock

import aiohttp

from rohlik_api import BASE_URL, Endpoints
from rohlik_api.http_client import HttpClient


class _FakeResponse:
    """Minimal stand-in for an aiohttp ClientResponse (also its own CM)."""

    def __init__(self, status: int, body: bytes = b"{}") -> None:
        self.status = status
        self._body = body

    async def __aenter__(self) -> "_FakeResponse":
        # Yield control so concurrent requests can interleave deterministically.
        await asyncio.sleep(0)
        return self

    async def __aexit__(self, *exc: object) -> bool:
        return False

    async def read(self) -> bytes:
        return self._body

    def raise_for_status(self) -> None:
        if self.status >= 400:
            raise aiohttp.ClientResponseError(None, (), status=self.status)


class _FakeSession:
    """Fake aiohttp session that yields a scripted sequence of responses.

    ``request`` returns the response object directly (not a coroutine), so it
    works with ``async with session.request(...)`` like the real client.
    """

    def __init__(self, responses: list[_FakeResponse]) -> None:
        self._responses = list(responses)
        self.closed = False
        self.calls: list[tuple[str, str]] = []

    def request(self, method: str, url: str, **kwargs: object) -> _FakeResponse:
        self.calls.append((method, url))
        return self._responses.pop(0)


class _CountingSession:
    """Fake session whose first ``fail_first`` requests return 401, rest 200."""

    def __init__(self, fail_first: int) -> None:
        self.fail_first = fail_first
        self.count = 0
        self.closed = False

    def request(self, method: str, url: str, **kwargs: object) -> _FakeResponse:
        self.count += 1
        status = 401 if self.count <= self.fail_first else 200
        return _FakeResponse(status)


class TestHttpClientInitialization:
    """Tests for HttpClient initialization."""

    def test_default_initialization(self):
        """Test HttpClient initializes with default values."""
        client = HttpClient()
        assert client.base_url == BASE_URL
        assert client.timeout == 30.0
        assert client._session is None

    def test_custom_base_url(self):
        """Test HttpClient with custom base URL."""
        custom_url = "https://custom.example.com"
        client = HttpClient(base_url=custom_url)
        assert client.base_url == custom_url

    def test_trailing_slash_removed(self):
        """Test that trailing slash is removed from base URL."""
        client = HttpClient(base_url="https://example.com/")
        assert client.base_url == "https://example.com"

    def test_custom_timeout(self):
        """Test HttpClient with custom timeout."""
        client = HttpClient(timeout=60.0)
        assert client.timeout == 60.0

    def test_default_headers(self):
        """Test that default headers are set."""
        client = HttpClient()
        assert "User-Agent" in client._headers
        assert "Accept" in client._headers
        assert client._headers["Accept"] == "application/json"

    def test_custom_headers_merged(self):
        """Test that custom headers are merged with defaults."""
        custom_headers = {"X-Custom": "Value", "Accept": "text/html"}
        client = HttpClient(headers=custom_headers)
        assert client._headers["X-Custom"] == "Value"
        assert client._headers["Accept"] == "text/html"  # Custom overrides default
        assert "User-Agent" in client._headers  # Default preserved


class TestHttpClientLazyInitialization:
    """Tests for HttpClient lazy initialization."""

    def test_session_is_none_initially(self):
        """Test that internal session is None before first use."""
        http = HttpClient()
        assert http._session is None

    async def test_session_created_on_access(self):
        """Test that accessing the session property creates the session."""
        http = HttpClient()
        assert http.session is not None
        assert http._session is not None
        await http.close()

    def test_is_closed_initially_true(self):
        """Test that is_closed returns True when session not created."""
        http = HttpClient()
        assert http.is_closed is True

    async def test_is_closed_false_after_access(self):
        """Test that is_closed returns False after session created."""
        http = HttpClient()
        _ = http.session
        assert http.is_closed is False
        await http.close()


class TestHttpClientClose:
    """Tests for HttpClient close functionality."""

    async def test_close_without_session(self):
        """Test closing when session was never created."""
        http = HttpClient()
        await http.close()  # Should not raise
        assert http._session is None

    async def test_close_with_session(self):
        """Test closing after the session was created."""
        http = HttpClient()
        _ = http.session  # Create session
        await http.close()
        assert http._session is None

    async def test_close_multiple_times(self):
        """Test that closing multiple times is safe."""
        http = HttpClient()
        _ = http.session
        await http.close()
        await http.close()  # Should not raise
        assert http._session is None


class TestHttpClientInjectedSession:
    """Tests for reusing an externally managed aiohttp session."""

    async def test_injected_session_is_used(self):
        """An injected session is returned instead of creating a new one."""
        session = aiohttp.ClientSession()
        try:
            http = HttpClient(session=session)
            assert http.session is session
            assert http.is_closed is False
        finally:
            await session.close()

    async def test_close_does_not_close_injected_session(self):
        """Closing the client must not close an externally owned session."""
        session = aiohttp.ClientSession()
        try:
            http = HttpClient(session=session)
            await http.close()
            assert session.closed is False
        finally:
            await session.close()

    async def test_closed_injected_session_is_not_replaced(self):
        """A closed injected session is returned as-is, never silently replaced."""
        session = aiohttp.ClientSession()
        await session.close()
        http = HttpClient(session=session)

        # The client must not spawn a new owned session in place of the
        # caller's (now closed) one.
        assert http.session is session
        assert http.is_closed is True


class TestHttpClientReauth:
    """Tests for transparent re-authentication on HTTP 401."""

    async def test_retries_once_after_reauth_on_401(self):
        """A 401 triggers the handler and the request is retried once."""
        session = _FakeSession([_FakeResponse(401), _FakeResponse(200, b'{"ok": true}')])
        handler = AsyncMock()
        http = HttpClient(session=session)
        http.set_unauthorized_handler(handler)

        response = await http.get("/api/v3/orders/upcoming")

        handler.assert_awaited_once()
        assert response.status == 200
        assert response.json() == {"ok": True}
        assert len(session.calls) == 2

    async def test_no_retry_without_handler(self):
        """Without a handler, a 401 is returned untouched."""
        session = _FakeSession([_FakeResponse(401)])
        http = HttpClient(session=session)

        response = await http.get("/api/v3/orders/upcoming")

        assert response.status == 401
        assert len(session.calls) == 1

    async def test_login_endpoint_is_exempt_from_reauth(self):
        """A 401 on the login endpoint must not invoke the handler (no recursion)."""
        session = _FakeSession([_FakeResponse(401)])
        handler = AsyncMock()
        http = HttpClient(session=session)
        http.set_unauthorized_handler(handler)

        response = await http.post(Endpoints.LOGIN, json={"email": "a", "password": "b"})

        handler.assert_not_awaited()
        assert response.status == 401
        assert len(session.calls) == 1

    async def test_non_401_does_not_trigger_reauth(self):
        """A successful request never invokes the re-auth handler."""
        session = _FakeSession([_FakeResponse(200)])
        handler = AsyncMock()
        http = HttpClient(session=session)
        http.set_unauthorized_handler(handler)

        await http.get("/api/v3/orders/upcoming")

        handler.assert_not_awaited()
        assert len(session.calls) == 1

    async def test_concurrent_401s_trigger_single_reauth(self):
        """Several requests hitting 401 at once re-authenticate only once."""
        # Both initial requests 401; both retries succeed -> 4 requests total.
        session = _CountingSession(fail_first=2)
        calls = 0

        async def handler() -> None:
            nonlocal calls
            calls += 1
            await asyncio.sleep(0)  # hold the lock long enough to overlap

        http = HttpClient(session=session)
        http.set_unauthorized_handler(handler)

        responses = await asyncio.gather(
            http.get("/api/v3/orders/upcoming"),
            http.get("/api/v3/orders/delivered"),
        )

        assert calls == 1
        assert all(r.status == 200 for r in responses)
        assert session.count == 4


class TestHttpClientContextManager:
    """Tests for HttpClient async context manager."""

    async def test_context_manager_entry(self):
        """Test async context manager entry."""
        async with HttpClient() as http:
            assert http is not None
            assert isinstance(http, HttpClient)

    async def test_context_manager_closes_on_exit(self):
        """Test that context manager closes the session on exit."""
        http = HttpClient()
        async with http:
            _ = http.session  # Ensure session is created
        assert http._session is None
