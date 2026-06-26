"""Tests for the RohlikAPI client class."""

from unittest.mock import AsyncMock

import pytest

from rohlik_api import RohlikAPI, mask_data

# Test credentials used throughout tests
TEST_USERNAME = "test@example.com"
TEST_PASSWORD = "password123"


class TestClientInitialization:
    """Tests for client initialization."""

    def test_client_initialization(self):
        """Test that client initializes correctly with required credentials."""
        client = RohlikAPI(username=TEST_USERNAME, password=TEST_PASSWORD)
        assert client.base_url == "https://www.rohlik.cz"
        assert client.timeout == 30.0
        assert client._http._client is None  # Lazy initialization

    def test_client_with_credentials(self):
        """Test client initializes with username and password."""
        client = RohlikAPI(username="test@example.com", password="password123")
        assert client._auth._username == "test@example.com"
        assert client._auth._password == "password123"
        assert client._auth.user_id is None
        assert client._auth.address_id is None
        assert client.is_logged_in is False

    def test_client_requires_credentials(self):
        """Test that client raises ValueError without credentials."""
        with pytest.raises(TypeError):
            RohlikAPI()
        with pytest.raises(ValueError, match="Username and password are required"):
            RohlikAPI(username="", password="")
        with pytest.raises(ValueError, match="Username and password are required"):
            RohlikAPI(username="test@example.com", password="")

    def test_client_custom_base_url(self):
        """Test client with custom base URL."""
        custom_url = "https://custom.rohlik.cz"
        client = RohlikAPI(username=TEST_USERNAME, password=TEST_PASSWORD, base_url=custom_url)
        assert client.base_url == custom_url

    def test_client_custom_timeout(self):
        """Test client with custom timeout."""
        custom_timeout = 60.0
        client = RohlikAPI(username=TEST_USERNAME, password=TEST_PASSWORD, timeout=custom_timeout)
        assert client.timeout == custom_timeout

    def test_client_custom_headers(self):
        """Test client with custom headers."""
        custom_headers = {"X-Custom-Header": "TestValue"}
        client = RohlikAPI(username=TEST_USERNAME, password=TEST_PASSWORD, headers=custom_headers)
        assert "X-Custom-Header" in client._http._headers
        assert client._http._headers["X-Custom-Header"] == "TestValue"

    def test_client_default_headers(self):
        """Test that default headers are set."""
        client = RohlikAPI(username=TEST_USERNAME, password=TEST_PASSWORD)
        assert "User-Agent" in client._http._headers
        assert "Accept" in client._http._headers
        assert client._http._headers["Accept"] == "application/json"

    def test_client_lazy_initialization(self):
        """Test that client is lazily initialized."""
        client = RohlikAPI(username=TEST_USERNAME, password=TEST_PASSWORD)
        assert client._http._client is None
        # Accessing client property creates the client
        _ = client.client
        assert client._http._client is not None

    def test_client_base_url_trailing_slash(self):
        """Test that trailing slash is removed from base URL."""
        client = RohlikAPI(
            username=TEST_USERNAME, password=TEST_PASSWORD, base_url="https://www.rohlik.cz/"
        )
        assert client.base_url == "https://www.rohlik.cz"


class TestAsyncContextManager:
    """Tests for async context manager."""

    @pytest.mark.asyncio
    async def test_async_context_manager(self):
        """Test client works as async context manager."""
        async with RohlikAPI(
            username=TEST_USERNAME, password=TEST_PASSWORD, auto_login=False
        ) as client:
            assert client.base_url == "https://www.rohlik.cz"

    @pytest.mark.asyncio
    async def test_client_close(self):
        """Test that client closes without error."""
        client = RohlikAPI(username=TEST_USERNAME, password=TEST_PASSWORD, auto_login=False)
        _ = client.client  # Create the client
        await client.close()
        assert client._http._client is None


