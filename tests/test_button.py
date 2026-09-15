"""Tests for the Little Log buttons."""

from __future__ import annotations

from unittest.mock import AsyncMock

import pytest
from pytest_homeassistant_custom_component.common import MockConfigEntry

from homeassistant.components.button import DOMAIN as BUTTON_DOMAIN, SERVICE_PRESS
from homeassistant.const import ATTR_ENTITY_ID
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers import entity_registry as er

from custom_components.little_log.api import LittleLogConnectionError
from custom_components.little_log.button import BUTTONS


async def _press(hass: HomeAssistant, entity_id: str) -> None:
    await hass.services.async_call(
        BUTTON_DOMAIN, SERVICE_PRESS, {ATTR_ENTITY_ID: entity_id}, blocking=True
    )


async def test_all_buttons_created(
    hass: HomeAssistant,
    init_integration: MockConfigEntry,
    entity_registry: er.EntityRegistry,
) -> None:
    """Every described button becomes an entity on the device."""
    entries = [
        entry
        for entry in er.async_entries_for_config_entry(
            entity_registry, init_integration.entry_id
        )
        if entry.domain == BUTTON_DOMAIN
    ]

    assert len(entries) == len(BUTTONS)
    assert {entry.unique_id for entry in entries} == {
        f"{init_integration.entry_id}_{description.key}" for description in BUTTONS
    }
    assert all(entry.device_id is not None for entry in entries)


@pytest.mark.parametrize(
    ("entity_id", "expected_path", "expected_body"),
    [
        ("button.little_log_toggle_sleep", "/sleep/toggle", None),
        ("button.little_log_start_sleep", "/sleep/start", None),
        ("button.little_log_stop_sleep", "/sleep/stop", None),
        ("button.little_log_start_crying", "/cry/start", None),
        ("button.little_log_stop_crying", "/cry/stop", None),
        ("button.little_log_bottle", "/bottle", None),
        ("button.little_log_nursing", "/nursing", {"side": "next"}),
        ("button.little_log_diaper", "/diaper", None),
        ("button.little_log_yawn", "/cue", {"subtype": "yawn"}),
        ("button.little_log_undo", "/undo", None),
    ],
)
async def test_press_sends_command(
    hass: HomeAssistant,
    init_integration: MockConfigEntry,
    mock_client: AsyncMock,
    entity_id: str,
    expected_path: str,
    expected_body: dict | None,
) -> None:
    """Each button posts to its endpoint with the documented body."""
    assert hass.states.get(entity_id) is not None

    await _press(hass, entity_id)

    mock_client.async_command.assert_awaited_once_with(expected_path, expected_body)


async def test_press_refreshes_the_sensor(
    hass: HomeAssistant, init_integration: MockConfigEntry, mock_client: AsyncMock
) -> None:
    """A press updates the sensor without waiting out the poll interval."""
    before = mock_client.async_get_status.await_count

    await _press(hass, "button.little_log_bottle")
    await hass.async_block_till_done()

    assert mock_client.async_get_status.await_count > before


async def test_press_surfaces_api_errors(
    hass: HomeAssistant, init_integration: MockConfigEntry, mock_client: AsyncMock
) -> None:
    """An API failure becomes a HomeAssistantError rather than a silent no-op."""
    mock_client.async_command.side_effect = LittleLogConnectionError("down")

    with pytest.raises(HomeAssistantError, match="down"):
        await _press(hass, "button.little_log_undo")
