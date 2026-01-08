"""Rohlik.cz API Client implementation."""

import logging
import httpx
from typing import Optional, Dict, Any, List

from .errors import InvalidCredentialsError, RohlikAPIError, APIRequestFailedError

_LOGGER = logging.getLogger(__name__)

BASE_URL = "https://www.rohlik.cz"


def mask_data(input_dict: Any) -> Any:
    """Takes a dictionary and replaces all non-null values with "XXXXXXX". Null values (None) remain unchanged."""
    if not isinstance(input_dict, dict):
        return input_dict

    result = {}
    for key, value in input_dict.items():
        if value is None:
            result[key] = None
        elif isinstance(value, dict):
            result[key] = mask_data(value)
        elif isinstance(value, list):
            result[key] = [mask_data(item) if isinstance(item, dict)
                           else "XXXXXXX" if item is not None else None
                           for item in value]
        else:
            result[key] = "XXXXXXX"

    return result



class RohlikAPI:
    """Async client for interacting with Rohlik.cz API.

    This client uses httpx with HTTP/2 support for optimal performance
    when communicating with the Rohlik.cz API endpoints.
    
    When used as an async context manager with auto_login=True (default),
    the client automatically logs in on entry and logs out on exit.

    Args:
        username: Email address used for Rohlik.cz login (required)
        password: Password for Rohlik.cz account (required)
        base_url: Base URL for the Rohlik.cz API. Defaults to https://www.rohlik.cz
        timeout: Request timeout in seconds. Defaults to 30.0
        headers: Optional custom headers to include in all requests
        auto_login: If True (default), automatically login when using context manager

    Example:
        >>> from rohlik_api import RohlikAPI
        >>> async def main():
        ...     async with RohlikAPI("username@example.com", "password") as client:
        ...         # No need to call login() - it's automatic!
        ...         data = await client.get_cart_content()
        ...         print(data)
        ...     # logout is called automatically on exit
    """
    
    ENDPOINTS = {
        "delivery": "/services/frontend-service/first-delivery?reasonableDeliveryTime=true",
        "next_order": "/api/v3/orders/upcoming",
        "announcements": "/services/frontend-service/announcements/top",
        "bags": "/api/v1/reusable-bags/user-info",
        "timeslot": "/services/frontend-service/v1/timeslot-reservation",
        "last_order": "/api/v3/orders/delivered?offset=0&limit=1",
        "premium_profile": "/services/frontend-service/premium/profile",
        "next_delivery_slot": "/services/frontend-service/timeslots-api/",
        "delivery_announcements": "/services/frontend-service/announcements/delivery",
        "delivered_orders": "/api/v3/orders/delivered?offset=0&limit=50"
    }

    def __init__(
        self,
        username: str,
        password: str,
        base_url: str = BASE_URL,
        timeout: float = 30.0,
        headers: Optional[Dict[str, str]] = None,
        auto_login: bool = True,
    ):
        """Initialize the Rohlik API client.

        Args:
            username: Email address used for Rohlik.cz login (required)
            password: Password for Rohlik.cz account (required)
            base_url: Base URL for the Rohlik.cz API
            timeout: Request timeout in seconds
            headers: Optional custom headers to include in all requests
            auto_login: If True, automatically login when using context manager
        """
        if not username or not password:
            raise ValueError("Username and password are required")

        self._username = username
        self._password = password
        self._auto_login = auto_login
        self._user_id: Optional[int] = None
        self._address_id: Optional[int] = None
        self._is_logged_in: bool = False
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        
        # Default headers
        default_headers = {
            "User-Agent": "rohlik-api-python/0.1.0",
            "Accept": "application/json",
        }
        
        if headers:
            default_headers.update(headers)
        
        self._default_headers = default_headers
        self._client: Optional[httpx.AsyncClient] = None

    @property
    def client(self) -> httpx.AsyncClient:
        """Get or create the async HTTP client."""
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(
                base_url=self.base_url,
                timeout=self.timeout,
                headers=self._default_headers,
                http2=True,
                follow_redirects=True,
            )
        return self._client

    @property
    def is_logged_in(self) -> bool:
        """Check if the client is currently logged in."""
        return self._is_logged_in

    async def __aenter__(self):
        """Async context manager entry - logs in automatically if auto_login is True."""
        if self._auto_login:
            await self.login()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit - logout and close."""
        await self.close()

    async def close(self):
        """Close the HTTP client and release resources. Logs out if logged in."""
        if self._is_logged_in:
            try:
                await self.logout()
            except Exception as err:
                _LOGGER.error(f"Error during logout on close: {err}")

        if self._client is not None and not self._client.is_closed:
            await self._client.aclose()
            self._client = None

    async def _ensure_logged_in(self) -> None:
        """Ensure the client is logged in, login if not."""
        if not self._is_logged_in:
            await self.login()

    async def _get(
        self,
        endpoint: str,
        params: Optional[Dict[str, Any]] = None,
        headers: Optional[Dict[str, str]] = None,
    ) -> httpx.Response:
        """Make a GET request to the API.
        
        Args:
            endpoint: API endpoint path
            params: Optional query parameters
            headers: Optional additional headers for this request
            
        Returns:
            httpx.Response object
            
        Raises:
            httpx.HTTPError: If the request fails
        """
        return await self.client.get(endpoint, params=params, headers=headers)

    async def _post(
        self,
        endpoint: str,
        data: Optional[Dict[str, Any]] = None,
        json: Optional[Dict[str, Any]] = None,
        headers: Optional[Dict[str, str]] = None,
    ) -> httpx.Response:
        """Make a POST request to the API.
        
        Args:
            endpoint: API endpoint path
            data: Optional form data
            json: Optional JSON data
            headers: Optional additional headers for this request
            
        Returns:
            httpx.Response object
            
        Raises:
            httpx.HTTPError: If the request fails
        """
        return await self.client.post(endpoint, data=data, json=json, headers=headers)


    async def _delete(
        self,
        endpoint: str,
        params: Optional[Dict[str, Any]] = None,
        headers: Optional[Dict[str, str]] = None,
    ) -> httpx.Response:
        """Make a DELETE request to the API.
        
        Args:
            endpoint: API endpoint path
            params: Optional query parameters
            headers: Optional additional headers for this request
            
        Returns:
            httpx.Response object
            
        Raises:
            httpx.HTTPError: If the request fails
        """
        return await self.client.delete(endpoint, params=params, headers=headers)

    # -------------------------------------------------------------------------
    # Authentication Methods
    # -------------------------------------------------------------------------

    async def login(self) -> Dict[str, Any]:
        """
        Authenticate with the Rohlik.cz service.

        If already logged in, returns cached login response without making a new request.

        Returns:
            dict: The JSON response containing authentication data and user information

        Raises:
            InvalidCredentialsError: If the credentials are invalid
            APIRequestFailedError: If the login request fails
        """
        if self._is_logged_in:
            _LOGGER.debug("Already logged in, skipping login request")
            return {"status": 200, "message": "Already logged in"}


        login_data = {"email": self._username, "password": self._password, "name": ""}
        login_url = "/services/frontend-service/login"

        try:
            response = await self._post(login_url, json=login_data)
            login_response = response.json()

            if login_response.get("status") != 200:
                if login_response.get("status") == 401:
                    messages = login_response.get("messages", [])
                    error_msg = messages[0].get("content", "Invalid credentials") if messages else "Invalid credentials"
                    raise InvalidCredentialsError(error_msg)
                else:
                    messages = login_response.get("messages", [])
                    error_msg = messages[0].get("content", "Unknown error") if messages else "Unknown error"
                    raise RohlikAPIError(f"Unknown error occurred during login: {error_msg}")

            # Mark as logged in
            self._is_logged_in = True

            # Extract user and address IDs
            if not self._user_id:
                self._user_id = login_response.get("data", {}).get("user", {}).get("id")

            if not self._address_id:
                try:
                    self._address_id = login_response.get("data", {}).get("address", {}).get("id")
                except AttributeError:
                    _LOGGER.error(f"Address cannot be retrieved from login data. Login response: {mask_data(login_response)}")

            return login_response

        except httpx.HTTPError as err:
            raise APIRequestFailedError(f"Cannot connect to website! Check your internet connection and try again: {err}")

    async def logout(self) -> None:
        """
        Log out from the Rohlik.cz service.

        Raises:
            RohlikAPIError: If logout fails
            APIRequestFailedError: If the request fails
        """
        if not self._is_logged_in:
            _LOGGER.debug("Not logged in, skipping logout request")
            return

        logout_url = "/services/frontend-service/logout"

        try:
            response = await self._post(logout_url)
            logout_response = response.json()

            if logout_response.get("status") != 200:
                raise RohlikAPIError(f"Unknown error occurred during logout: {logout_response}")

            self._is_logged_in = False

        except httpx.HTTPError as err:
            self._is_logged_in = False  # Reset state even on error
            raise APIRequestFailedError(f"Cannot connect to website! Check your internet connection and try again: {err}")

    # -------------------------------------------------------------------------
    # Data Retrieval Methods
    # -------------------------------------------------------------------------

    async def get_data(self) -> Dict[str, Any]:
        """
        Retrieve all account data from Rohlik.cz in a single operation.

        Returns:
            dict: A dictionary containing all data from various Rohlik endpoints,
                 including login information, delivery details, cart contents, etc.

        Raises:
            APIRequestFailedError: If connection fails
        """
        result: Dict[str, Any] = {}

        # Step 1: Ensure we are logged in
        result["login"] = await self.login()

        try:
            # Step 2: Get data from all other endpoints
            for endpoint_name, path in self.ENDPOINTS.items():

                if endpoint_name == "next_delivery_slot":
                    if self._address_id and self._user_id:
                        path = f"{path}0?userId={self._user_id}&addressId={self._address_id}&reasonableDeliveryTime=true"
                    else:
                        result[endpoint_name] = None
                        continue

                try:
                    response = await self._get(path)
                    response.raise_for_status()
                    result[endpoint_name] = response.json()
                except httpx.HTTPError as err:
                    _LOGGER.error(f"Error fetching {endpoint_name}: {err}")
                    result[endpoint_name] = None

            # Get cart content
            try:
                result["cart"] = await self.get_cart_content()
            except Exception as err:
                _LOGGER.error(f"Error fetching cart: {err}")
                result["cart"] = None

            return result

        except httpx.HTTPError as err:
            raise APIRequestFailedError(f"Cannot connect to website! Check your internet connection and try again: {err}")

    # -------------------------------------------------------------------------
    # Product Methods
    # -------------------------------------------------------------------------

    async def search_product(
        self,
        product_name: str,
        limit: int = 10,
        favourite: bool = False
    ) -> Optional[Dict[str, Any]]:
        """
        Search for products by name.

        Args:
            product_name: The name or search term for the product
            limit: Number of products returned
            favourite: Whether only favourite items shall be returned

        Returns:
            dict: Search results with product details, or None if no products found
        """
        await self._ensure_logged_in()

        search_url = "/services/frontend-service/search-metadata"
        search_payload = {
            "search": product_name,
            "offset": 0,
            "limit": limit + 5,
            "companyId": 1,
            "filterData": {"filters": []},
            "canCorrect": True
        }

        try:
            response = await self._get(search_url, params=search_payload)
            response.raise_for_status()
            search_data = response.json()
            found_products: List[Dict] = search_data.get("data", {}).get("productList", [])

            # Remove sponsored content
            found_products = [p for p in found_products if
                             not any(badge.get("slug") == "promoted" for badge in p.get("badge", []))]

            # Keep only favourites if requested
            if favourite:
                found_products = [p for p in found_products if p.get("favourite", False)]

            # Keep only results up to the specified limit
            if len(found_products) > limit:
                found_products = found_products[:limit]

            if found_products:
                search_results = {"search_results": []}
                for product in found_products:
                    price_info = product.get("price", {})
                    search_results["search_results"].append({
                        "id": product.get("productId"),
                        "name": product.get("productName"),
                        "price": f"{price_info.get('full', '')} {price_info.get('currency', '')}",
                        "brand": product.get("brand"),
                        "amount": product.get("textualAmount")
                    })
                return search_results
            else:
                return None

        except httpx.HTTPError as err:
            _LOGGER.error(f"Request failed: {err}")
            return None

    # -------------------------------------------------------------------------
    # Cart Methods
    # -------------------------------------------------------------------------

    async def get_cart_content(self) -> Dict[str, Any]:
        """
        Fetches the current cart contents.

        Returns:
            dict: Dictionary with cart content including total_price, total_items,
                  can_make_order, and products list

        Raises:
            APIRequestFailedError: If the request fails
        """
        await self._ensure_logged_in()

        cart_url = "/services/frontend-service/v2/cart"

        try:
            response = await self._get(cart_url)
            response.raise_for_status()
            cart_content = response.json()

            data = cart_content.get("data", {})

            # Extract the main cart information
            cart_info: Dict[str, Any] = {
                "total_price": data.get("totalPrice", 0),
                "total_items": len(data.get("items", {})),
                "can_make_order": data.get("submitConditionPassed", False),
                "products": []
            }

            # Process each product item
            for product_id, product_data in data.get("items", {}).items():
                product_info = {
                    "id": product_id,
                    "cart_item_id": product_data.get("orderFieldId", ""),
                    "name": product_data.get("productName", ""),
                    "quantity": product_data.get("quantity", 0),
                    "price": product_data.get("price", 0),
                    "category_name": product_data.get("primaryCategoryName", ""),
                    "brand": product_data.get("brand", "")
                }
                cart_info["products"].append(product_info)

            return cart_info

        except httpx.HTTPError as err:
            _LOGGER.error(f"Request failed: {err}")
            raise APIRequestFailedError(f"Failed to fetch cart: {err}")

    async def add_to_cart(self, product_list: List[Dict[str, Any]]) -> Dict[str, List[int]]:
        """
        Add multiple products to the shopping cart.

        Args:
            product_list: A list of dictionaries containing product_id and quantity
                         for each product to be added to the cart

        Returns:
            dict: A dictionary with 'added_products' key containing list of product IDs
                  that were successfully added

        Raises:
            APIRequestFailedError: If the request fails
        """
        await self._ensure_logged_in()

        cart_url = "/services/frontend-service/v2/cart"
        added_products: List[int] = []

        for product in product_list:
            cart_payload = {
                "actionId": None,
                "productId": int(product["product_id"]),
                "quantity": int(product["quantity"]),
                "recipeId": None,
                "source": "true:Shopping Lists"
            }
            try:
                response = await self._post(cart_url, json=cart_payload)
                response.raise_for_status()
                added_products.append(product["product_id"])
            except httpx.HTTPError as err:
                _LOGGER.error(f"Error adding {product['product_id']} due to {err}")

        return {"added_products": added_products}

    async def delete_from_cart(self, order_field_id: str) -> Dict[str, Any]:
        """
        Delete an item from the shopping cart using orderFieldId.

        Args:
            order_field_id: The orderFieldId of the item to delete

        Returns:
            dict: Response from the deletion operation

        Raises:
            APIRequestFailedError: If the deletion fails
        """
        await self._ensure_logged_in()

        delete_url = "/services/frontend-service/v2/cart"

        try:
            response = await self._delete(delete_url, params={"orderFieldId": order_field_id})
            response.raise_for_status()

            try:
                return response.json()
            except Exception:
                return {"success": True, "status_code": response.status_code}

        except httpx.HTTPError as err:
            _LOGGER.error(f"Error deleting item with orderFieldId {order_field_id}: {err}")
            raise APIRequestFailedError(f"Failed to delete item from cart: {err}")

    # -------------------------------------------------------------------------
    # Shopping List Methods
    # -------------------------------------------------------------------------

    async def get_shopping_list(self, shopping_list_id: str) -> Dict[str, Any]:
        """
        Retrieve a shopping list by its ID.

        Args:
            shopping_list_id: The ID of the shopping list to retrieve

        Returns:
            dict: The shopping list details with 'name' and 'products_in_list' keys

        Raises:
            ValueError: If shopping_list_id is not provided
            APIRequestFailedError: If the request fails
        """
        if not shopping_list_id:
            raise ValueError("Missing argument - shopping list id")

        await self._ensure_logged_in()

        shopping_list_url = f"/api/v1/shopping-lists/id/{shopping_list_id}"

        try:
            response = await self._get(shopping_list_url)
            response.raise_for_status()
            search_data = response.json()

            return {
                "name": search_data.get("name"),
                "products_in_list": search_data.get("products", [])
            }

        except httpx.HTTPError as err:
            _LOGGER.error(f"Request failed: {err}")
            raise APIRequestFailedError(f"Request failed: {err}")

    # -------------------------------------------------------------------------
    # Delivery Methods
    # -------------------------------------------------------------------------

    async def _fetch_endpoint(self, endpoint_key: str, error_context: str) -> Optional[Dict[str, Any]]:
        """
        Fetch data from a predefined endpoint.

        Args:
            endpoint_key: Key from ENDPOINTS dictionary
            error_context: Context string for error logging

        Returns:
            dict: Response data or None if request fails
        """
        await self._ensure_logged_in()

        try:
            response = await self._get(self.ENDPOINTS[endpoint_key])
            response.raise_for_status()
            return response.json()
        except httpx.HTTPError as err:
            _LOGGER.error(f"Error fetching {error_context}: {err}")
            return None

    async def get_delivery_info(self) -> Optional[Dict[str, Any]]:
        """
        Get first delivery information.

        Returns:
            dict: Delivery information or None if request fails
        """
        return await self._fetch_endpoint("delivery", "delivery info")

    async def get_next_order(self) -> Optional[Dict[str, Any]]:
        """
        Get upcoming order information.

        Returns:
            dict: Next order information or None if request fails
        """
        return await self._fetch_endpoint("next_order", "next order")

    async def get_last_order(self) -> Optional[Dict[str, Any]]:
        """
        Get last delivered order information.

        Returns:
            dict: Last order information or None if request fails
        """
        return await self._fetch_endpoint("last_order", "last order")

    async def get_delivered_orders(self, limit: int = 50, offset: int = 0) -> Optional[List[Dict[str, Any]]]:
        """
        Get list of delivered orders.

        Args:
            limit: Maximum number of orders to return
            offset: Offset for pagination

        Returns:
            list: List of delivered orders or None if request fails
        """
        await self._ensure_logged_in()

        try:
            url = f"/api/v3/orders/delivered?offset={offset}&limit={limit}"
            response = await self._get(url)
            response.raise_for_status()
            return response.json()
        except httpx.HTTPError as err:
            _LOGGER.error(f"Error fetching delivered orders: {err}")
            return None

    async def get_timeslot_reservation(self) -> Optional[Dict[str, Any]]:
        """
        Get current timeslot reservation.

        Returns:
            dict: Timeslot reservation information or None if request fails
        """
        return await self._fetch_endpoint("timeslot", "timeslot reservation")

    async def get_premium_profile(self) -> Optional[Dict[str, Any]]:
        """
        Get premium profile information.

        Returns:
            dict: Premium profile information or None if request fails
        """
        return await self._fetch_endpoint("premium_profile", "premium profile")

    async def get_bags_info(self) -> Optional[Dict[str, Any]]:
        """
        Get reusable bags user information.

        Returns:
            dict: Bags information or None if request fails
        """
        return await self._fetch_endpoint("bags", "bags info")

    async def get_announcements(self) -> Optional[Dict[str, Any]]:
        """
        Get top announcements.

        Returns:
            dict: Announcements or None if request fails
        """
        return await self._fetch_endpoint("announcements", "announcements")

    async def get_delivery_announcements(self) -> Optional[Dict[str, Any]]:
        """
        Get delivery announcements.

        Returns:
            dict: Delivery announcements or None if request fails
        """
        return await self._fetch_endpoint("delivery_announcements", "delivery announcements")
