"""Tests for helper utilities."""

from datetime import UTC, datetime, timedelta, timezone

import pytest

from rohlik_api.helpers import format_price, mask_data, parse_datetime


class TestParseDatetime:
    """Tests for parse_datetime against the timestamp formats the API uses."""

    @pytest.mark.parametrize(
        ("raw", "expected"),
        [
            ("2026-11-24T12:00:01Z", datetime(2026, 11, 24, 12, 0, 1, tzinfo=UTC)),
            ("2026-11-24T11:40:19.886Z", datetime(2026, 11, 24, 11, 40, 19, 886000, tzinfo=UTC)),
            (
                "2026-11-24T11:40:20.12272713Z",
                datetime(2026, 11, 24, 11, 40, 20, 122727, tzinfo=UTC),
            ),
            (
                "2026-11-24T13:00:01.000+0100",
                datetime(2026, 11, 24, 13, 0, 1, tzinfo=timezone(timedelta(hours=1))),
            ),
            (
                "2026-11-24T12:45:34.604989874+01:00",
                datetime(2026, 11, 24, 12, 45, 34, 604989, tzinfo=timezone(timedelta(hours=1))),
            ),
        ],
    )
    def test_parses_api_formats(self, raw, expected):
        result = parse_datetime(raw)
        assert result == expected
        assert result.tzinfo is not None

    @pytest.mark.parametrize(
        "raw", [None, "", "not a date", "2026-11-24T12:00:01", 1732449601, True, {"a": 1}]
    )
    def test_rejects_invalid_or_naive(self, raw):
        assert parse_datetime(raw) is None


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
