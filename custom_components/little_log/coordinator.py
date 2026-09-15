"""Data update coordinator for the Little Log integration."""

from __future__ import annotations

import logging
from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryAuthFailed, HomeAssistantError
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .api import (
    LittleLogAuthError,
    LittleLogClient,
    LittleLogConnectionError,
    LittleLogError,
    LittleLogStatus,
)
from .const import DEFAULT_SCAN_INTERVAL, DOMAIN

_LOGGER = logging.getLogger(__name__)

type LittleLogConfigEntry = ConfigEntry[LittleLogCoordinator]


class LittleLogCoordinator(DataUpdateCoordinator[LittleLogStatus]):
    """Poll `GET /status` on the vendor-recommended interval."""

    config_entry: LittleLogConfigEntry

    def __init__(
        self,
        hass: HomeAssistant,
        config_entry: LittleLogConfigEntry,
        client: LittleLogClient,
    ) -> None:
        """Initialise the coordinator."""
        super().__init__(
            hass,
            _LOGGER,
            config_entry=config_entry,
            name=DOMAIN,
            update_interval=DEFAULT_SCAN_INTERVAL,
        )
        self.client = client

    async def _async_update_data(self) -> LittleLogStatus:
        """Fetch the latest status."""
        try:
            return await self.client.async_get_status()
        except LittleLogAuthError as err:
            # Triggers the reauth flow instead of retrying a token that will
            # keep failing.
            raise ConfigEntryAuthFailed(str(err)) from err
        except LittleLogConnectionError as err:
            raise UpdateFailed(str(err)) from err

    async def async_send_command(
        self, path: str, body: dict[str, Any] | None = None
    ) -> dict[str, Any]:
        """Run a write command, then refresh so the sensor reflects it.

        Shared by the actions and the button entities so both report failures the
        same way and neither has to wait out the poll interval to show the result.
        """
        try:
            response = await self.client.async_command(path, body or None)
        except LittleLogError as err:
            raise HomeAssistantError(str(err)) from err

        await self.async_request_refresh()
        return response
