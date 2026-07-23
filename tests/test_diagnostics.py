"""Unit tests for Forecast Fusion diagnostics."""

from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.forecast_fusion.const import CONF_SOURCES, DOMAIN
from custom_components.forecast_fusion.diagnostics import async_get_config_entry_diagnostics


async def test_diagnostics(hass):
    """Test diagnostics output and credential redaction."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        title="Forecast Fusion",
        data={CONF_SOURCES: ["weather.mock_source"], "api_key": "secret123"},
    )
    entry.add_to_hass(hass)

    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()

    diag = await async_get_config_entry_diagnostics(hass, entry)
    assert diag["entry_title"] == "Forecast Fusion"
    assert diag["entry_data"]["api_key"] == "**REDACTED**"
