"""Helper utilities for the Rohlik.cz API client."""

from __future__ import annotations

from typing import Any


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
