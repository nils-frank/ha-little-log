"""Config flow for the Baby Tracker integration."""

from __future__ import annotations

from collections.abc import Mapping
import logging
from typing import Any

import voluptuous as vol

from homeassistant.config_entries import ConfigFlow, ConfigFlowResult
from homeassistant.const import CONF_TOKEN
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.selector import (
    TextSelector,
    TextSelectorConfig,
    TextSelectorType,
)

from .api import BabyTrackerAuthError, BabyTrackerClient, BabyTrackerConnectionError
from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)

STEP_USER_DATA_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_TOKEN): TextSelector(
            TextSelectorConfig(type=TextSelectorType.PASSWORD)
        ),
    }
)


class BabyTrackerConfigFlow(ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Baby Tracker."""

    VERSION = 1

    async def _async_validate_token(self, token: str) -> dict[str, str]:
        """Validate a token with a live GET /status call.

        Returns a mapping of form errors, empty when the token works.
        """
        client = BabyTrackerClient(async_get_clientsession(self.hass), token)
        try:
            await client.async_get_status()
        except BabyTrackerAuthError:
            return {"base": "invalid_auth"}
        except BabyTrackerConnectionError:
            return {"base": "cannot_connect"}
        except Exception:
            _LOGGER.exception("Unexpected error validating the Baby Tracker token")
            return {"base": "unknown"}
        return {}

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Handle the initial step."""
        errors: dict[str, str] = {}
        if user_input is not None:
            token = user_input[CONF_TOKEN].strip()
            # One entry per token; the token is the only identity the API exposes.
            await self.async_set_unique_id(token)
            self._abort_if_unique_id_configured()

            errors = await self._async_validate_token(token)
            if not errors:
                return self.async_create_entry(
                    title="Baby Tracker", data={CONF_TOKEN: token}
                )

        return self.async_show_form(
            step_id="user", data_schema=STEP_USER_DATA_SCHEMA, errors=errors
        )

    async def async_step_reauth(
        self, entry_data: Mapping[str, Any]
    ) -> ConfigFlowResult:
        """Handle a token that stopped working."""
        return await self.async_step_reauth_confirm()

    async def async_step_reauth_confirm(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Ask for a fresh token."""
        errors: dict[str, str] = {}
        if user_input is not None:
            token = user_input[CONF_TOKEN].strip()
            errors = await self._async_validate_token(token)
            if not errors:
                return self.async_update_reload_and_abort(
                    self._get_reauth_entry(),
                    unique_id=token,
                    data_updates={CONF_TOKEN: token},
                )

        return self.async_show_form(
            step_id="reauth_confirm",
            data_schema=STEP_USER_DATA_SCHEMA,
            errors=errors,
        )
