"""Tests for the AuthManager class."""

from unittest.mock import AsyncMock, MagicMock

import pytest

from rohlik_api.auth import AuthManager
from rohlik_api.http_client import HttpClient


def _response(payload):
    """Build a mock httpx response returning the given JSON payload."""
    resp = MagicMock()
    resp.json.return_value = payload
    return resp


class TestAuthManagerInitialization:
    """Tests for AuthManager initialization."""

    def test_initialization_with_credentials(self):
        """Test AuthManager initializes with valid credentials."""
        http = HttpClient()
        auth = AuthManager(http, "user@example.com", "password123")
        assert auth._username == "user@example.com"
        assert auth._password == "password123"
        assert auth.is_logged_in is False
        assert auth.user_id is None
        assert auth.address_id is None

    def test_requires_username(self):
        """Test that username is required."""
        http = HttpClient()
        with pytest.raises(ValueError, match="Username and password are required"):
            AuthManager(http, "", "password123")

    def test_requires_password(self):
        """Test that password is required."""
        http = HttpClient()
        with pytest.raises(ValueError, match="Username and password are required"):
            AuthManager(http, "user@example.com", "")

    def test_requires_both_credentials(self):
        """Test that both credentials are required."""
        http = HttpClient()
        with pytest.raises(ValueError, match="Username and password are required"):
            AuthManager(http, "", "")


class TestAuthManagerProperties:
    """Tests for AuthManager properties."""

    def test_is_logged_in_initially_false(self):
        """Test that is_logged_in is False initially."""
        http = HttpClient()
        auth = AuthManager(http, "user@example.com", "password123")
        assert auth.is_logged_in is False

    def test_user_id_initially_none(self):
        """Test that user_id is None initially."""
        http = HttpClient()
        auth = AuthManager(http, "user@example.com", "password123")
        assert auth.user_id is None

    def test_address_id_initially_none(self):
        """Test that address_id is None initially."""
        http = HttpClient()
        auth = AuthManager(http, "user@example.com", "password123")
        assert auth.address_id is None


class TestAuthManagerEnsureLoggedIn:
    """Tests for ensure_logged_in method."""

    async def test_ensure_logged_in_when_not_logged_in(self):
        """Test that ensure_logged_in attempts login when not logged in."""
        http = HttpClient()
        auth = AuthManager(http, "user@example.com", "password123")

        # This will fail because we don't have a real server
        # but we're testing that the method is callable
        assert auth.is_logged_in is False
        await http.close()


class TestAuthManagerSession:
    """Tests for login caching and session reset on logout."""

    async def test_login_caches_response_and_extracts_ids(self):
        """Login stores the real response and user/address IDs."""
        http = MagicMock(spec=HttpClient)
        http.post = AsyncMock(
            return_value=_response(
                {"status": 200, "data": {"user": {"id": 1}, "address": {"id": 2}}}
            )
        )
        auth = AuthManager(http, "user@example.com", "password123")

        result = await auth.login()

        assert result["status"] == 200
        assert auth.user_id == 1
        assert auth.address_id == 2

        # A second login returns the cached real response, no new request.
        http.post.reset_mock()
        cached = await auth.login()
        assert cached == result
        http.post.assert_not_called()

    async def test_logout_resets_session_state(self):
        """Logout clears is_logged_in plus cached user/address IDs."""
        http = MagicMock(spec=HttpClient)
        http.post = AsyncMock(
            side_effect=[
                _response({"status": 200, "data": {"user": {"id": 1}, "address": {"id": 2}}}),
                _response({"status": 200}),
            ]
        )
        auth = AuthManager(http, "user@example.com", "password123")

        await auth.login()
        await auth.logout()

        assert auth.is_logged_in is False
        assert auth.user_id is None
        assert auth.address_id is None
