"""Config flow for Forecast Fusion integration."""

from typing import Any

import voluptuous as vol
from homeassistant.config_entries import (
    ConfigEntry,
    ConfigFlow,
    ConfigFlowResult,
    OptionsFlow,
)
from homeassistant.core import callback
from homeassistant.helpers import selector

from .const import (
    CONF_POLL_INTERVAL_MINUTES,
    CONF_SOURCES,
    DEFAULT_POLL_INTERVAL_MINUTES,
    DOMAIN,
)


class ForecastFusionConfigFlow(ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Forecast Fusion."""

    VERSION = 1

    async def async_step_user(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        """Handle the initial step."""
        errors: dict[str, str] = {}

        if user_input is not None:
            sources = user_input.get(CONF_SOURCES, [])
            if not sources:
                errors["base"] = "no_sources"
            else:
                await self.async_set_unique_id(f"{DOMAIN}_instance")
                self._abort_if_unique_id_configured()
                return self.async_create_entry(
                    title=user_input.get("name", "Forecast Fusion"),
                    data=user_input,
                )

        data_schema = vol.Schema(
            {
                vol.Required("name", default="Forecast Fusion"): str,
                vol.Required(CONF_SOURCES): selector.EntitySelector(
                    selector.EntitySelectorConfig(
                        domain="weather",
                        multiple=True,
                    )
                ),
                vol.Required(
                    CONF_POLL_INTERVAL_MINUTES,
                    default=DEFAULT_POLL_INTERVAL_MINUTES,
                ): vol.All(vol.Coerce(int), vol.Range(min=5, max=1440)),
            }
        )

        return self.async_show_form(
            step_id="user",
            data_schema=data_schema,
            errors=errors,
        )

    @staticmethod
    @callback
    def async_get_options_flow(config_entry: ConfigEntry) -> OptionsFlow:
        """Get the options flow for this handler."""
        return ForecastFusionOptionsFlowHandler()


class ForecastFusionOptionsFlowHandler(OptionsFlow):
    """Handle options for Forecast Fusion."""

    async def async_step_init(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        """Manage the options."""
        errors: dict[str, str] = {}

        if user_input is not None:
            sources = user_input.get(CONF_SOURCES, [])
            if not sources:
                errors["base"] = "no_sources"
            else:
                return self.async_create_entry(title="", data=user_input)

        current_sources = self.config_entry.options.get(
            CONF_SOURCES,
            self.config_entry.data.get(CONF_SOURCES, []),
        )
        current_poll_interval = self.config_entry.options.get(
            CONF_POLL_INTERVAL_MINUTES,
            self.config_entry.data.get(CONF_POLL_INTERVAL_MINUTES, DEFAULT_POLL_INTERVAL_MINUTES),
        )

        options_schema = vol.Schema(
            {
                vol.Required(CONF_SOURCES, default=current_sources): selector.EntitySelector(
                    selector.EntitySelectorConfig(
                        domain="weather",
                        multiple=True,
                    )
                ),
                vol.Required(
                    CONF_POLL_INTERVAL_MINUTES,
                    default=current_poll_interval,
                ): vol.All(vol.Coerce(int), vol.Range(min=5, max=1440)),
            }
        )

        return self.async_show_form(
            step_id="init",
            data_schema=options_schema,
            errors=errors,
        )
