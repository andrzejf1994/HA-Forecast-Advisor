"""Test Forecast Fusion config flow and options flow."""

from unittest.mock import patch

from homeassistant import config_entries, data_entry_flow
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.forecast_fusion.const import (
    CONF_POLL_INTERVAL_MINUTES,
    CONF_SOURCES,
    DOMAIN,
)


async def test_full_config_flow_success(hass):
    """Test successful config flow."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )
    assert result["type"] == data_entry_flow.FlowResultType.FORM
    assert result["step_id"] == "user"

    result2 = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        {
            "name": "My Forecast Fusion",
            CONF_SOURCES: ["weather.source1", "weather.source2"],
            CONF_POLL_INTERVAL_MINUTES: 30,
        },
    )
    assert result2["type"] == data_entry_flow.FlowResultType.CREATE_ENTRY
    assert result2["title"] == "My Forecast Fusion"
    assert result2["data"][CONF_SOURCES] == ["weather.source1", "weather.source2"]
    assert result2["data"][CONF_POLL_INTERVAL_MINUTES] == 30


async def test_config_flow_no_sources_error(hass):
    """Test config flow error when no sources selected."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )
    result2 = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        {
            "name": "Forecast Fusion",
            CONF_SOURCES: [],
            CONF_POLL_INTERVAL_MINUTES: 30,
        },
    )
    assert result2["type"] == data_entry_flow.FlowResultType.FORM
    assert result2["errors"] == {"base": "no_sources"}


async def test_config_flow_single_instance(hass):
    """Test that only one instance of Forecast Fusion can be configured."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        unique_id=f"{DOMAIN}_instance",
        data={CONF_SOURCES: ["weather.source1"]},
    )
    entry.add_to_hass(hass)

    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )
    result2 = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        {
            "name": "Second Instance",
            CONF_SOURCES: ["weather.source2"],
        },
    )
    assert result2["type"] == data_entry_flow.FlowResultType.ABORT
    assert result2["reason"] == "already_configured"


async def test_options_flow_success(hass):
    """Test options flow."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        unique_id=f"{DOMAIN}_instance",
        data={
            CONF_SOURCES: ["weather.source1"],
            CONF_POLL_INTERVAL_MINUTES: 30,
        },
    )
    entry.add_to_hass(hass)

    with patch("custom_components.forecast_fusion.async_setup_entry", return_value=True):
        await hass.config_entries.async_setup(entry.entry_id)
        await hass.async_block_till_done()

    result = await hass.config_entries.options.async_init(entry.entry_id)
    assert result["type"] == data_entry_flow.FlowResultType.FORM
    assert result["step_id"] == "init"

    result2 = await hass.config_entries.options.async_configure(
        result["flow_id"],
        {
            CONF_SOURCES: ["weather.source1", "weather.source2"],
            CONF_POLL_INTERVAL_MINUTES: 15,
        },
    )
    assert result2["type"] == data_entry_flow.FlowResultType.CREATE_ENTRY
    assert result2["data"][CONF_SOURCES] == ["weather.source1", "weather.source2"]
    assert result2["data"][CONF_POLL_INTERVAL_MINUTES] == 15


async def test_options_flow_no_sources_error(hass):
    """Test options flow error when no sources selected."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        unique_id=f"{DOMAIN}_instance",
        data={CONF_SOURCES: ["weather.source1"]},
    )
    entry.add_to_hass(hass)

    with patch("custom_components.forecast_fusion.async_setup_entry", return_value=True):
        await hass.config_entries.async_setup(entry.entry_id)
        await hass.async_block_till_done()

    result = await hass.config_entries.options.async_init(entry.entry_id)
    result2 = await hass.config_entries.options.async_configure(
        result["flow_id"],
        {
            CONF_SOURCES: [],
            CONF_POLL_INTERVAL_MINUTES: 30,
        },
    )
    assert result2["type"] == data_entry_flow.FlowResultType.FORM
    assert result2["errors"] == {"base": "no_sources"}
