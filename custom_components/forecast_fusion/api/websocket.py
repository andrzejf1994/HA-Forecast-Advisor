"""WebSocket API registration and handlers for Forecast Fusion."""

import logging
from datetime import UTC, datetime
from typing import Any

import voluptuous as vol
from homeassistant.components import websocket_api
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback

from ..const import (
    CONF_RADAR_ZOOM,
    CONF_VERIFICATION_SENSORS,
    DEFAULT_RADAR_ZOOM,
    DOMAIN,
)
from ..coordinator import ForecastFusionCoordinator, ForecastFusionRuntimeData
from ..core.enums import WeatherParameter
from ..core.fusion import fuse_forecasts
from ..core.models import ForecastPoint
from ..core.normalizer import ensure_utc

_LOGGER = logging.getLogger(__name__)


def _get_entry(hass: HomeAssistant, msg: dict[str, Any]) -> ConfigEntry | None:
    """Helper to get ConfigEntry from msg or fallback to first active entry."""
    entry_id = msg.get("config_entry_id")
    if entry_id:
        entry = hass.config_entries.async_get_entry(entry_id)
        if entry and entry.domain == DOMAIN:
            return entry
    entries = hass.config_entries.async_entries(DOMAIN)
    if entries:
        return entries[0]
    return None


@callback
def async_register_websocket_api(hass: HomeAssistant) -> None:
    """Register Forecast Fusion WebSocket commands."""
    websocket_api.async_register_command(hass, ws_get_overview)
    websocket_api.async_register_command(hass, ws_get_accuracy)
    websocket_api.async_register_command(hass, ws_get_history)
    websocket_api.async_register_command(hass, ws_submit_feedback)
    websocket_api.async_register_command(hass, ws_save_verification_sensors)


@websocket_api.websocket_command(  # type: ignore[attr-defined]
    {
        vol.Required("type"): "forecast_fusion/get_overview",
        vol.Optional("config_entry_id"): str,
    }
)
@websocket_api.async_response  # type: ignore[attr-defined]
async def ws_get_overview(hass: HomeAssistant, connection: Any, msg: dict[str, Any]) -> None:
    """Handle forecast_fusion/get_overview command."""
    entry = _get_entry(hass, msg)
    if not entry:
        connection.send_error(msg["id"], "entry_not_found", "Config entry not found")
        return

    runtime_data: ForecastFusionRuntimeData = entry.runtime_data
    coordinator: ForecastFusionCoordinator = runtime_data.coordinator

    points_summary = []
    if coordinator.fused_forecast:
        for p in coordinator.fused_forecast:
            points_summary.append(
                {
                    "valid_at": p.valid_at.isoformat(),
                    "temperature": p.temperature.value,
                    "apparent_temperature": p.apparent_temperature.value,
                    "humidity": p.humidity.value,
                    "precipitation_probability": p.precipitation_probability.value,
                    "precipitation_amount": p.precipitation_amount.value,
                    "wind_speed": p.wind_speed.value,
                    "wind_gust": p.wind_gust.value,
                    "condition": p.condition.value,
                    "overall_confidence": p.overall_confidence,
                }
            )

    verification_sensors = entry.options.get(
        CONF_VERIFICATION_SENSORS, entry.data.get(CONF_VERIFICATION_SENSORS, {})
    )
    radar_zoom = entry.options.get(
        CONF_RADAR_ZOOM, entry.data.get(CONF_RADAR_ZOOM, DEFAULT_RADAR_ZOOM)
    )

    connection.send_result(
        msg["id"],
        {
            "config_entry_id": entry.entry_id,
            "last_update_success": coordinator.last_update_success,
            "sources": coordinator.sources,
            "fusion_algorithm": coordinator.algorithm,
            "fused_points": points_summary,
            "overall_confidence": coordinator.overall_confidence,
            "verification_sensors": verification_sensors,
            "latitude": hass.config.latitude,
            "longitude": hass.config.longitude,
            "radar_zoom": radar_zoom,
        },
    )


@websocket_api.websocket_command(  # type: ignore[attr-defined]
    {
        vol.Required("type"): "forecast_fusion/get_accuracy",
        vol.Optional("config_entry_id"): str,
    }
)
@websocket_api.async_response  # type: ignore[attr-defined]
async def ws_get_accuracy(hass: HomeAssistant, connection: Any, msg: dict[str, Any]) -> None:
    """Handle forecast_fusion/get_accuracy command."""
    entry = _get_entry(hass, msg)
    if not entry:
        connection.send_error(msg["id"], "entry_not_found", "Config entry not found")
        return

    connection.send_result(
        msg["id"],
        {
            "status": "ok",
            "sources": entry.data.get("sources", []),
            "metrics": {},
        },
    )


