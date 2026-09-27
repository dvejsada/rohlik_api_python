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
    """

    code: str
    name: str
    base_url: str
    currency: str
    timezone: str


SITES: Final[dict[str, Site]] = {
    site.code: site
    for site in (
        Site("cz", "Rohlík.cz", "https://www.rohlik.cz", "CZK", "Europe/Prague"),
        Site("de", "Knuspr.de", "https://www.knuspr.de", "EUR", "Europe/Berlin"),
        Site("at", "Gurkerl.at", "https://www.gurkerl.at", "EUR", "Europe/Vienna"),
        Site("hu", "Kifli.hu", "https://www.kifli.hu", "HUF", "Europe/Budapest"),
        Site("ro", "Sezamo.ro", "https://www.sezamo.ro", "RON", "Europe/Bucharest"),
    )
}
"""Known shops, keyed by :attr:`Site.code`."""
