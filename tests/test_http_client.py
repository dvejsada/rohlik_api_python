"""Tests for the HttpClient class."""

import aiohttp

from rohlik_api import BASE_URL
from rohlik_api.http_client import HttpClient


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