class TestMaskData:
    """Tests for the mask_data utility function."""

    def test_mask_simple_dict(self):
        """Test masking a simple dictionary."""
        input_data = {"name": "John", "email": "john@example.com"}
        result = mask_data(input_data)
        assert result["name"] == "XXXXXXX"
        assert result["email"] == "XXXXXXX"

    def test_mask_nested_dict(self):
        """Test masking a nested dictionary."""
        input_data = {"user": {"name": "John", "email": "john@example.com"}}
        result = mask_data(input_data)
        assert result["user"]["name"] == "XXXXXXX"
        assert result["user"]["email"] == "XXXXXXX"

    def test_mask_preserves_none(self):
        """Test that None values are preserved."""
        input_data = {"name": "John", "email": None}
        result = mask_data(input_data)
        assert result["name"] == "XXXXXXX"
        assert result["email"] is None

    def test_mask_list_values(self):
        """Test masking list values."""
        input_data = {"items": ["item1", "item2"]}
        result = mask_data(input_data)
        assert result["items"] == ["XXXXXXX", "XXXXXXX"]

    def test_mask_non_dict_returns_unchanged(self):
        """Test that non-dict input returns unchanged."""
        assert mask_data("string") == "string"
        assert mask_data(123) == 123
        assert mask_data(None) is None


class TestClientAuthentication:
    """Tests for authentication methods."""

    def test_credentials_required_on_init(self):
        """Test that credentials are required on initialization."""
        with pytest.raises(TypeError):
            RohlikAPI()
        with pytest.raises(ValueError, match="Username and password are required"):
            RohlikAPI(username="", password="")

    @pytest.mark.asyncio
    async def test_get_shopping_list_requires_id(self):
        """Test that get_shopping_list raises ValueError without ID."""
        client = RohlikAPI(username="test@example.com", password="password123", auto_login=False)
        with pytest.raises(ValueError, match="Missing argument"):
            await client.account.get_shopping_list("")
        await client.close()

    @pytest.mark.asyncio
    async def test_login_delegates_to_auth(self):
        """Test that client.login() delegates to the auth manager."""
        client = RohlikAPI(username=TEST_USERNAME, password=TEST_PASSWORD, auto_login=False)
        client._auth.login = AsyncMock(return_value={"status": 200})

        result = await client.login()

        client._auth.login.assert_awaited_once()
        assert result == {"status": 200}

    @pytest.mark.asyncio
    async def test_logout_delegates_to_auth(self):
        """Test that client.logout() delegates to the auth manager."""
        client = RohlikAPI(username=TEST_USERNAME, password=TEST_PASSWORD, auto_login=False)
        client._auth.logout = AsyncMock()

        await client.logout()

        client._auth.logout.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_context_manager_auto_login(self):
        """Test that entering the context manager logs in when auto_login is True."""
        client = RohlikAPI(username=TEST_USERNAME, password=TEST_PASSWORD, auto_login=True)
        client._auth.login = AsyncMock(return_value={"status": 200})
        client._auth.logout = AsyncMock()
        client._http.close = AsyncMock()

        async with client:
            client._auth.login.assert_awaited_once()

    def test_user_and_address_id_properties(self):
        """Test that user_id and address_id properties expose auth state."""
        client = RohlikAPI(username=TEST_USERNAME, password=TEST_PASSWORD)
        assert client.user_id is None
        assert client.address_id is None
        client._auth._user_id = 111
        client._auth._address_id = 222
        assert client.user_id == 111
        assert client.address_id == 222


class TestClientEndpoints:
    """Tests for endpoint configuration."""

    def test_endpoints_defined(self):
        """Test that all required endpoints are defined in Endpoints class."""
        from rohlik_api import Endpoints

        # Check that required endpoint constants exist
        assert hasattr(Endpoints, "DELIVERY")
        assert hasattr(Endpoints, "NEXT_ORDER")
        assert hasattr(Endpoints, "ANNOUNCEMENTS")
        assert hasattr(Endpoints, "BAGS")
        assert hasattr(Endpoints, "TIMESLOT_RESERVATION")
        assert hasattr(Endpoints, "LAST_ORDER")
        assert hasattr(Endpoints, "PREMIUM_PROFILE")
        assert hasattr(Endpoints, "DELIVERY_ANNOUNCEMENTS")

        # Check that builder methods exist
        assert callable(getattr(Endpoints, "timeslots", None))
        assert callable(getattr(Endpoints, "delivered_orders", None))

    def test_service_properties_exist(self):
        """Test that all service properties are available on RohlikAPI."""
        client = RohlikAPI(username=TEST_USERNAME, password=TEST_PASSWORD)
        assert hasattr(client, "cart")
        assert hasattr(client, "products")
        assert hasattr(client, "orders")
        assert hasattr(client, "delivery")
        assert hasattr(client, "account")
        assert hasattr(client, "recipes")