@websocket_api.websocket_command(  # type: ignore[attr-defined]
    {
        vol.Required("type"): "forecast_fusion/get_history",
        vol.Optional("config_entry_id"): str,
    }
)
@websocket_api.async_response  # type: ignore[attr-defined]
async def ws_get_history(hass: HomeAssistant, connection: Any, msg: dict[str, Any]) -> None:
    """Handle forecast_fusion/get_history command."""
    entry = _get_entry(hass, msg)
    if not entry:
        connection.send_error(msg["id"], "entry_not_found", "Config entry not found")
        return

    runtime_data: ForecastFusionRuntimeData = entry.runtime_data
    coordinator = runtime_data.coordinator

    history_records = await coordinator.repo.query_observations()
    verification_sensors = entry.options.get(
        CONF_VERIFICATION_SENSORS, entry.data.get(CONF_VERIFICATION_SENSORS, {})
    )
    binary_precip_entity = verification_sensors.get("precipitation_binary")

    serialized_obs = []
    for o in history_records[:200]:
        param_name = o.parameter.value
        if binary_precip_entity and o.source_entity_id == binary_precip_entity:
            param_name = "precipitation_binary"
        serialized_obs.append(
            {
                "id": o.observation_id,
                "parameter": param_name,
                "start_at": o.start_at.isoformat(),
                "end_at": o.end_at.isoformat(),
                "value": o.value,
                "unit": o.unit,
                "source_mode": o.source_mode.value,
                "source_entity_id": o.source_entity_id,
            }
        )

    fused_summary = []
    if coordinator.fused_forecast:
        for p in coordinator.fused_forecast:
            fused_summary.append(
                {
                    "valid_at": p.valid_at.isoformat(),
                    "temperature": p.temperature.value,
                    "apparent_temperature": p.apparent_temperature.value,
                    "humidity": p.humidity.value,
                    "precipitation_probability": p.precipitation_probability.value,
                    "precipitation_amount": p.precipitation_amount.value,
                    "wind_speed": p.wind_speed.value,
                    "condition": p.condition.value,
                    "overall_confidence": p.overall_confidence,
                }
            )

    try:
        snapshots = await coordinator.repo.query_snapshots()
        past_points: list[ForecastPoint] = []
        for snap in snapshots:
            past_points.extend(snap.points)
        if past_points:
            fused_past = fuse_forecasts(past_points, algorithm=coordinator.algorithm)
            existing_times = {item["valid_at"] for item in fused_summary}
            for p in fused_past:
                v_iso = p.valid_at.isoformat()
                if v_iso not in existing_times:
                    existing_times.add(v_iso)
                    fused_summary.append(
                        {
                            "valid_at": v_iso,
                            "temperature": p.temperature.value,
                            "apparent_temperature": p.apparent_temperature.value,
                            "humidity": p.humidity.value,
                            "precipitation_probability": p.precipitation_probability.value,
                            "precipitation_amount": p.precipitation_amount.value,
                            "wind_speed": p.wind_speed.value,
                            "condition": p.condition.value,
                            "overall_confidence": p.overall_confidence,
                        }
                    )
    except Exception as exc:
        _LOGGER.debug("Could not query historical snapshots for history view: %s", exc)

    connection.send_result(
        msg["id"],
        {
            "status": "ok",
            "observations_count": len(history_records),
            "recent_observations": serialized_obs,
            "fused_points": fused_summary,
        },
    )


@websocket_api.websocket_command(  # type: ignore[attr-defined]
    {
        vol.Required("type"): "forecast_fusion/submit_feedback",
        vol.Optional("config_entry_id"): str,
        vol.Required("user_profile_id"): str,
        vol.Required("start_at"): str,
        vol.Required("end_at"): str,
        vol.Required("comfort_score"): vol.All(vol.Coerce(int), vol.Range(min=-3, max=3)),
        vol.Optional("observed_temp_c"): vol.Coerce(float),
        vol.Optional("whole_day", default=False): bool,
        vol.Optional("worn_outfit_id"): str,
        vol.Optional("transport_value"): str,
        vol.Optional("manual_rain_observation"): str,
    }
)
@websocket_api.async_response  # type: ignore[attr-defined]
async def ws_submit_feedback(hass: HomeAssistant, connection: Any, msg: dict[str, Any]) -> None:
    """Handle forecast_fusion/submit_feedback command for setting comfort rating/observation."""
    entry = _get_entry(hass, msg)
    if not entry:
        connection.send_error(msg["id"], "entry_not_found", "Config entry not found")
        return

    runtime_data: ForecastFusionRuntimeData = entry.runtime_data
    coordinator = runtime_data.coordinator

    start_utc = ensure_utc(msg["start_at"]) or datetime.now(UTC)
    end_utc = ensure_utc(msg["end_at"]) or datetime.now(UTC)
    observed_temp = msg.get("observed_temp_c", 20.0)

    fb = await coordinator.feedback_manager.record_feedback(
        user_profile_id=msg["user_profile_id"],
        start_at=start_utc,
        end_at=end_utc,
        comfort_score=msg["comfort_score"],
        observed_temp_c=observed_temp,
        whole_day=msg.get("whole_day", False),
        worn_outfit_id=msg.get("worn_outfit_id"),
        transport_value=msg.get("transport_value"),
    )

    if "manual_rain_observation" in msg and msg["manual_rain_observation"]:
        await coordinator.observation_manager.record_manual_observation(
            parameter=WeatherParameter.PRECIPITATION,
            start_at=start_utc,
            end_at=end_utc,
            value=msg["manual_rain_observation"],
        )

    connection.send_result(
        msg["id"],
        {
            "status": "ok",
            "feedback_id": fb.feedback_id,
        },
    )


@websocket_api.websocket_command(  # type: ignore[attr-defined]
    {
        vol.Required("type"): "forecast_fusion/save_verification_sensors",
        vol.Optional("config_entry_id"): str,
        vol.Required("verification_sensors"): dict,
    }
)
@websocket_api.async_response  # type: ignore[attr-defined]
async def ws_save_verification_sensors(
    hass: HomeAssistant, connection: Any, msg: dict[str, Any]
) -> None:
    """Handle forecast_fusion/save_verification_sensors command."""
    entry = _get_entry(hass, msg)
    if not entry:
        connection.send_error(msg["id"], "entry_not_found", "Config entry not found")
        return

    new_options = dict(entry.options)
    new_options[CONF_VERIFICATION_SENSORS] = msg["verification_sensors"]
    hass.config_entries.async_update_entry(entry, options=new_options)

    connection.send_result(
        msg["id"],
        {
            "status": "ok",
            "verification_sensors": msg["verification_sensors"],
        },
    )
