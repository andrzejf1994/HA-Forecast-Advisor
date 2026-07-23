"""Unit tests for WebSocket API commands."""

from datetime import UTC, datetime

from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.forecast_fusion.const import CONF_SOURCES, DOMAIN


async def test_websocket_commands_overview_and_history(hass, hass_ws_client):
    """Test forecast_fusion/get_overview and get_history websocket commands."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        title="Forecast Fusion",
        data={CONF_SOURCES: ["weather.mock_source"]},
    )
    entry.add_to_hass(hass)

    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()

    client = await hass_ws_client(hass)

    # Test get_overview
    await client.send_json_auto_id(
        {
            "type": "forecast_fusion/get_overview",
            "config_entry_id": entry.entry_id,
        }
    )
    resp_overview = await client.receive_json()
    assert resp_overview["success"] is True
    assert "fused_points" in resp_overview["result"]
    assert "verification_sensors" in resp_overview["result"]

    # Test get_history
    await client.send_json_auto_id(
        {
            "type": "forecast_fusion/get_history",
            "config_entry_id": entry.entry_id,
        }
    )
    resp_hist = await client.receive_json()
    assert resp_hist["success"] is True
    assert "recent_observations" in resp_hist["result"]

    # Test submit_feedback
    now_iso = datetime.now(UTC).isoformat()
    await client.send_json_auto_id(
        {
            "type": "forecast_fusion/submit_feedback",
            "config_entry_id": entry.entry_id,
            "user_profile_id": "test_user",
            "start_at": now_iso,
            "end_at": now_iso,
            "comfort_score": 0,
            "manual_rain_observation": "rain",
        }
    )
    resp_fb = await client.receive_json()
    assert resp_fb["success"] is True
    assert "feedback_id" in resp_fb["result"]

    # Test save_verification_sensors
    await client.send_json_auto_id(
        {
            "type": "forecast_fusion/save_verification_sensors",
            "config_entry_id": entry.entry_id,
            "verification_sensors": {
                "temperature": "sensor.outdoor_temp",
                "humidity": "sensor.outdoor_humidity",
            },
        }
    )
    resp_sens = await client.receive_json()
    assert resp_sens["success"] is True
    assert resp_sens["result"]["verification_sensors"]["temperature"] == "sensor.outdoor_temp"
