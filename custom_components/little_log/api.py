"""Async client for the Little Log integration API."""

from __future__ import annotations

from dataclasses import dataclass, field
import logging
from typing import Any

from aiohttp import ClientError, ClientResponseError, ClientSession, ClientTimeout

from .const import API_BASE_URL

_LOGGER = logging.getLogger(__name__)

# Generous but bounded: the API is a small cloud service and the coordinator polls it
# every 60s, so a request must never outlive its own interval.
REQUEST_TIMEOUT = ClientTimeout(total=30)


class LittleLogError(Exception):
    """Base error for all Little Log API failures."""


class LittleLogAuthError(LittleLogError):
    """Raised when the bearer token is rejected (HTTP 401/403)."""


class LittleLogConnectionError(LittleLogError):
    """Raised when the API is unreachable or answers unusably."""


@dataclass(slots=True)
class LittleLogStatus:
    """Parsed `GET /status` payload.

    Only `state` is treated as required. Everything else is optional because the full
    response schema is not published; the vendor documents `since_utc`, `elapsed_min`,
    `last_sleep`, `today` and `say`, and the nested shapes of `last_sleep`/`today`/`say`
    are passed through untouched rather than guessed at.
    """

    state: str | None = None
    since_utc: str | None = None
    elapsed_min: int | None = None
    last_sleep: dict[str, Any] = field(default_factory=dict)
    today: dict[str, Any] = field(default_factory=dict)
    say: dict[str, Any] = field(default_factory=dict)
    raw: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> LittleLogStatus:
        """Build a status from an API payload, tolerating missing/odd fields."""
        elapsed = data.get("elapsed_min")
        if not isinstance(elapsed, int) or isinstance(elapsed, bool):
            # Assumption: the API sends an integer. Anything else (float, string, null)
            # is coerced when possible and dropped otherwise, so one odd value cannot
            # break the whole update.
            try:
                elapsed = int(elapsed)  # type: ignore[arg-type]
            except (TypeError, ValueError):
                elapsed = None

        state = data.get("state")
        return cls(
            state=state if isinstance(state, str) else None,
            since_utc=data.get("since_utc")
            if isinstance(data.get("since_utc"), str)
            else None,
            elapsed_min=elapsed,
            last_sleep=_as_dict(data.get("last_sleep")),
            today=_as_dict(data.get("today")),
            say=_as_dict(data.get("say")),
            raw=data,
        )


def _as_dict(value: Any) -> dict[str, Any]:
    """Return `value` when it is a mapping, an empty dict otherwise."""
    return value if isinstance(value, dict) else {}


class LittleLogClient:
    """Thin async wrapper around the Little Log HTTP API."""

    def __init__(
        self,
        session: ClientSession,
        token: str,
        base_url: str = API_BASE_URL,
    ) -> None:
        """Initialise the client with an HA-managed aiohttp session."""
        self._session = session
        self._token = token
        self._base_url = base_url.rstrip("/")

    async def async_get_status(self) -> LittleLogStatus:
        """Fetch the current status."""
        data = await self._async_request("GET", "/status")
        return LittleLogStatus.from_dict(data)

    async def async_command(
        self, path: str, body: dict[str, Any] | None = None
    ) -> dict[str, Any]:
        """Run a write command and return its parsed response.

        Only `speech_de` is documented in POST responses; the whole payload is returned
        so callers can surface anything else the API happens to send.
        """
        return await self._async_request("POST", path, body)

    async def _async_request(
        self, method: str, path: str, body: dict[str, Any] | None = None
    ) -> dict[str, Any]:
        """Perform one request and normalise every failure into a typed error."""
        url = f"{self._base_url}{path}"
        try:
            response = await self._session.request(
                method,
                url,
                json=body,
                headers={"Authorization": f"Bearer {self._token}"},
                # Never follow redirects: the old vendor host 301s cross-host, and
                # aiohttp drops the Authorization header on such a hop, which surfaces
                # as a bogus 401 instead of a connection problem.
                allow_redirects=False,
                timeout=REQUEST_TIMEOUT,
            )
            if response.status in (301, 302, 303, 307, 308):
                raise LittleLogConnectionError(
                    f"Unexpected redirect from {url} to "
                    f"{response.headers.get('Location', 'unknown location')}; "
                    "the configured API base URL is wrong"
                )
            if response.status in (401, 403):
                raise LittleLogAuthError(
                    f"Little Log rejected the token (HTTP {response.status})"
                )
            response.raise_for_status()
            payload = await response.json(content_type=None)
        except LittleLogError:
            raise
        except ClientResponseError as err:
            # Any other non-2xx: no documented error codes, so report it generically.
            raise LittleLogConnectionError(
                f"Little Log returned HTTP {err.status} for {method} {path}"
            ) from err
        except (ClientError, TimeoutError) as err:
            raise LittleLogConnectionError(f"Cannot reach Little Log: {err}") from err
        except ValueError as err:
            raise LittleLogConnectionError(
                f"Little Log sent a non-JSON response for {method} {path}"
            ) from err

        if not isinstance(payload, dict):
            raise LittleLogConnectionError(
                f"Little Log sent an unexpected payload for {method} {path}"
            )
        return payload
