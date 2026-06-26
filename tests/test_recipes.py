"""Tests for the RecipeService class."""

from unittest.mock import AsyncMock, MagicMock

import pytest

from rohlik_api.auth import AuthManager
from rohlik_api.http_client import HttpClient
from rohlik_api.services.recipes import RecipeService


@pytest.fixture
def mock_http():
    """Create a mock HttpClient."""
    http = MagicMock(spec=HttpClient)
    http.get = AsyncMock()
    http.post = AsyncMock()
    return http


@pytest.fixture
def mock_auth():
    """Create a mock AuthManager."""
    auth = MagicMock(spec=AuthManager)
    auth.ensure_logged_in = AsyncMock()
    auth.is_logged_in = True
    return auth


class TestRecipeServiceSearch:
    """Tests for RecipeService.search method."""

    @pytest.mark.asyncio
    async def test_search_returns_recipes(self, mock_http, mock_auth):
        """Test search returns properly formatted recipe data."""
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "status": 200,
            "data": {
                "meals": [
                    {
                        "id": 59,
                        "name": "Rajská omáčka s hovězím masem",
                        "link": "/chef/59-rajska-omacka",
                        "image": "/images/meals/small/59.jpg",
                        "isFavorite": False,
                        "isNew": True,
                        "isBestSeller": False,
                    },
                    {
                        "id": 39,
                        "name": "Kuře s rajčaty",
                        "link": "/chef/39-kure-s-rajcaty",
                        "image": "/images/meals/small/39.jpg",
                        "isFavorite": True,
                        "isNew": False,
                        "isBestSeller": True,
                    },
                ],
                "totalHits": 2,
            },
        }
        mock_response.raise_for_status = MagicMock()
        mock_http.get.return_value = mock_response

        service = RecipeService(mock_http, mock_auth)
        result = await service.search("rajská")

        assert result is not None
        assert len(result["recipes"]) == 2
        assert result["total_hits"] == 2
        assert result["recipes"][0]["id"] == 59
        assert result["recipes"][0]["name"] == "Rajská omáčka s hovězím masem"
        assert result["recipes"][0]["is_new"] is True
        assert result["recipes"][1]["is_favorite"] is True

    @pytest.mark.asyncio
    async def test_search_returns_none_on_error(self, mock_http, mock_auth):
        """Test search returns None when request fails."""
        import httpx

        mock_http.get.side_effect = httpx.HTTPError("Connection failed")

        service = RecipeService(mock_http, mock_auth)
        result = await service.search("test")

        assert result is None

    @pytest.mark.asyncio
    async def test_search_with_pagination(self, mock_http, mock_auth):
        """Test search passes pagination parameters."""
        mock_response = MagicMock()
        mock_response.json.return_value = {"data": {"meals": [], "totalHits": 0}}
        mock_response.raise_for_status = MagicMock()
        mock_http.get.return_value = mock_response

        service = RecipeService(mock_http, mock_auth)
        await service.search("test", limit=5, offset=10)

        call_args = mock_http.get.call_args
        url = call_args[0][0]
        assert "limit=5" in url
        assert "offset=10" in url


