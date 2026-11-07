"""Set up Home Hub check-in: where to send the "I'm online" message."""

from __future__ import annotations

from typing import Any

import voluptuous as vol

from homeassistant.config_entries import ConfigFlow, ConfigFlowResult
from homeassistant.helpers import selector

from .const import CONF_HOUSE, CONF_REMOTE, CONF_URL, DOMAIN

URL = selector.TextSelector(selector.TextSelectorConfig(type=selector.TextSelectorType.URL))


class CheckInConfigFlow(ConfigFlow, domain=DOMAIN):
    """One page: the house's name, the check-in address and how to reach it remotely."""

    VERSION = 1

    async def async_step_user(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        errors: dict[str, str] = {}
        if user_input is not None:
            url = user_input[CONF_URL].strip()
            if not url.startswith(("http://", "https://")):
                errors[CONF_URL] = "bad_url"
            else:
                data = {**user_input, CONF_URL: url}
                return self.async_create_entry(title=user_input[CONF_HOUSE], data=data)
        schema = vol.Schema(
            {
                vol.Required(CONF_HOUSE, default=self.hass.config.location_name): selector.TextSelector(),
                vol.Required(CONF_URL): URL,
                vol.Optional(CONF_REMOTE): URL,
            }
        )
        return self.async_show_form(step_id="user", data_schema=schema, errors=errors)
