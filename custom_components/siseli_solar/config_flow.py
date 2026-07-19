"""Config flow for Siseli Solar."""

import voluptuous as vol
from homeassistant import config_entries
from homeassistant.const import CONF_USERNAME
from homeassistant.data_entry_flow import FlowResult
from homeassistant.core import callback
from typing import Any

from .const import (
    DOMAIN,
    CONF_ACCOUNT,
    CONF_SISELI_PASSWORD,
    CONF_BASE_URL,
    DEFAULT_BASE_URL,
)

class SiseliSolarConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Siseli Solar."""

    VERSION = 1

    async def async_step_user(self, user_input: dict[str, Any] | None = None) -> FlowResult:
        """Handle the initial step."""
        errors: dict[str, str] = {}

        if user_input is not None:
            account = user_input[CONF_ACCOUNT]
            await self.async_set_unique_id(account)
            self._abort_if_unique_id_configured()
            return self.async_create_entry(
                title=account,
                data=user_input,
            )

        schema = vol.Schema(
            {
                vol.Required(CONF_ACCOUNT): str,
                vol.Required(CONF_SISELI_PASSWORD): str,
                vol.Optional(CONF_BASE_URL, default=DEFAULT_BASE_URL): str,
            }
        )

        return self.async_show_form(
            step_id="user",
            data_schema=schema,
            errors=errors,
        )
