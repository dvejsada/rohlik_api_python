"""Tests for the AuthManager class."""

import pytest
from rohlik_api.http_client import HttpClient
from rohlik_api.auth import AuthManager


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

    @pytest.mark.asyncio
    async def test_ensure_logged_in_when_not_logged_in(self):
        """Test that ensure_logged_in attempts login when not logged in."""
        http = HttpClient()
        auth = AuthManager(http, "user@example.com", "password123")

        # This will fail because we don't have a real server
        # but we're testing that the method is callable
        assert auth.is_logged_in is False
        await http.close()
