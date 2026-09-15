"""Services for the Baby Tracker integration."""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from datetime import datetime
from typing import Any

import voluptuous as vol

from homeassistant.config_entries import ConfigEntryState
from homeassistant.core import (
    HomeAssistant,
    ServiceCall,
    ServiceResponse,
    SupportsResponse,
    callback,
)
from homeassistant.exceptions import HomeAssistantError, ServiceValidationError
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers.selector import ConfigEntrySelector
from homeassistant.util import dt as dt_util

from .api import BabyTrackerError
from .const import (
    ATTR_AT_UTC,
    ATTR_KIND,
    ATTR_MINUTES_AGO,
    ATTR_PEE_LEVEL,
    ATTR_POOP_LEVEL,
    ATTR_SIDE,
    ATTR_SUBTYPE,
    DIAPER_KINDS,
    DIAPER_LEVELS,
    DOMAIN,
    MAX_MINUTES_AGO,
    MIN_MINUTES_AGO,
    NURSING_SIDE_MAP,
    NURSING_SIDES,
    SERVICE_BOTTLE,
    SERVICE_CRY_START,
    SERVICE_CRY_STOP,
    SERVICE_CUE,
    SERVICE_DIAPER,
    SERVICE_NURSING,
    SERVICE_SLEEP_START,
    SERVICE_SLEEP_STOP,
    SERVICE_SLEEP_TOGGLE,
    SERVICE_UNDO,
)

ATTR_CONFIG_ENTRY_ID = "config_entry_id"

_ENTRY_SCHEMA = {
    vol.Optional(ATTR_CONFIG_ENTRY_ID): ConfigEntrySelector({"integration": DOMAIN}),
}

# `minutes_ago` and `at_utc` are two ways of saying the same thing, so the schema
# rejects both at once instead of letting the API pick a winner.
_TIMING_SCHEMA = {
    vol.Exclusive(ATTR_MINUTES_AGO, "timing"): vol.All(
        vol.Coerce(int), vol.Range(min=MIN_MINUTES_AGO, max=MAX_MINUTES_AGO)
    ),
    vol.Exclusive(ATTR_AT_UTC, "timing"): cv.datetime,
}

TIMED_SERVICE_SCHEMA = vol.Schema({**_ENTRY_SCHEMA, **_TIMING_SCHEMA})
PLAIN_SERVICE_SCHEMA = vol.Schema(_ENTRY_SCHEMA)

CUE_SERVICE_SCHEMA = vol.Schema(
    {**_ENTRY_SCHEMA, **_TIMING_SCHEMA, vol.Required(ATTR_SUBTYPE): cv.string}
)

DIAPER_SERVICE_SCHEMA = vol.Schema(
    {
        **_ENTRY_SCHEMA,
        **_TIMING_SCHEMA,
        # `kind` is a shorthand for a pee/poop level pair, so the API takes one form or
        # the other, never both.
        vol.Exclusive(ATTR_KIND, "diaper"): vol.In(DIAPER_KINDS),
        vol.Inclusive(ATTR_PEE_LEVEL, "diaper_levels"): vol.Any(
            vol.All(vol.Coerce(int), vol.Range(min=0, max=3)), vol.In(DIAPER_LEVELS)
        ),
        vol.Inclusive(ATTR_POOP_LEVEL, "diaper_levels"): vol.Any(
            vol.All(vol.Coerce(int), vol.Range(min=0, max=3)), vol.In(DIAPER_LEVELS)
        ),
    }
)


def _no_kind_with_levels(data: dict[str, Any]) -> dict[str, Any]:
    """Reject a diaper call that mixes the two ways of describing the same change."""
    if ATTR_KIND in data and (ATTR_PEE_LEVEL in data or ATTR_POOP_LEVEL in data):
        raise vol.Invalid(
            f"{ATTR_KIND} cannot be combined with {ATTR_PEE_LEVEL}/{ATTR_POOP_LEVEL}"
        )
    return data


DIAPER_SERVICE_SCHEMA = vol.All(DIAPER_SERVICE_SCHEMA, _no_kind_with_levels)

NURSING_SERVICE_SCHEMA = vol.Schema(
    {
        **_ENTRY_SCHEMA,
        **_TIMING_SCHEMA,
        vol.Optional(ATTR_SIDE, default="next"): vol.In(NURSING_SIDES),
    }
)


@dataclass(frozen=True, slots=True)
class BabyTrackerService:
    """One service and the API call it maps to."""

    name: str
    path: str
    schema: Any
    # Fields copied straight from the call into the JSON body.
    body_fields: tuple[str, ...] = ()


