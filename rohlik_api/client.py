"""Rohlik.cz API Client implementation."""

import httpx
from typing import Optional, Dict, Any, List


class RohlikAPI:
    """Client for interacting with Rohlik.cz API.
    
    This client uses httpx with HTTP/2 support for optimal performance
    when communicating with the Rohlik.cz API endpoints.
    
    Args:
        base_url: Base URL for the Rohlik.cz API. Defaults to https://www.rohlik.cz
        timeout: Request timeout in seconds. Defaults to 30.0
        headers: Optional custom headers to include in all requests
        
    Example:
        >>> from rohlik_api import RohlikAPI
        >>> client = RohlikAPI()
        >>> # Use the client to make API calls
        >>> client.close()
        
        Or use as a context manager:
        >>> with RohlikAPI() as client:
        ...     # Make API calls
        ...     pass
    """
    
    def __init__(
        self,
        base_url: str = "https://www.rohlik.cz",
        timeout: float = 30.0,
        headers: Optional[Dict[str, str]] = None,
    ):
        """Initialize the Rohlik API client."""
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        
        # Default headers
        default_headers = {
            "User-Agent": "rohlik-api-python/0.1.0",
            "Accept": "application/json",
        }
        
        if headers:
            default_headers.update(headers)
        
        # Initialize httpx client with HTTP/2 support
        self.client = httpx.Client(
            base_url=self.base_url,
            timeout=timeout,
            headers=default_headers,
            http2=True,
            follow_redirects=True,
        )
    
    def __enter__(self):
        """Context manager entry."""
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.close()
    
    def close(self):
        """Close the HTTP client and release resources."""
        if self.client:
            self.client.close()
    
    def get(
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
        return self.client.get(endpoint, params=params, headers=headers)
    
    def post(
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
        return self.client.post(endpoint, data=data, json=json, headers=headers)
    
    def put(
        self,
        endpoint: str,
        data: Optional[Dict[str, Any]] = None,
        json: Optional[Dict[str, Any]] = None,
        headers: Optional[Dict[str, str]] = None,
    ) -> httpx.Response:
        """Make a PUT request to the API.
        
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
        return self.client.put(endpoint, data=data, json=json, headers=headers)
    
    def delete(
        self,
        endpoint: str,
        headers: Optional[Dict[str, str]] = None,
    ) -> httpx.Response:
        """Make a DELETE request to the API.
        
        Args:
            endpoint: API endpoint path
            headers: Optional additional headers for this request
            
        Returns:
            httpx.Response object
            
        Raises:
            httpx.HTTPError: If the request fails
        """
        return self.client.delete(endpoint, headers=headers)
    
    def get_categories(self) -> List[Dict[str, Any]]:
        """Get list of product categories.
        
        Returns:
            List of category dictionaries
            
        Example:
            >>> client = RohlikAPI()
            >>> categories = client.get_categories()
            >>> client.close()
        """
        response = self.get("/api/v1/categories")
        response.raise_for_status()
        return response.json()
    
    def get_products(
        self,
        category_id: Optional[int] = None,
        search: Optional[str] = None,
        limit: int = 50,
        offset: int = 0,
    ) -> List[Dict[str, Any]]:
        """Get list of products.
        
        Args:
            category_id: Optional category ID to filter products
            search: Optional search query
            limit: Maximum number of products to return
            offset: Offset for pagination
            
        Returns:
            List of product dictionaries
            
        Example:
            >>> client = RohlikAPI()
            >>> products = client.get_products(search="mleko", limit=10)
            >>> client.close()
        """
        params = {"limit": limit, "offset": offset}
        if category_id is not None:
            params["category_id"] = category_id
        if search:
            params["search"] = search
        
        response = self.get("/api/v1/products", params=params)
        response.raise_for_status()
        return response.json()
    
    def get_product(self, product_id: int) -> Dict[str, Any]:
        """Get details of a specific product.
        
        Args:
            product_id: Product ID
            
        Returns:
            Product details dictionary
            
        Example:
            >>> client = RohlikAPI()
            >>> product = client.get_product(12345)
            >>> client.close()
        """
        response = self.get(f"/api/v1/products/{product_id}")
        response.raise_for_status()
        return response.json()
