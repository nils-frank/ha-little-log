"""Shared entity plumbing for the Little Log integration."""

from __future__ import annotations

from homeassistant.helpers.device_registry import DeviceInfo

from .const import DOMAIN
from .coordinator import LittleLogCoordinator


def build_device_info(coordinator: LittleLogCoordinator) -> DeviceInfo:
    """Return the device every Little Log entity belongs to.

    Both platforms build the identical device, so whichever sets up first names it.
    Leaving the name off one of them would strip the device prefix from that
    platform's generated entity ids, depending on setup order.
    """
    return DeviceInfo(
        identifiers={(DOMAIN, coordinator.config_entry.entry_id)},
        name="Little Log",
        manufacturer="Lukas Reindl",
        configuration_url="https://little-log.de/",
    )
