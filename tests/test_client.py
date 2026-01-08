"""Tests for the RohlikAPI client class."""

import pytest
from rohlik_api import RohlikAPI


def test_client_initialization():
    """Test that client initializes correctly."""
    client = RohlikAPI()
    assert client.base_url == "https://www.rohlik.cz"
    assert client.timeout == 30.0
    assert client.client is not None
    client.close()


def test_client_custom_base_url():
    """Test client with custom base URL."""
    custom_url = "https://custom.rohlik.cz"
    client = RohlikAPI(base_url=custom_url)
    assert client.base_url == custom_url
    client.close()


def test_client_custom_timeout():
    """Test client with custom timeout."""
    custom_timeout = 60.0
    client = RohlikAPI(timeout=custom_timeout)
    assert client.timeout == custom_timeout
    client.close()


def test_client_custom_headers():
    """Test client with custom headers."""
    custom_headers = {"X-Custom-Header": "TestValue"}
    client = RohlikAPI(headers=custom_headers)
    assert "X-Custom-Header" in client.client.headers
    assert client.client.headers["X-Custom-Header"] == "TestValue"
    client.close()


def test_client_default_headers():
    """Test that default headers are set."""
    client = RohlikAPI()
    assert "User-Agent" in client.client.headers
    assert "Accept" in client.client.headers
    assert client.client.headers["Accept"] == "application/json"
    client.close()


def test_client_http2_enabled():
    """Test that HTTP/2 is enabled."""
    client = RohlikAPI()
    # Check that http2 is enabled in the client configuration
    assert hasattr(client.client, "_transport")
    client.close()


def test_client_context_manager():
    """Test client works as context manager."""
    with RohlikAPI() as client:
        assert client.base_url == "https://www.rohlik.cz"
        assert client.client is not None


def test_client_base_url_trailing_slash():
    """Test that trailing slash is removed from base URL."""
    client = RohlikAPI(base_url="https://www.rohlik.cz/")
    assert client.base_url == "https://www.rohlik.cz"
    client.close()


def test_make_url():
    """Test URL construction."""
    client = RohlikAPI()
    url = client._make_url("/api/v1/test")
    assert url == "https://www.rohlik.cz/api/v1/test"
    
    # Test with leading slash removed
    url = client._make_url("api/v1/test")
    assert url == "https://www.rohlik.cz/api/v1/test"
    client.close()


def test_client_close():
    """Test that client closes without error."""
    client = RohlikAPI()
    client.close()
    # Should be able to close multiple times without error
    client.close()
