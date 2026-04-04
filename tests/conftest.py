"""Pytest fixtures for Cosmos tests"""

import sys
from pathlib import Path
from unittest.mock import MagicMock

import pytest
from aioresponses import aioresponses

# Add the project root to the path so we can import custom_components
sys.path.insert(0, str(Path(__file__).parent.parent))

# Mock homeassistant module before any imports
# This allows tests to run without the full HA package
ha_mock = MagicMock()
ha_mock.config_entries = MagicMock()
ha_mock.core = MagicMock()
ha_mock.exceptions = MagicMock()
ha_mock.helpers = MagicMock()
sys.modules["homeassistant"] = ha_mock
sys.modules["homeassistant.config_entries"] = ha_mock.config_entries
sys.modules["homeassistant.core"] = ha_mock.core
sys.modules["homeassistant.exceptions"] = ha_mock.exceptions
sys.modules["homeassistant.helpers"] = ha_mock.helpers
sys.modules["homeassistant.helpers.config_validation"] = MagicMock()


class AioresponsesCookiejar(aioresponses):
    """Extended aioresponses that updates session cookie jar from Set-Cookie headers."""

    async def _request_mock(self, orig_self, method, url, *args, **kwargs):
        """Override _request_mock to update cookie jar from response cookies."""
        # Call parent implementation
        response = await super()._request_mock(orig_self, method, url, *args, **kwargs)

        # Update cookie jar from response cookies
        # response.cookies is already parsed from Set-Cookie header by parent
        if response.cookies:
            orig_self.cookie_jar.update_cookies(response.cookies, response.url)

        return response


@pytest.fixture
def mock_api():
    """Mock aiohttp requests with cookie jar support."""
    with AioresponsesCookiejar() as m:
        yield m


@pytest.fixture
def config():
    """Sample config fixture"""
    from custom_components.cosmos.models import Config

    return Config(username="test_user", password="test_pass", mandant="test_mandant")


@pytest.fixture
def mandant_data():
    """Sample mandant data fixture"""
    from custom_components.cosmos.models import MandantData

    return MandantData(login_token="test_token_123", member_nr="12345")


@pytest.fixture
def sample_course():
    """Sample course fixture"""
    from custom_components.cosmos.models import Course

    return Course(
        nr=1,
        course_name="Yoga",
        begin="2024-01-15T18:00:00",
        end="2024-01-15T19:00:00",
        booked=0,
        online_book_max=10,
        course_nr=101,
        course_period_begin="2024-01-01",
        course_period_end="2024-12-31",
        course_price_single="10.00",
        book_type="online",
        waitlist=0,
        max_anz=20,
        akt_anz=15,
    )
