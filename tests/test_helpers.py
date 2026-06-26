"""Tests for helper utilities."""

from rohlik_api.helpers import format_price, mask_data


class TestFormatPrice:
    """Tests for the format_price helper."""

    def test_full_and_currency(self):
        assert format_price({"full": "29.90", "currency": "Kč"}) == "29.90 Kč"

    def test_numeric_amount(self):
        assert format_price({"full": 10, "currency": "Kč"}) == "10 Kč"

    def test_missing_currency(self):
        assert format_price({"full": "29.90"}) == "29.90"

    def test_missing_full(self):
        assert format_price({"currency": "Kč"}) == "Kč"

    def test_empty_dict(self):
        assert format_price({}) == ""

    def test_none(self):
        assert format_price(None) == ""


class TestMaskData:
    """Additional tests for mask_data covering list-of-dicts and mixed lists."""

    def test_list_of_dicts(self):
        result = mask_data({"users": [{"name": "John"}, {"name": "Jane"}]})
        assert result == {"users": [{"name": "XXXXXXX"}, {"name": "XXXXXXX"}]}

    def test_list_with_none(self):
        result = mask_data({"items": ["a", None, "b"]})
        assert result == {"items": ["XXXXXXX", None, "XXXXXXX"]}
