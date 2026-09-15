"""Fixtures for the Baby Tracker tests."""

from __future__ import annotations

from collections.abc import Generator
from unittest.mock import AsyncMock, patch

import pytest
from pytest_homeassistant_custom_component.common import MockConfigEntry
from pytest_homeassistant_custom_component.test_util.aiohttp import AiohttpClientMocker

from homeassistant.const import CONF_TOKEN
from homeassistant.core import HomeAssistant

from custom_components.babytracker.api import BabyTrackerStatus
from custom_components.babytracker.const import API_BASE_URL, DOMAIN
from tests.const import COMMAND_RESPONSE, MOCK_TOKEN, STATUS_PAYLOAD


@pytest.fixture(autouse=True)
def auto_enable_custom_integrations(
    enable_custom_integrations: None,
) -> None:
    """Load `custom_components` in every test."""


@pytest.fixture
def mock_config_entry() -> MockConfigEntry:
    """Return a config entry holding a placeholder token."""
    return MockConfigEntry(
        domain=DOMAIN,
        title="Baby Tracker",
        data={CONF_TOKEN: MOCK_TOKEN},
        unique_id=MOCK_TOKEN,
    )


@pytest.fixture
def mock_status_api(aioclient_mock: AiohttpClientMocker) -> AiohttpClientMocker:
    """Answer `GET /status` with a placeholder payload."""
    aioclient_mock.get(f"{API_BASE_URL}/status", json=STATUS_PAYLOAD)
    return aioclient_mock


@pytest.fixture
def mock_client() -> Generator[AsyncMock]:
    """Replace the API client with a fake for every entry point that builds one."""
    client = AsyncMock()
    client.async_get_status.return_value = BabyTrackerStatus.from_dict(STATUS_PAYLOAD)
    client.async_command.return_value = COMMAND_RESPONSE
    with (
        patch("custom_components.babytracker.BabyTrackerClient", return_value=client),
        patch(
            "custom_components.babytracker.config_flow.BabyTrackerClient",
            return_value=client,
        ),
    ):
        yield client


@pytest.fixture
async def init_integration(
    hass: HomeAssistant, mock_config_entry: MockConfigEntry, mock_client: AsyncMock
) -> MockConfigEntry:
    """Set up the integration with a fake client."""
    mock_config_entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(mock_config_entry.entry_id)
    await hass.async_block_till_done()
    return mock_config_entry
