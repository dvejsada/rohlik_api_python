"""The Rohlík Group shops this client can talk to.

Every shop runs the same backend API, so any of them can be used by passing its
``base_url`` to :class:`~rohlik_api.RohlikAPI`::

    RohlikAPI(username, password, base_url=SITES["de"].base_url)
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Final


@dataclass(frozen=True, slots=True)
class Site:
    """A Rohlík Group shop.

    Attributes:
        code: Short key of the shop in :data:`SITES` (the country code).
        name: Display name, e.g. ``"Knuspr.de"``.
        base_url: Base URL to pass to :class:`~rohlik_api.RohlikAPI`.
        currency: ISO 4217 code of the shop's prices, e.g. ``"EUR"``.
        timezone: IANA timezone the shop's delivery times are in.
        cdn_url: Base URL of the shop's image CDN. Relative image paths from the
            API (``imgPath``) are joined onto it, see
            :func:`~rohlik_api.image_url`. The Rohlík.cz and Gurkerl.at hosts
            are taken from image URLs the API returns; the others follow the
            same ``cdn.<shop domain>`` pattern and are not yet verified.
    """

    code: str
    name: str
    base_url: str
    currency: str
    timezone: str
    cdn_url: str = ""


SITES: Final[dict[str, Site]] = {
    site.code: site
    for site in (
        Site(
            "cz",
            "Rohlík.cz",
            "https://www.rohlik.cz",
            "CZK",
            "Europe/Prague",
            "https://cdn.rohlik.cz",
        ),
        Site(
            "de",
            "Knuspr.de",
            "https://www.knuspr.de",
            "EUR",
            "Europe/Berlin",
            "https://cdn.knuspr.de",
        ),
        Site(
            "at",
            "Gurkerl.at",
            "https://www.gurkerl.at",
            "EUR",
            "Europe/Vienna",
            "https://cdn.gurkerl.at",
        ),
        Site(
            "hu",
            "Kifli.hu",
            "https://www.kifli.hu",
            "HUF",
            "Europe/Budapest",
            "https://cdn.kifli.hu",
        ),
        Site(
            "ro",
            "Sezamo.ro",
            "https://www.sezamo.ro",
            "RON",
            "Europe/Bucharest",
            "https://cdn.sezamo.ro",
        ),
    )
}
"""Known shops, keyed by :attr:`Site.code`."""
