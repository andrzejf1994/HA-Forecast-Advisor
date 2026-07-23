"""Diagnostics support for Forecast Fusion."""

from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.redact import async_redact_data

from .coordinator import ForecastFusionRuntimeData

TO_REDACT = {"api_key", "password", "token", "secret", "note", "latitude", "longitude"}


async def async_get_config_entry_diagnostics(
    hass: HomeAssistant, entry: ConfigEntry
) -> dict[str, Any]:
    """Return diagnostics for a config entry with redacted sensitive info."""
    runtime_data: ForecastFusionRuntimeData = entry.runtime_data
    coordinator = runtime_data.coordinator

    raw_data: dict[str, Any] = {
        "entry_title": entry.title,
        "entry_data": dict(entry.data),
        "entry_options": dict(entry.options),
        "coordinator_update_success": coordinator.last_update_success,
        "fused_points_count": len(coordinator.fused_forecast or []),
        "overall_confidence": coordinator.overall_confidence,
    }

    return async_redact_data(raw_data, TO_REDACT)
