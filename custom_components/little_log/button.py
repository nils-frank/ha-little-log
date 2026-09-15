"""Button platform for the Little Log integration."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any

from homeassistant.components.button import ButtonEntity, ButtonEntityDescription
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from .coordinator import LittleLogConfigEntry, LittleLogCoordinator
from .entity import build_device_info

# Each press is a single write with no per-entity polling.
PARALLEL_UPDATES = 0


@dataclass(frozen=True, kw_only=True)
class LittleLogButtonDescription(ButtonEntityDescription):
    """Describes a button and the API call behind it."""

    path: str
    body: Mapping[str, Any] | None = None


# Buttons cover the commands that need no arguments. Anything that takes a value
# (backdating with `minutes_ago`, a specific diaper kind, a chosen nursing side) stays
# an action, since a button entity cannot carry parameters or return `speech_de`.
BUTTONS: tuple[LittleLogButtonDescription, ...] = (
    LittleLogButtonDescription(
        key="sleep_toggle", translation_key="sleep_toggle", path="/sleep/toggle"
    ),
    LittleLogButtonDescription(
        key="sleep_start", translation_key="sleep_start", path="/sleep/start"
    ),
    LittleLogButtonDescription(
        key="sleep_stop", translation_key="sleep_stop", path="/sleep/stop"
    ),
    LittleLogButtonDescription(
        key="cry_start", translation_key="cry_start", path="/cry/start"
    ),
    LittleLogButtonDescription(
        key="cry_stop", translation_key="cry_stop", path="/cry/stop"
    ),
    LittleLogButtonDescription(key="bottle", translation_key="bottle", path="/bottle"),
    LittleLogButtonDescription(
        key="nursing",
        translation_key="nursing",
        path="/nursing",
        # "next" alternates from the last recorded side, which is the API's own default.
        body={"side": "next"},
    ),
    LittleLogButtonDescription(
        key="diaper",
        translation_key="diaper",
        path="/diaper",
        # No body: the API defaults to medium for both pee and poop.
        body=None,
    ),
    LittleLogButtonDescription(
        key="cue_yawn",
        translation_key="cue_yawn",
        path="/cue",
        body={"subtype": "yawn"},
    ),
    LittleLogButtonDescription(key="undo", translation_key="undo", path="/undo"),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: LittleLogConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up the Little Log buttons."""
    coordinator = entry.runtime_data
    async_add_entities(
        LittleLogButton(coordinator, description) for description in BUTTONS
    )


class LittleLogButton(ButtonEntity):
    """A one-press Little Log command."""

    _attr_has_entity_name = True
    entity_description: LittleLogButtonDescription

    def __init__(
        self,
        coordinator: LittleLogCoordinator,
        description: LittleLogButtonDescription,
    ) -> None:
        """Initialise the button."""
        self.entity_description = description
        self._coordinator = coordinator
        entry_id = coordinator.config_entry.entry_id
        self._attr_unique_id = f"{entry_id}_{description.key}"
        self._attr_device_info = build_device_info(coordinator)

    async def async_press(self) -> None:
        """Send the command."""
        body = dict(self.entity_description.body or {}) or None
        await self._coordinator.async_send_command(self.entity_description.path, body)
