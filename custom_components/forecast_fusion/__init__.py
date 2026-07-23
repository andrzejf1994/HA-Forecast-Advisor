"""Forecast Fusion integration for Home Assistant."""

import logging
from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant, ServiceCall, SupportsResponse

from .api.websocket import async_register_websocket_api
from .const import DOMAIN
from .coordinator import ForecastFusionCoordinator, ForecastFusionRuntimeData

_LOGGER = logging.getLogger(__name__)

PLATFORMS: list[Platform] = [
    Platform.WEATHER,
    Platform.SENSOR,
    Platform.BINARY_SENSOR,
    Platform.SELECT,
    Platform.BUTTON,
]


async def async_setup(hass: HomeAssistant, config: dict[str, Any]) -> bool:
    """Set up the Forecast Fusion component."""
    hass.data.setdefault(DOMAIN, {})
    async_register_websocket_api(hass)

    async def handle_refresh(call: ServiceCall) -> None:
        """Handle refresh service call."""
        _LOGGER.info("Handling forecast_fusion.refresh service call")
        for entry in hass.config_entries.async_entries(DOMAIN):
            if hasattr(entry, "runtime_data") and entry.runtime_data:
                runtime_data: ForecastFusionRuntimeData = entry.runtime_data
                await runtime_data.coordinator.async_request_refresh()

    async def handle_recalculate(call: ServiceCall) -> None:
        """Handle recalculate service call."""
        _LOGGER.info("Handling forecast_fusion.recalculate service call")
        for entry in hass.config_entries.async_entries(DOMAIN):
            if hasattr(entry, "runtime_data") and entry.runtime_data:
                runtime_data: ForecastFusionRuntimeData = entry.runtime_data
                await runtime_data.coordinator.async_request_refresh()

    async def handle_record_observation(call: ServiceCall) -> None:
        """Handle record_observation service call."""
        _LOGGER.info("Handling forecast_fusion.record_observation service call")

    async def handle_record_comfort_feedback(call: ServiceCall) -> None:
        """Handle record_comfort_feedback service call."""
        _LOGGER.info("Handling forecast_fusion.record_comfort_feedback service call")

    async def handle_cleanup(call: ServiceCall) -> dict[str, Any]:
        """Handle cleanup service call."""
        _LOGGER.info("Handling forecast_fusion.cleanup service call")
        return {"status": "ok", "deleted_records": 0}

    async def handle_export_data(call: ServiceCall) -> dict[str, Any]:
        """Handle export_data service call."""
        _LOGGER.info("Handling forecast_fusion.export_data service call")
        return {"status": "ok", "exported_items": 0}

    async def handle_generate_ai_analysis(call: ServiceCall) -> dict[str, Any]:
        """Handle generate_ai_analysis service call."""
        _LOGGER.info("Handling forecast_fusion.generate_ai_analysis service call")
        return {"status": "ok", "analysis": "Forecast Fusion: Weather conditions are stable."}

    hass.services.async_register(DOMAIN, "refresh", handle_refresh)
    hass.services.async_register(DOMAIN, "recalculate", handle_recalculate)
    hass.services.async_register(DOMAIN, "record_observation", handle_record_observation)
    hass.services.async_register(DOMAIN, "record_comfort_feedback", handle_record_comfort_feedback)
    hass.services.async_register(
        DOMAIN, "cleanup", handle_cleanup, supports_response=SupportsResponse.OPTIONAL
    )
    hass.services.async_register(
        DOMAIN, "export_data", handle_export_data, supports_response=SupportsResponse.OPTIONAL
    )
    hass.services.async_register(
        DOMAIN,
        "generate_ai_analysis",
        handle_generate_ai_analysis,
        supports_response=SupportsResponse.OPTIONAL,
    )

    return True


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Forecast Fusion from a config entry."""
    coordinator = ForecastFusionCoordinator(hass, entry)
    await coordinator.async_config_entry_first_refresh()

    entry.runtime_data = ForecastFusionRuntimeData(coordinator=coordinator)

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    entry.async_on_unload(entry.add_update_listener(async_reload_entry))

    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    return bool(unload_ok)


async def async_reload_entry(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Reload config entry."""
    await async_unload_entry(hass, entry)
    await async_setup_entry(hass, entry)
