"""Tests for the Little Log API client."""

from __future__ import annotations

import pytest
from pytest_homeassistant_custom_component.test_util.aiohttp import AiohttpClientMocker

from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from custom_components.little_log.api import (
    LittleLogAuthError,
    LittleLogClient,
    LittleLogConnectionError,
    LittleLogStatus,
)
from custom_components.little_log.const import API_BASE_URL
from tests.const import COMMAND_RESPONSE, MOCK_TOKEN, STATUS_PAYLOAD


def _client(hass: HomeAssistant) -> LittleLogClient:
    return LittleLogClient(async_get_clientsession(hass), MOCK_TOKEN)


async def test_get_status_parses_payload(
    hass: HomeAssistant, mock_status_api: AiohttpClientMocker
) -> None:
    """A documented payload maps onto the status model, auth header included."""
    status = await _client(hass).async_get_status()

    assert status.state == "asleep"
    assert status.elapsed_min == 42
    assert status.say["forecast"] == "Placeholder forecast."
    assert status.raw == STATUS_PAYLOAD
    headers = mock_status_api.mock_calls[0][3]
    assert headers["Authorization"] == f"Bearer {MOCK_TOKEN}"


async def test_command_sends_body(
    hass: HomeAssistant, aioclient_mock: AiohttpClientMocker
) -> None:
    """A command posts its body and returns the parsed response."""
    aioclient_mock.post(f"{API_BASE_URL}/diaper", json=COMMAND_RESPONSE)

    response = await _client(hass).async_command("/diaper", {"kind": "wet"})

    assert response == COMMAND_RESPONSE
    assert aioclient_mock.mock_calls[0][2] == {"kind": "wet"}


@pytest.mark.parametrize("status", [401, 403])
async def test_auth_error(
    hass: HomeAssistant, aioclient_mock: AiohttpClientMocker, status: int
) -> None:
    """A rejected token raises the auth error."""
    aioclient_mock.get(f"{API_BASE_URL}/status", status=status)

    with pytest.raises(LittleLogAuthError):
        await _client(hass).async_get_status()


async def test_server_error(
    hass: HomeAssistant, aioclient_mock: AiohttpClientMocker
) -> None:
    """Any other non-2xx surfaces as a connection error."""
    aioclient_mock.get(f"{API_BASE_URL}/status", status=500)

    with pytest.raises(LittleLogConnectionError):
        await _client(hass).async_get_status()


async def test_redirect_is_not_followed(
    hass: HomeAssistant, aioclient_mock: AiohttpClientMocker
) -> None:
    """A cross-host redirect fails loudly instead of silently dropping the token."""
    aioclient_mock.get(
        f"{API_BASE_URL}/status",
        status=301,
        headers={"Location": "https://example.invalid/status"},
    )

    with pytest.raises(LittleLogConnectionError, match="redirect"):
        await _client(hass).async_get_status()


async def test_non_json_payload(
    hass: HomeAssistant, aioclient_mock: AiohttpClientMocker
) -> None:
    """A non-JSON body is reported rather than crashing the coordinator."""
    aioclient_mock.get(f"{API_BASE_URL}/status", text="not json")

    with pytest.raises(LittleLogConnectionError):
        await _client(hass).async_get_status()


def test_status_tolerates_missing_fields() -> None:
    """Undocumented or missing fields do not break parsing."""
    status = LittleLogStatus.from_dict(
        {"state": "awake", "elapsed_min": "7", "today": None}
    )

    assert status.elapsed_min == 7
    assert status.since_utc is None
    assert status.today == {}

    assert LittleLogStatus.from_dict({"elapsed_min": "n/a"}).elapsed_min is None
