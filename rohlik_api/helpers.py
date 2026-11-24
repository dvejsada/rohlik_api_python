"""Helper utilities for the Rohlik.cz API client."""

from __future__ import annotations

from datetime import datetime
from typing import Any


def parse_datetime(value: Any) -> datetime | None:
    """Parse an API timestamp into a timezone-aware :class:`~datetime.datetime`.

    Accepts the formats the shop's API uses, e.g. ``"2026-11-24T12:00:01Z"``,
    ``"2026-11-24T11:40:20.12272713Z"`` (fractional seconds beyond microseconds
    are truncated) and ``"2026-11-24T13:00:01.000+0100"``.

    Args:
        value: The raw value from an API response.

    Returns:
        An aware datetime, or None if the value is missing, not a string, not a
        valid timestamp, or has no UTC offset (a naive value is never guessed).
    """
    if not isinstance(value, str) or not value:
        return None
    try:
        parsed = datetime.fromisoformat(value)
    except ValueError:
        return None
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        return None
    return parsed


def format_price(price_info: dict[str, Any] | None) -> str:
    """Format a Rohlik price object into a ``"<amount> <currency>"`` string.

    Args:
        price_info: A price mapping with optional ``full`` and ``currency`` keys.

    Returns:
        A string like ``"29.90 Kč"``. Missing parts are rendered as empty.
    """
    price_info = price_info or {}
    full = price_info.get("full", "")
    currency = price_info.get("currency", "")
    return f"{full} {currency}".strip()


def mask_data(input_dict: Any) -> Any:
    """Recursively mask all non-null values in a dictionary with ``"XXXXXXX"``.

    Useful for logging API payloads without leaking personal data. ``None``
    values are preserved so the shape of the data remains visible.

    Args:
        input_dict: The value to mask. Non-dict values are returned unchanged.

    Returns:
        A copy of the input with every non-null leaf value replaced by
        ``"XXXXXXX"``.
    """
    if not isinstance(input_dict, dict):
        return input_dict

    result: dict[Any, Any] = {}
    for key, value in input_dict.items():
        if value is None:
            result[key] = None
        elif isinstance(value, dict):
            result[key] = mask_data(value)
        elif isinstance(value, list):
            result[key] = [
                (
                    mask_data(item)
                    if isinstance(item, dict)
                    else "XXXXXXX" if item is not None else None
                )
                for item in value
            ]
        else:
            result[key] = "XXXXXXX"

    return result
