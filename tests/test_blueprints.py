"""Validate the shipped blueprints against Home Assistant's own schema."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest

from homeassistant.components.automation.config import (
    AUTOMATION_BLUEPRINT_SCHEMA,
    async_validate_config_item,
)
from homeassistant.components.blueprint.models import Blueprint, BlueprintInputs
from homeassistant.core import HomeAssistant
from homeassistant.util.yaml import parse_yaml

BLUEPRINT_DIR = (
    Path(__file__).parent.parent / "blueprints" / "automation" / "little_log"
)

# Inputs a user would pick in the UI. Entity and device ids need not exist for
# schema validation; what matters is that every `!input` resolves and the result
# is a config Home Assistant would accept.
BLUEPRINT_INPUTS: dict[str, dict[str, Any]] = {
    "live_activity.yaml": {
        "baby_sensor": "sensor.baby_state",
        "mobile_device": "0123456789abcdef0123456789abcdef",
    },
    "button_sleep_toggle.yaml": {
        "button_event": "event.nursery_button",
    },
}


def _blueprint_files() -> list[str]:
    return sorted(path.name for path in BLUEPRINT_DIR.glob("*.yaml"))


def test_every_blueprint_is_covered() -> None:
    """Guard against a new blueprint being added without a validation case."""
    assert set(_blueprint_files()) == set(BLUEPRINT_INPUTS)


@pytest.mark.parametrize("filename", _blueprint_files())
def test_blueprint_metadata(filename: str) -> None:
    """Each blueprint parses and carries the metadata needed to be importable."""
    blueprint = Blueprint(
        parse_yaml((BLUEPRINT_DIR / filename).read_text()),
        expected_domain="automation",
        schema=AUTOMATION_BLUEPRINT_SCHEMA,
    )

    # Catches an unresolved !input and a min_version newer than the test core.
    assert blueprint.validate() is None
    assert blueprint.name
    assert blueprint.metadata["description"]
    # Without source_url a blueprint cannot be re-imported to pick up fixes.
    assert blueprint.metadata["source_url"].endswith(filename)
    assert blueprint.metadata["homeassistant"]["min_version"]


@pytest.mark.parametrize("filename", _blueprint_files())
async def test_blueprint_substitutes_into_valid_automation(
    hass: HomeAssistant, filename: str
) -> None:
    """Filling in the inputs produces an automation config HA accepts."""
    blueprint = Blueprint(
        parse_yaml((BLUEPRINT_DIR / filename).read_text()),
        expected_domain="automation",
        schema=AUTOMATION_BLUEPRINT_SCHEMA,
    )
    inputs = BlueprintInputs(
        blueprint, {"use_blueprint": {"input": BLUEPRINT_INPUTS[filename]}}
    )
    # Raises if a required input is missing or an unknown one is supplied.
    inputs.validate()

    validated = await async_validate_config_item(
        hass, f"automation {filename}", inputs.async_substitute()
    )

    assert validated is not None
