"""Unit tests for WebSocket API commands."""

from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.forecast_fusion.const import CONF_SOURCES, DOMAIN


async def test_websocket_commands(hass, hass_ws_client):
    """Test forecast_fusion/get_overview websocket command."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        title="Forecast Fusion",
        data={CONF_SOURCES: ["weather.mock_source"]},
    )
    entry.add_to_hass(hass)

    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()

    client = await hass_ws_client(hass)
    await client.send_json_auto_id(
        {
            "type": "forecast_fusion/get_overview",
            "config_entry_id": entry.entry_id,
        }
    )
    response = await client.receive_json()

    assert response["success"] is True
    assert "fused_points" in response["result"]