class TestRecipeServiceGetDetail:
    """Tests for RecipeService.get_detail method."""

    @pytest.mark.asyncio
    async def test_get_detail_returns_recipe(self, mock_http, mock_auth):
        """Test get_detail returns properly formatted recipe details."""
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "status": 200,
            "data": {
                "id": 59,
                "name": "Rajská omáčka s hovězím masem",
                "duration": "Do hodinky",
                "servings": [{"name": "4 PORCE", "default": True}],
                "image": {"path": "/images/meals/large/59.jpg"},
                "author": {"name": "Roman Vaněk", "annotation": "Test annotation"},
                "tips": [{"content": "Tip 1"}, {"content": "Tip 2"}],
                "ingredients": [
                    {
                        "name": "HOVĚZÍ VÝVAR",
                        "position": 0,
                        "items": [
                            {
                                "name": "Mrkev",
                                "ingredientId": 56,
                                "ingredientName": "2 větší mrkve",
                                "productsCount": 4,
                                "imgPath": "/images/mrkev.jpg",
                            }
                        ],
                    }
                ],
                "directions": [
                    {
                        "name": "POSTUP",
                        "position": 0,
                        "steps": [
                            {"stepNumber": 1, "content": "Step 1 content"},
                            {"stepNumber": 2, "content": "Step 2 content"},
                        ],
                    }
                ],
                "isFavorite": False,
                "link": "/chef/59-rajska-omacka",
            },
        }
        mock_response.raise_for_status = MagicMock()
        mock_http.get.return_value = mock_response

        service = RecipeService(mock_http, mock_auth)
        result = await service.get_detail(59)

        assert result is not None
        assert result["id"] == 59
        assert result["name"] == "Rajská omáčka s hovězím masem"
        assert result["duration"] == "Do hodinky"
        assert result["author"]["name"] == "Roman Vaněk"
        assert len(result["tips"]) == 2
        assert len(result["ingredients"]) == 1
        assert result["ingredients"][0]["items"][0]["ingredient_id"] == 56
        assert len(result["directions"]) == 1
        assert len(result["directions"][0]["steps"]) == 2

    @pytest.mark.asyncio
    async def test_get_detail_returns_none_on_error(self, mock_http, mock_auth):
        """Test get_detail returns None when request fails."""
        import httpx

        mock_http.get.side_effect = httpx.HTTPError("Connection failed")

        service = RecipeService(mock_http, mock_auth)
        result = await service.get_detail(59)

        assert result is None


class TestRecipeServiceGetIngredientProducts:
    """Tests for RecipeService.get_ingredient_products method."""

    @pytest.mark.asyncio
    async def test_get_ingredient_products_returns_data(self, mock_http, mock_auth):
        """Test get_ingredient_products returns properly formatted data."""
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "status": 200,
            "data": {
                "ingredients": [
                    {
                        "id": 102,
                        "products": [
                            {
                                "productId": 1350675,
                                "productName": "Celer bulvový 1ks",
                                "imgPath": "/images/celer.jpg",
                                "price": {"full": 41.88, "currency": "Kč"},
                                "unit": "kg",
                                "textualAmount": "cca 1,2 kg",
                                "inStock": True,
                                "favourite": True,
                            },
                            {
                                "productId": 1313889,
                                "productName": "Celer bulva s natí",
                                "imgPath": "/images/celer2.jpg",
                                "price": {"full": 49.9, "currency": "Kč"},
                                "unit": "ks",
                                "textualAmount": "1 ks",
                                "inStock": True,
                                "favourite": False,
                            },
                        ],
                        "totalHits": 3,
                    }
                ]
            },
        }
        mock_response.raise_for_status = MagicMock()
        mock_http.post.return_value = mock_response

        service = RecipeService(mock_http, mock_auth)
        result = await service.get_ingredient_products([102])

        assert result is not None
        assert len(result["ingredients"]) == 1
        assert result["ingredients"][0]["ingredient_id"] == 102
        assert len(result["ingredients"][0]["products"]) == 2
        assert result["ingredients"][0]["products"][0]["product_id"] == 1350675
        assert result["ingredients"][0]["products"][0]["price"] == "41.88 Kč"
        assert result["ingredients"][0]["products"][0]["in_stock"] is True
        assert result["ingredients"][0]["products"][0]["is_favorite"] is True

    @pytest.mark.asyncio
    async def test_get_ingredient_products_sends_correct_payload(self, mock_http, mock_auth):
        """Test get_ingredient_products sends correct payload."""
        mock_response = MagicMock()
        mock_response.json.return_value = {"data": {"ingredients": []}}
        mock_response.raise_for_status = MagicMock()
        mock_http.post.return_value = mock_response

        service = RecipeService(mock_http, mock_auth)
        await service.get_ingredient_products([102, 56], limit=10, offset=5)

        mock_http.post.assert_called_once()
        call_kwargs = mock_http.post.call_args[1]
        assert call_kwargs["json"]["ingredientIds"] == [102, 56]
        assert call_kwargs["json"]["limit"] == 10
        assert call_kwargs["json"]["offset"] == 5

    @pytest.mark.asyncio
    async def test_get_ingredient_products_returns_none_on_error(self, mock_http, mock_auth):
        """Test get_ingredient_products returns None when request fails."""
        import httpx

        mock_http.post.side_effect = httpx.HTTPError("Connection failed")

        service = RecipeService(mock_http, mock_auth)
        result = await service.get_ingredient_products([102])

        assert result is None
