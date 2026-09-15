"""Tests for the Little Log services."""

from __future__ import annotations

from unittest.mock import AsyncMock

import pytest
from pytest_homeassistant_custom_component.common import MockConfigEntry
import voluptuous as vol

from homeassistant.const import CONF_TOKEN
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError, ServiceValidationError
from homeassistant.setup import async_setup_component

from custom_components.little_log.api import LittleLogConnectionError
from custom_components.little_log.const import DOMAIN
from custom_components.little_log.services import SERVICES
from tests.const import COMMAND_RESPONSE


async def test_all_services_registered(
    hass: HomeAssistant, init_integration: MockConfigEntry
) -> None:
    """Every documented endpoint has a service."""
    for service in SERVICES:
        assert hass.services.has_service(DOMAIN, service.name)


async def test_simple_command_returns_speech(
    hass: HomeAssistant, init_integration: MockConfigEntry, mock_client: AsyncMock
) -> None:
    """A plain command posts an empty body and returns the API response."""
    response = await hass.services.async_call(
        DOMAIN, "sleep_toggle", {}, blocking=True, return_response=True
    )

    mock_client.async_command.assert_awaited_once_with("/sleep/toggle", None)
    assert response == COMMAND_RESPONSE
    assert response["speech_de"] == "Platzhalter."


async def test_minutes_ago_is_sent(
    hass: HomeAssistant, init_integration: MockConfigEntry, mock_client: AsyncMock
) -> None:
    """`minutes_ago` is passed through to the API."""
    await hass.services.async_call(
        DOMAIN, "sleep_start", {"minutes_ago": 15}, blocking=True
    )

    mock_client.async_command.assert_awaited_once_with(
        "/sleep/start", {"minutes_ago": 15}
    )


async def test_at_utc_is_normalised(
    hass: HomeAssistant, init_integration: MockConfigEntry, mock_client: AsyncMock
) -> None:
    """A timestamp is converted to UTC ISO 8601 before being sent."""
    await hass.services.async_call(
        DOMAIN, "bottle", {"at_utc": "2026-01-01T07:30:00+02:00"}, blocking=True
    )

    mock_client.async_command.assert_awaited_once_with(
        "/bottle", {"at_utc": "2026-01-01T05:30:00+00:00"}
    )


@pytest.mark.parametrize(
    ("service", "data", "expected_path", "expected_body"),
    [
        ("cue", {"subtype": "yawn"}, "/cue", {"subtype": "yawn"}),
        ("diaper", {"kind": "wet"}, "/diaper", {"kind": "wet"}),
        (
            "diaper",
            {"pee_level": "light", "poop_level": 2},
            "/diaper",
            {"pee_level": "light", "poop_level": 2},
        ),
        ("diaper", {}, "/diaper", None),
        ("nursing", {}, "/nursing", {"side": "next"}),
        ("nursing", {"side": "L"}, "/nursing", {"side": "L"}),
        ("nursing", {"side": "left"}, "/nursing", {"side": "L"}),
        ("nursing", {"side": "right"}, "/nursing", {"side": "R"}),
        ("undo", {}, "/undo", None),
    ],
)
async def test_service_bodies(
    hass: HomeAssistant,
    init_integration: MockConfigEntry,
    mock_client: AsyncMock,
    service: str,
    data: dict,
    expected_path: str,
    expected_body: dict | None,
) -> None:
    """Each service maps onto its documented endpoint and body."""
    await hass.services.async_call(DOMAIN, service, data, blocking=True)

    mock_client.async_command.assert_awaited_once_with(expected_path, expected_body)


@pytest.mark.parametrize(
    ("service", "data"),
    [
        ("sleep_start", {"minutes_ago": 721}),
        ("sleep_start", {"minutes_ago": -1}),
        ("sleep_start", {"minutes_ago": 5, "at_utc": "2026-01-01T00:00:00+00:00"}),
        ("diaper", {"kind": "soaked"}),
        ("diaper", {"kind": "wet", "pee_level": "light", "poop_level": "light"}),
        ("diaper", {"pee_level": "light"}),
        ("nursing", {"side": "middle"}),
    ],
)
async def test_invalid_input_rejected(
    hass: HomeAssistant,
    init_integration: MockConfigEntry,
    mock_client: AsyncMock,
    service: str,
    data: dict,
) -> None:
    """Bad input is rejected before a request is made."""
    with pytest.raises(vol.Invalid):
        await hass.services.async_call(DOMAIN, service, data, blocking=True)

    mock_client.async_command.assert_not_awaited()


async def test_api_error_surfaces(
    hass: HomeAssistant, init_integration: MockConfigEntry, mock_client: AsyncMock
) -> None:
    """An API failure becomes a HomeAssistantError."""
    mock_client.async_command.side_effect = LittleLogConnectionError("down")

    with pytest.raises(HomeAssistantError, match="down"):
        await hass.services.async_call(DOMAIN, "undo", {}, blocking=True)


async def test_config_entry_id_selects_the_entry(
    hass: HomeAssistant, init_integration: MockConfigEntry, mock_client: AsyncMock
) -> None:
    """With two entries loaded the call must name one."""
    second = MockConfigEntry(
        domain=DOMAIN,
        title="Little Log 2",
        data={CONF_TOKEN: "bt_second00000000000000000000000"},
        unique_id="bt_second00000000000000000000000",
    )
    second.add_to_hass(hass)
    assert await hass.config_entries.async_setup(second.entry_id)
    await hass.async_block_till_done()

    with pytest.raises(ServiceValidationError):
        await hass.services.async_call(DOMAIN, "undo", {}, blocking=True)

    await hass.services.async_call(
        DOMAIN,
        "undo",
        {"config_entry_id": second.entry_id},
        blocking=True,
    )
    mock_client.async_command.assert_awaited_once_with("/undo", None)


async def test_services_exist_without_a_loaded_entry(hass: HomeAssistant) -> None:
    """Services are registered up front and explain themselves when unusable."""
    assert await async_setup_component(hass, DOMAIN, {})

    assert hass.services.has_service(DOMAIN, "sleep_toggle")
    with pytest.raises(ServiceValidationError):
        await hass.services.async_call(DOMAIN, "sleep_toggle", {}, blocking=True)
