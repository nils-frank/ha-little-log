"""Sensor platform for the Baby Tracker integration."""

from __future__ import annotations

from typing import Any

from homeassistant.components.sensor import (
    ENTITY_ID_FORMAT,
    SensorDeviceClass,
    SensorEntity,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity import async_generate_entity_id
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .coordinator import BabyTrackerConfigEntry, BabyTrackerCoordinator

# The API documents exactly these two states.
STATE_OPTIONS = ["awake", "asleep"]


async def async_setup_entry(
    hass: HomeAssistant,
    entry: BabyTrackerConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up the Baby Tracker sensor."""
    async_add_entities([BabyStateSensor(hass, entry.runtime_data)])


class BabyStateSensor(CoordinatorEntity[BabyTrackerCoordinator], SensorEntity):
    """Current awake/asleep state, with the rest of `GET /status` as attributes."""

    _attr_has_entity_name = True
    _attr_translation_key = "baby_state"
    _attr_device_class = SensorDeviceClass.ENUM
    _attr_options = STATE_OPTIONS

    def __init__(
        self, hass: HomeAssistant, coordinator: BabyTrackerCoordinator
    ) -> None:
        """Initialise the sensor."""
        super().__init__(coordinator)
        entry_id = coordinator.config_entry.entry_id
        self._attr_unique_id = f"{entry_id}_baby_state"
        # Pin the default object id so the documented `sensor.baby_state` is what a
        # fresh install gets; a second entry falls back to `_2` as usual.
        self.entity_id = async_generate_entity_id(
            ENTITY_ID_FORMAT, "baby_state", hass=hass
        )
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, entry_id)},
            name="Baby Tracker",
            manufacturer="Lukas Reindl",
            configuration_url="https://lukas-reindl.de/babytracker/",
        )

    @property
    def native_value(self) -> str | None:
        """Return `awake` or `asleep`."""
        state = self.coordinator.data.state
        # Guard against an undocumented third state breaking the enum device class.
        return state if state in STATE_OPTIONS else None

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return the remaining status fields."""
        data = self.coordinator.data
        return {
            "since_utc": data.since_utc,
            "elapsed_min": data.elapsed_min,
            "last_sleep": data.last_sleep,
            "today": data.today,
            "say": data.say,
        }
