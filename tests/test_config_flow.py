"""Tests for the Little Log config flow."""

from __future__ import annotations

from unittest.mock import AsyncMock

import pytest
from pytest_homeassistant_custom_component.common import MockConfigEntry

from homeassistant.config_entries import SOURCE_USER
from homeassistant.const import CONF_TOKEN
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResultType

from custom_components.little_log.api import (
    LittleLogAuthError,
    LittleLogConnectionError,
)
from custom_components.little_log.const import DOMAIN
from tests.const import MOCK_TOKEN


async def test_user_flow_success(hass: HomeAssistant, mock_client: AsyncMock) -> None:
    """A valid token creates an entry."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": SOURCE_USER}
    )
    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "user"

    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], {CONF_TOKEN: MOCK_TOKEN}
    )
    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["title"] == "Little Log"
    assert result["data"] == {CONF_TOKEN: MOCK_TOKEN}
    assert result["result"].unique_id == MOCK_TOKEN
    # Once to validate the token, once for the coordinator's first refresh.
    assert mock_client.async_get_status.await_count >= 1


@pytest.mark.parametrize(
    ("error", "expected"),
    [
        (LittleLogAuthError("nope"), "invalid_auth"),
        (LittleLogConnectionError("down"), "cannot_connect"),
        (RuntimeError("boom"), "unknown"),
    ],
)
async def test_user_flow_errors_then_recovers(
    hass: HomeAssistant,
    mock_client: AsyncMock,
    error: Exception,
    expected: str,
) -> None:
    """A failing validation shows an error and the form can be retried."""
    mock_client.async_get_status.side_effect = error

    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": SOURCE_USER}
    )
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], {CONF_TOKEN: MOCK_TOKEN}
    )
    assert result["type"] is FlowResultType.FORM
    assert result["errors"] == {"base": expected}

    mock_client.async_get_status.side_effect = None
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], {CONF_TOKEN: MOCK_TOKEN}
    )
    assert result["type"] is FlowResultType.CREATE_ENTRY


async def test_user_flow_duplicate_token(
    hass: HomeAssistant, mock_client: AsyncMock, mock_config_entry: MockConfigEntry
) -> None:
    """The same token cannot be added twice."""
    mock_config_entry.add_to_hass(hass)

    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": SOURCE_USER}
    )
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], {CONF_TOKEN: MOCK_TOKEN}
    )
    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "already_configured"


async def test_reauth_flow(
    hass: HomeAssistant,
    mock_client: AsyncMock,
    init_integration: MockConfigEntry,
) -> None:
    """Reauth replaces the stored token."""
    new_token = "bt_newtoken00000000000000000000000"
    result = await init_integration.start_reauth_flow(hass)
    assert result["step_id"] == "reauth_confirm"

    mock_client.async_get_status.side_effect = LittleLogAuthError("nope")
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], {CONF_TOKEN: new_token}
    )
    assert result["errors"] == {"base": "invalid_auth"}

    mock_client.async_get_status.side_effect = None
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], {CONF_TOKEN: new_token}
    )
    await hass.async_block_till_done()
    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "reauth_successful"
    assert init_integration.data[CONF_TOKEN] == new_token
