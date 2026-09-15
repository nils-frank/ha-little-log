"""The Baby Tracker integration."""

from __future__ import annotations

from homeassistant.const import CONF_TOKEN, Platform
from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .api import BabyTrackerClient
from .coordinator import BabyTrackerConfigEntry, BabyTrackerCoordinator
from .services import async_setup_services

PLATFORMS: list[Platform] = [Platform.SENSOR]


async def async_setup_entry(hass: HomeAssistant, entry: BabyTrackerConfigEntry) -> bool:
    """Set up Baby Tracker from a config entry."""
    client = BabyTrackerClient(async_get_clientsession(hass), entry.data[CONF_TOKEN])
    coordinator = BabyTrackerCoordinator(hass, entry, client)
    await coordinator.async_config_entry_first_refresh()

    # The coordinator (which owns the client) lives on the entry itself rather than in
    # hass.data, per current config entry runtime-data conventions.
    entry.runtime_data = coordinator

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    async_setup_services(hass)
    return True


async def async_unload_entry(
    hass: HomeAssistant, entry: BabyTrackerConfigEntry
) -> bool:
    """Unload a config entry."""
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
