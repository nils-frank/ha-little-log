"""Shared placeholder test data."""

from __future__ import annotations

from typing import Any

# Placeholder token in the documented `bt_` shape - not a real credential.
MOCK_TOKEN = "bt_testtoken000000000000000000000"

STATUS_PAYLOAD: dict[str, Any] = {
    "state": "asleep",
    "since_utc": "2026-01-01T12:00:00+00:00",
    "elapsed_min": 42,
    "last_sleep": {"start_utc": "2026-01-01T10:00:00+00:00", "duration_min": 90},
    "today": {"sleep_min": 180, "bottles": 2, "diapers": 3},
    "say": {
        "summary": "Placeholder summary.",
        "state": "Placeholder state.",
        "last_sleep": "Placeholder last sleep.",
        "forecast": "Placeholder forecast.",
        "today": "Placeholder today.",
        "diaper": "Placeholder diaper.",
        "bottle": "Placeholder bottle.",
        "nursing": "Placeholder nursing.",
    },
}

COMMAND_RESPONSE: dict[str, Any] = {"ok": True, "speech_de": "Platzhalter."}
