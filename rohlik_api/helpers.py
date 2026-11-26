"""Helper utilities for the Rohlik.cz API client."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from .sites import SITES


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


def cdn_url_for(base_url: str) -> str:
    """Return the image CDN base URL for a shop's API ``base_url``.

    Known shops use :attr:`~rohlik_api.Site.cdn_url`. For any other base URL the
    ``www.`` host prefix is swapped for ``cdn.``, the pattern the known shops
    follow (``https://www.rohlik.cz`` -> ``https://cdn.rohlik.cz``).

    Args:
        base_url: The shop's base URL, e.g. ``"https://www.gurkerl.at"``.

    Returns:
        The CDN base URL without a trailing slash.
    """
    base = base_url.rstrip("/")
    for site in SITES.values():
        if site.base_url == base and site.cdn_url:
            return site.cdn_url
    return base.replace("://www.", "://cdn.", 1)


def image_url(path: Any, cdn_url: str = "") -> str | None:
    """Turn an image path from the API into a full URL.

    Absolute URLs are returned unchanged, protocol-relative ones (``//host/…``)
    get ``https:``, and relative paths are joined onto ``cdn_url``.

    Args:
        path: The image path or URL as returned by the API (``imgPath``).
        cdn_url: Base URL of the shop's image CDN, see :func:`cdn_url_for`.

    Returns:
        The full image URL, or ``None`` when ``path`` is empty or not a string,
        or when it is relative and no ``cdn_url`` is given.
    """
    if not isinstance(path, str) or not path.strip():
        return None
    text: str = path.strip()
    if text.startswith(("https://", "http://")):
        return text
    if text.startswith("//"):
        return f"https:{text}"
    if not cdn_url:
        return None
    return f"{cdn_url.rstrip('/')}/{text.lstrip('/')}"
