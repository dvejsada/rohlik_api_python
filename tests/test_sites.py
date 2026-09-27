"""Tests for the Rohlík Group shop presets."""

from zoneinfo import ZoneInfo

import rohlik_api
from rohlik_api import SITES, RohlikAPI, Site
from rohlik_api.endpoints import BASE_URL


def test_default_site_is_the_client_default():
    """Rohlík.cz's preset matches the URL the client uses when none is given."""
    assert SITES["cz"].base_url == BASE_URL


def test_sites_are_keyed_by_code():
    assert set(SITES) == {"cz", "de", "at", "hu", "ro"}
    for code, site in SITES.items():
        assert isinstance(site, Site)
        assert site.code == code


def test_site_fields_are_well_formed():
    for site in SITES.values():
        assert site.base_url.startswith("https://www.")
        assert not site.base_url.endswith("/")
        assert len(site.currency) == 3 and site.currency.isupper()
        ZoneInfo(site.timezone)  # raises if the zone name is wrong


def test_exported_from_package():
    assert "SITES" in rohlik_api.__all__
    assert "Site" in rohlik_api.__all__


async def test_client_targets_site_base_url():
    client = RohlikAPI("user@example.com", "secret", base_url=SITES["de"].base_url)
    try:
        assert client.base_url == "https://www.knuspr.de"
    finally:
        await client.close()
