"""Constants for the Baby Tracker integration."""

from __future__ import annotations

from datetime import timedelta
from typing import Final

DOMAIN: Final = "babytracker"

# The vendor migrated from https://lukas-reindl.de/babytracker/api/integration/v1 to
# this host and dropped the /babytracker path prefix. The old URL answers with a
# cross-host 301; HTTP clients (aiohttp included) strip the Authorization header on a
# cross-host redirect, which turns a valid token into a misleading 401. Always call the
# new host directly and never follow a redirect away from it.
API_BASE_URL: Final = "https://little-log.de/api/integration/v1"

CONF_TOKEN: Final = "token"

# Vendor-recommended poll interval (their own rest: scan_interval default).
DEFAULT_SCAN_INTERVAL: Final = timedelta(seconds=60)

# Shared optional fields for the timing of an event.
ATTR_MINUTES_AGO: Final = "minutes_ago"
ATTR_AT_UTC: Final = "at_utc"

# Diaper fields.
ATTR_KIND: Final = "kind"
ATTR_PEE_LEVEL: Final = "pee_level"
ATTR_POOP_LEVEL: Final = "poop_level"

# Cue fields.
ATTR_SUBTYPE: Final = "subtype"

# Nursing fields.
ATTR_SIDE: Final = "side"

# The API accepts 0-720 minutes for minutes_ago.
MIN_MINUTES_AGO: Final = 0
MAX_MINUTES_AGO: Final = 720

DIAPER_KINDS: Final = ["wet", "dirty", "both", "dry"]
DIAPER_LEVELS: Final = ["none", "light", "medium", "full"]
# The API takes "next", "L" and "R". The lowercase spellings are accepted as
# aliases so the service can offer translatable select options (a translation key
# may not contain uppercase letters) and are normalised before the request.
NURSING_SIDE_MAP: Final = {
    "next": "next",
    "left": "L",
    "right": "R",
    "L": "L",
    "R": "R",
}
NURSING_SIDES: Final = list(NURSING_SIDE_MAP)

SERVICE_SLEEP_START: Final = "sleep_start"
SERVICE_SLEEP_STOP: Final = "sleep_stop"
SERVICE_SLEEP_TOGGLE: Final = "sleep_toggle"
SERVICE_CRY_START: Final = "cry_start"
SERVICE_CRY_STOP: Final = "cry_stop"
SERVICE_BOTTLE: Final = "bottle"
SERVICE_CUE: Final = "cue"
SERVICE_DIAPER: Final = "diaper"
SERVICE_NURSING: Final = "nursing"
SERVICE_UNDO: Final = "undo"
