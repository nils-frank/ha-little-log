"""Data update coordinator for the Baby Tracker integration."""

from __future__ import annotations

import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryAuthFailed
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .api import (
    BabyTrackerAuthError,
    BabyTrackerClient,
    BabyTrackerConnectionError,
    BabyTrackerStatus,
)
from .const import DEFAULT_SCAN_INTERVAL, DOMAIN

_LOGGER = logging.getLogger(__name__)

type BabyTrackerConfigEntry = ConfigEntry[BabyTrackerCoordinator]


class BabyTrackerCoordinator(DataUpdateCoordinator[BabyTrackerStatus]):
    """Poll `GET /status` on the vendor-recommended interval."""

    config_entry: BabyTrackerConfigEntry

    def __init__(
        self,
        hass: HomeAssistant,
        config_entry: BabyTrackerConfigEntry,
        client: BabyTrackerClient,
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

    async def _async_update_data(self) -> BabyTrackerStatus:
        """Fetch the latest status."""
        try:
            return await self.client.async_get_status()
        except BabyTrackerAuthError as err:
            # Triggers the reauth flow instead of retrying a token that will
            # keep failing.
            raise ConfigEntryAuthFailed(str(err)) from err
        except BabyTrackerConnectionError as err:
            raise UpdateFailed(str(err)) from err
