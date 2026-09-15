"""Tests for setup, unload and the coordinator."""

from __future__ import annotations

from datetime import timedelta
from unittest.mock import AsyncMock

from freezegun.api import FrozenDateTimeFactory
from pytest_homeassistant_custom_component.common import (
    MockConfigEntry,
    async_fire_time_changed,
)

from homeassistant.config_entries import ConfigEntryState
from homeassistant.core import HomeAssistant

from custom_components.little_log.api import (
    LittleLogAuthError,
    LittleLogConnectionError,
    LittleLogStatus,
)
from custom_components.little_log.const import DEFAULT_SCAN_INTERVAL
from tests.const import STATUS_PAYLOAD


async def test_setup_and_unload(
    hass: HomeAssistant, init_integration: MockConfigEntry
) -> None:
    """The entry loads, exposes the sensor and unloads again."""
    assert init_integration.state is ConfigEntryState.LOADED
    assert hass.states.get("sensor.baby_state") is not None

    assert await hass.config_entries.async_unload(init_integration.entry_id)
    await hass.async_block_till_done()
    assert init_integration.state is ConfigEntryState.NOT_LOADED


async def test_setup_retries_on_connection_error(
    hass: HomeAssistant, mock_config_entry: MockConfigEntry, mock_client: AsyncMock
) -> None:
    """An unreachable API leaves the entry in retry."""
    mock_client.async_get_status.side_effect = LittleLogConnectionError("down")
    mock_config_entry.add_to_hass(hass)

    await hass.config_entries.async_setup(mock_config_entry.entry_id)
    await hass.async_block_till_done()

    assert mock_config_entry.state is ConfigEntryState.SETUP_RETRY


async def test_sensor_attributes(
    hass: HomeAssistant, init_integration: MockConfigEntry
) -> None:
    """The sensor mirrors the status payload."""
    state = hass.states.get("sensor.baby_state")

    assert state.state == "asleep"
    assert state.attributes["since_utc"] == STATUS_PAYLOAD["since_utc"]
    assert state.attributes["elapsed_min"] == 42
    assert state.attributes["last_sleep"] == STATUS_PAYLOAD["last_sleep"]
    assert state.attributes["today"] == STATUS_PAYLOAD["today"]
    assert state.attributes["say"] == STATUS_PAYLOAD["say"]
    assert state.attributes["options"] == ["awake", "asleep"]


async def test_coordinator_polls_and_recovers(
    hass: HomeAssistant,
    init_integration: MockConfigEntry,
    mock_client: AsyncMock,
    freezer: FrozenDateTimeFactory,
) -> None:
    """Polling picks up new data, and a failed poll marks the sensor unavailable."""
    mock_client.async_get_status.return_value = LittleLogStatus.from_dict(
        {**STATUS_PAYLOAD, "state": "awake", "elapsed_min": 5}
    )
    freezer.tick(DEFAULT_SCAN_INTERVAL + timedelta(seconds=1))
    async_fire_time_changed(hass)
    await hass.async_block_till_done()

    state = hass.states.get("sensor.baby_state")
    assert state.state == "awake"
    assert state.attributes["elapsed_min"] == 5

    mock_client.async_get_status.side_effect = LittleLogConnectionError("down")
    freezer.tick(DEFAULT_SCAN_INTERVAL + timedelta(seconds=1))
    async_fire_time_changed(hass)
    await hass.async_block_till_done()

    assert hass.states.get("sensor.baby_state").state == "unavailable"


async def test_coordinator_auth_error_starts_reauth(
    hass: HomeAssistant, init_integration: MockConfigEntry, mock_client: AsyncMock
) -> None:
    """A revoked token triggers the reauth flow instead of endless retries."""
    mock_client.async_get_status.side_effect = LittleLogAuthError("revoked")

    await init_integration.runtime_data.async_refresh()
    await hass.async_block_till_done()

    flows = [
        flow
        for flow in hass.config_entries.flow.async_progress()
        if flow["context"].get("source") == "reauth"
    ]
    assert len(flows) == 1
