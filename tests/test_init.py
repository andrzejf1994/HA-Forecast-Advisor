"""Test Forecast Fusion integration setup, entry setup, and unload."""

from homeassistant.config_entries import ConfigEntryState
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.forecast_fusion import async_setup
from custom_components.forecast_fusion.const import CONF_SOURCES, DOMAIN
from custom_components.forecast_fusion.coordinator import ForecastFusionRuntimeData


async def test_async_setup(hass):
    """Test global async_setup."""
    assert await async_setup(hass, {})
    assert DOMAIN in hass.data


async def test_setup_and_unload_entry(hass):
    """Test setting up and unloading a config entry."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        title="Forecast Fusion",
        data={
            CONF_SOURCES: ["weather.mock_source"],
        },
    )
    entry.add_to_hass(hass)

    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    assert entry.state is ConfigEntryState.LOADED

    assert isinstance(entry.runtime_data, ForecastFusionRuntimeData)
    assert entry.runtime_data.coordinator is not None

    assert await hass.config_entries.async_unload(entry.entry_id)
    await hass.async_block_till_done()
    assert entry.state is ConfigEntryState.NOT_LOADED


async def test_reload_entry(hass):
    """Test reloading a config entry."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        title="Forecast Fusion",
        data={
            CONF_SOURCES: ["weather.mock_source"],
        },
    )
    entry.add_to_hass(hass)

    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    assert entry.state is ConfigEntryState.LOADED

    assert await hass.config_entries.async_reload(entry.entry_id)
    await hass.async_block_till_done()
    assert entry.state is ConfigEntryState.LOADED
    assert isinstance(entry.runtime_data, ForecastFusionRuntimeData)
