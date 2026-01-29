"""Tests for the HttpClient class."""

import pytest
from rohlik_api.http_client import HttpClient
from rohlik_api import BASE_URL


class TestHttpClientInitialization:
    """Tests for HttpClient initialization."""

    def test_default_initialization(self):
        """Test HttpClient initializes with default values."""
        client = HttpClient()
        assert client.base_url == BASE_URL
        assert client.timeout == 30.0
        assert client._client is None

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

    def test_client_is_none_initially(self):
        """Test that internal client is None before first use."""
        http = HttpClient()
        assert http._client is None

    def test_client_created_on_access(self):
        """Test that accessing client property creates the client."""
        http = HttpClient()
        _ = http.client
        assert http._client is not None

    def test_is_closed_initially_true(self):
        """Test that is_closed returns True when client not created."""
        http = HttpClient()
        assert http.is_closed is True

    def test_is_closed_false_after_access(self):
        """Test that is_closed returns False after client created."""
        http = HttpClient()
        _ = http.client
        assert http.is_closed is False


class TestHttpClientClose:
    """Tests for HttpClient close functionality."""

    @pytest.mark.asyncio
    async def test_close_without_client(self):
        """Test closing when client was never created."""
        http = HttpClient()
        await http.close()  # Should not raise
        assert http._client is None

    @pytest.mark.asyncio
    async def test_close_with_client(self):
        """Test closing after client was created."""
        http = HttpClient()
        _ = http.client  # Create client
        await http.close()
        assert http._client is None

    @pytest.mark.asyncio
    async def test_close_multiple_times(self):
        """Test that closing multiple times is safe."""
        http = HttpClient()
        _ = http.client
        await http.close()
        await http.close()  # Should not raise
        assert http._client is None


class TestHttpClientContextManager:
    """Tests for HttpClient async context manager."""

    @pytest.mark.asyncio
    async def test_context_manager_entry(self):
        """Test async context manager entry."""
        async with HttpClient() as http:
            assert http is not None
            assert isinstance(http, HttpClient)

    @pytest.mark.asyncio
    async def test_context_manager_closes_on_exit(self):
        """Test that context manager closes client on exit."""
        http = HttpClient()
        async with http:
            _ = http.client  # Ensure client is created
        assert http._client is None