SERVICES: tuple[BabyTrackerService, ...] = (
    BabyTrackerService(SERVICE_SLEEP_START, "/sleep/start", TIMED_SERVICE_SCHEMA),
    BabyTrackerService(SERVICE_SLEEP_STOP, "/sleep/stop", TIMED_SERVICE_SCHEMA),
    BabyTrackerService(SERVICE_SLEEP_TOGGLE, "/sleep/toggle", TIMED_SERVICE_SCHEMA),
    BabyTrackerService(SERVICE_CRY_START, "/cry/start", TIMED_SERVICE_SCHEMA),
    BabyTrackerService(SERVICE_CRY_STOP, "/cry/stop", TIMED_SERVICE_SCHEMA),
    BabyTrackerService(SERVICE_BOTTLE, "/bottle", TIMED_SERVICE_SCHEMA),
    BabyTrackerService(
        SERVICE_CUE, "/cue", CUE_SERVICE_SCHEMA, body_fields=(ATTR_SUBTYPE,)
    ),
    BabyTrackerService(
        SERVICE_DIAPER,
        "/diaper",
        DIAPER_SERVICE_SCHEMA,
        body_fields=(ATTR_KIND, ATTR_PEE_LEVEL, ATTR_POOP_LEVEL),
    ),
    BabyTrackerService(
        SERVICE_NURSING, "/nursing", NURSING_SERVICE_SCHEMA, body_fields=(ATTR_SIDE,)
    ),
    BabyTrackerService(SERVICE_UNDO, "/undo", PLAIN_SERVICE_SCHEMA),
)


def _async_get_coordinator(hass: HomeAssistant, call: ServiceCall) -> Any:
    """Resolve the config entry the call is aimed at."""
    entry_id = call.data.get(ATTR_CONFIG_ENTRY_ID)
    entries = [
        entry
        for entry in hass.config_entries.async_entries(DOMAIN)
        if entry.state is ConfigEntryState.LOADED
    ]
    if entry_id is not None:
        entries = [entry for entry in entries if entry.entry_id == entry_id]
        if not entries:
            raise ServiceValidationError(
                translation_domain=DOMAIN,
                translation_key="entry_not_loaded",
            )
    if not entries:
        raise ServiceValidationError(
            translation_domain=DOMAIN, translation_key="no_entries"
        )
    if len(entries) > 1:
        raise ServiceValidationError(
            translation_domain=DOMAIN, translation_key="multiple_entries"
        )
    return entries[0].runtime_data


def _build_body(service: BabyTrackerService, call: ServiceCall) -> dict[str, Any]:
    """Turn the service call into the API's JSON body."""
    body: dict[str, Any] = {}
    if (minutes_ago := call.data.get(ATTR_MINUTES_AGO)) is not None:
        body[ATTR_MINUTES_AGO] = minutes_ago
    if (at_utc := call.data.get(ATTR_AT_UTC)) is not None:
        body[ATTR_AT_UTC] = _to_utc_iso(at_utc)
    for name in service.body_fields:
        if (value := call.data.get(name)) is not None:
            body[name] = value
    if ATTR_SIDE in body:
        body[ATTR_SIDE] = NURSING_SIDE_MAP[body[ATTR_SIDE]]
    return body


def _to_utc_iso(value: datetime | str) -> str:
    """Normalise a timestamp to a UTC ISO 8601 string."""
    if isinstance(value, str):
        parsed = dt_util.parse_datetime(value)
        if parsed is None:
            raise ServiceValidationError(
                translation_domain=DOMAIN, translation_key="invalid_at_utc"
            )
        value = parsed
    # A naive timestamp is read in the user's configured time zone, matching how HA
    # treats datetime input elsewhere.
    return dt_util.as_utc(value).isoformat()


def _make_handler(
    service: BabyTrackerService,
) -> Callable[[ServiceCall], Awaitable[ServiceResponse]]:
    """Build the handler for one service."""

    async def handler(call: ServiceCall) -> ServiceResponse:
        coordinator = _async_get_coordinator(call.hass, call)
        body = _build_body(service, call)
        try:
            response = await coordinator.client.async_command(
                service.path, body or None
            )
        except BabyTrackerError as err:
            raise HomeAssistantError(str(err)) from err

        # Refresh so the sensor reflects the change without waiting out the interval.
        await coordinator.async_request_refresh()
        # Only `speech_de` is documented; the rest of the payload is passed through
        # unchanged so nothing the API sends is lost.
        return dict(response)

    return handler


@callback
def async_setup_services(hass: HomeAssistant) -> None:
    """Register the Baby Tracker services once."""
    for service in SERVICES:
        if hass.services.has_service(DOMAIN, service.name):
            continue
        hass.services.async_register(
            DOMAIN,
            service.name,
            _make_handler(service),
            schema=service.schema,
            supports_response=SupportsResponse.OPTIONAL,
        )
