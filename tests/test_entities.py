"""Unit tests for Forecast Fusion HA entities."""

from datetime import UTC, datetime

from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.forecast_fusion.binary_sensor import (
    ForecastFusionStormAlertBinarySensor,
    ForecastFusionUmbrellaBinarySensor,
)
from custom_components.forecast_fusion.const import CONF_SOURCES, DOMAIN
from custom_components.forecast_fusion.coordinator import ForecastFusionRuntimeData
from custom_components.forecast_fusion.core.models import FusedForecastPoint, FusedValue
from custom_components.forecast_fusion.sensor import (
    ForecastFusionConfidenceSensor,
    ForecastFusionPerceivedTemperatureSensor,
    ForecastFusionStormRiskSensor,
    ForecastFusionThermalPerceptionSensor,
)
from custom_components.forecast_fusion.weather import ForecastFusionWeatherEntity


async def test_weather_and_sensors(hass):
    """Test weather, sensor, and binary sensor entity properties."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        title="Forecast Fusion",
        data={CONF_SOURCES: ["weather.mock_source"]},
    )
    entry.add_to_hass(hass)

    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()

    runtime_data: ForecastFusionRuntimeData = entry.runtime_data
    coordinator = runtime_data.coordinator

    now = datetime.now(UTC)
    point = FusedForecastPoint(
        valid_at=now,
        temperature=FusedValue(22.0, 0.9, 21.0, 23.0, (), "median", ()),
        apparent_temperature=FusedValue(23.0, 0.9, 22.0, 24.0, (), "median", ()),
        humidity=FusedValue(55.0, 0.9, None, None, (), "median", ()),
        precipitation_probability=FusedValue(60.0, 0.9, None, None, (), "median", ()),
        precipitation_amount=FusedValue(2.5, 0.9, None, None, (), "median", ()),
        wind_speed=FusedValue(4.0, 0.9, None, None, (), "median", ()),
        wind_gust=FusedValue(6.0, 0.9, None, None, (), "median", ()),
        cloud_cover=FusedValue(30.0, 0.9, None, None, (), "median", ()),
        condition=FusedValue("rainy", 0.9, None, None, (), "median", ()),
        overall_confidence=0.85,
    )

    coordinator.fused_forecast = [point]

    weather_entity = ForecastFusionWeatherEntity(coordinator, entry)
    assert weather_entity.native_temperature == 22.0
    assert weather_entity.native_apparent_temperature == 23.0
    assert weather_entity.condition == "rainy"

    forecast_data = await weather_entity.async_forecast_hourly()
    assert forecast_data is not None
    assert len(forecast_data) == 1
    assert forecast_data[0]["native_temperature"] == 22.0

    conf_sensor = ForecastFusionConfidenceSensor(coordinator, entry)
    assert conf_sensor.native_value == 85.0

    umbrella_sensor = ForecastFusionUmbrellaBinarySensor(coordinator, entry)
    assert umbrella_sensor.is_on is True

    storm_risk_sensor = ForecastFusionStormRiskSensor(coordinator, entry)
    storm_alert_sensor = ForecastFusionStormAlertBinarySensor(coordinator, entry)

    assert storm_risk_sensor.native_value in ("Brak", "Umiarkowane", "Wysokie", "Ekstremalne")
    assert isinstance(storm_alert_sensor.is_on, bool)
    assert storm_risk_sensor.extra_state_attributes["fused_points_count"] == 1

    perceived_sensor = ForecastFusionPerceivedTemperatureSensor(coordinator, entry)
    assert perceived_sensor.native_value is not None
    assert isinstance(perceived_sensor.native_value, float)
    assert "thermal_perception" in perceived_sensor.extra_state_attributes

    perception_sensor = ForecastFusionThermalPerceptionSensor(coordinator, entry)
    assert perception_sensor.native_value == "Komfortowo"
