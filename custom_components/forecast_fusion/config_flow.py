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
    CONF_VERIFICATION_SENSORS,
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
                verif_sensors = {}
                for k in ("temperature", "humidity", "precipitation", "wind_speed"):
                    s_val = user_input.pop(f"{k}_sensor", None)
                    if s_val:
                        verif_sensors[k] = s_val
                if verif_sensors:
                    user_input[CONF_VERIFICATION_SENSORS] = verif_sensors

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
                vol.Optional("temperature_sensor"): selector.EntitySelector(
                    selector.EntitySelectorConfig(domain="sensor", device_class="temperature")
                ),
                vol.Optional("humidity_sensor"): selector.EntitySelector(
                    selector.EntitySelectorConfig(domain="sensor", device_class="humidity")
                ),
                vol.Optional("precipitation_sensor"): selector.EntitySelector(
                    selector.EntitySelectorConfig(domain="sensor")
                ),
                vol.Optional("wind_speed_sensor"): selector.EntitySelector(
                    selector.EntitySelectorConfig(domain="sensor")
                ),
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
                verif_sensors = {}
                for k in ("temperature", "humidity", "precipitation", "wind_speed"):
                    s_val = user_input.pop(f"{k}_sensor", None)
                    if s_val:
                        verif_sensors[k] = s_val
                if verif_sensors:
                    user_input[CONF_VERIFICATION_SENSORS] = verif_sensors
                return self.async_create_entry(title="", data=user_input)

        current_sources = self.config_entry.options.get(
            CONF_SOURCES,
            self.config_entry.data.get(CONF_SOURCES, []),
        )
        current_poll_interval = self.config_entry.options.get(
            CONF_POLL_INTERVAL_MINUTES,
            self.config_entry.data.get(CONF_POLL_INTERVAL_MINUTES, DEFAULT_POLL_INTERVAL_MINUTES),
        )
        current_verif = self.config_entry.options.get(
            CONF_VERIFICATION_SENSORS,
            self.config_entry.data.get(CONF_VERIFICATION_SENSORS, {}),
        )

        schema_dict: dict[Any, Any] = {
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

        if current_verif.get("temperature"):
            schema_dict[
                vol.Optional("temperature_sensor", default=current_verif["temperature"])
            ] = selector.EntitySelector(
                selector.EntitySelectorConfig(domain="sensor", device_class="temperature")
            )
        else:
            schema_dict[vol.Optional("temperature_sensor")] = selector.EntitySelector(
                selector.EntitySelectorConfig(domain="sensor", device_class="temperature")
            )

        if current_verif.get("humidity"):
            schema_dict[vol.Optional("humidity_sensor", default=current_verif["humidity"])] = (
                selector.EntitySelector(
                    selector.EntitySelectorConfig(domain="sensor", device_class="humidity")
                )
            )
        else:
            schema_dict[vol.Optional("humidity_sensor")] = selector.EntitySelector(
                selector.EntitySelectorConfig(domain="sensor", device_class="humidity")
            )

        if current_verif.get("precipitation"):
            schema_dict[
                vol.Optional("precipitation_sensor", default=current_verif["precipitation"])
            ] = selector.EntitySelector(selector.EntitySelectorConfig(domain="sensor"))
        else:
            schema_dict[vol.Optional("precipitation_sensor")] = selector.EntitySelector(
                selector.EntitySelectorConfig(domain="sensor")
            )

        if current_verif.get("wind_speed"):
            schema_dict[vol.Optional("wind_speed_sensor", default=current_verif["wind_speed"])] = (
                selector.EntitySelector(selector.EntitySelectorConfig(domain="sensor"))
            )
        else:
            schema_dict[vol.Optional("wind_speed_sensor")] = selector.EntitySelector(
                selector.EntitySelectorConfig(domain="sensor")
            )

        return self.async_show_form(
            step_id="init",
            data_schema=vol.Schema(schema_dict),
            errors=errors,
        )
