"""WebSocket API registration and handlers for Forecast Fusion."""

from typing import Any

import voluptuous as vol
from homeassistant.components import websocket_api
from homeassistant.core import HomeAssistant, callback

from ..const import DOMAIN
from ..coordinator import ForecastFusionRuntimeData


@callback
def async_register_websocket_api(hass: HomeAssistant) -> None:
    """Register Forecast Fusion WebSocket commands."""
    websocket_api.async_register_command(hass, ws_get_overview)
    websocket_api.async_register_command(hass, ws_get_accuracy)


@websocket_api.websocket_command(  # type: ignore[attr-defined]
    {
        vol.Required("type"): "forecast_fusion/get_overview",
        vol.Required("config_entry_id"): str,
    }
)
@websocket_api.async_response  # type: ignore[attr-defined]
async def ws_get_overview(hass: HomeAssistant, connection: Any, msg: dict[str, Any]) -> None:
    """Handle forecast_fusion/get_overview command."""
    entry_id = msg["config_entry_id"]
    entry = hass.config_entries.async_get_entry(entry_id)
    if not entry or entry.domain != DOMAIN:
        connection.send_error(msg["id"], "entry_not_found", "Config entry not found")
        return

    runtime_data: ForecastFusionRuntimeData = entry.runtime_data
    coordinator = runtime_data.coordinator

    points_summary = []
    if coordinator.fused_forecast:
        for p in coordinator.fused_forecast:
            points_summary.append(
                {
                    "valid_at": p.valid_at.isoformat(),
                    "temperature": p.temperature.value,
                    "apparent_temperature": p.apparent_temperature.value,
                    "precipitation_probability": p.precipitation_probability.value,
                    "precipitation_amount": p.precipitation_amount.value,
                    "wind_speed": p.wind_speed.value,
                    "condition": p.condition.value,
                    "overall_confidence": p.overall_confidence,
                }
            )

    connection.send_result(
        msg["id"],
        {
            "last_update_success": coordinator.last_update_success,
            "fused_points": points_summary,
            "overall_confidence": coordinator.overall_confidence,
        },
    )


@websocket_api.websocket_command(  # type: ignore[attr-defined]
    {
        vol.Required("type"): "forecast_fusion/get_accuracy",
        vol.Required("config_entry_id"): str,
    }
)
@websocket_api.async_response  # type: ignore[attr-defined]
async def ws_get_accuracy(hass: HomeAssistant, connection: Any, msg: dict[str, Any]) -> None:
    """Handle forecast_fusion/get_accuracy command."""
    entry_id = msg["config_entry_id"]
    entry = hass.config_entries.async_get_entry(entry_id)
    if not entry or entry.domain != DOMAIN:
        connection.send_error(msg["id"], "entry_not_found", "Config entry not found")
        return

    # Accuracy matrix report payload
    connection.send_result(
        msg["id"],
        {
            "status": "ok",
            "sources": entry.data.get("sources", []),
            "metrics": {},
        },
    )
