"""Sensor platform for Forecast Fusion."""

from typing import Any

from homeassistant.components.sensor import SensorDeviceClass, SensorEntity, SensorStateClass
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import PERCENTAGE, UnitOfTemperature
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import CONF_VERIFICATION_SENSORS
from .coordinator import ForecastFusionCoordinator, ForecastFusionRuntimeData
from .core.apparent_temp import (
    calculate_perceived_temperature,
    get_thermal_perception,
)
from .entity import ForecastFusionBaseEntity


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Forecast Fusion sensors."""
    runtime_data: ForecastFusionRuntimeData = entry.runtime_data
    coordinator = runtime_data.coordinator

    confidence_sensor = ForecastFusionConfidenceSensor(coordinator, entry)
    storm_risk_sensor = ForecastFusionStormRiskSensor(coordinator, entry)
    perceived_temp_sensor = ForecastFusionPerceivedTemperatureSensor(coordinator, entry)
    perception_sensor = ForecastFusionThermalPerceptionSensor(coordinator, entry)
    async_add_entities(
        [confidence_sensor, storm_risk_sensor, perceived_temp_sensor, perception_sensor]
    )


class ForecastFusionConfidenceSensor(ForecastFusionBaseEntity, SensorEntity):
    """Sensor exposing overall forecast confidence percentage."""

    _attr_native_unit_of_measurement = PERCENTAGE
    _attr_state_class = SensorStateClass.MEASUREMENT

    def __init__(self, coordinator: ForecastFusionCoordinator, entry: ConfigEntry) -> None:
        """Initialize confidence sensor."""
        super().__init__(
            coordinator,
            unique_id=f"{entry.entry_id}_overall_confidence",
            name="Forecast Fusion Overall Confidence",
        )

    @property
    def native_value(self) -> float | None:
        """Return confidence as a percentage 0..100."""
        if not self.coordinator.fused_forecast:
            return None
        return round(self.coordinator.fused_forecast[0].overall_confidence * 100.0, 1)


class ForecastFusionStormRiskSensor(ForecastFusionBaseEntity, SensorEntity):
    """Sensor evaluating storm and lightning risk (supports Burze.dzis.net integration)."""

    _attr_icon = "mdi:flash"

    def __init__(self, coordinator: ForecastFusionCoordinator, entry: ConfigEntry) -> None:
        """Initialize storm risk sensor."""
        super().__init__(
            coordinator,
            unique_id=f"{entry.entry_id}_storm_risk",
            name="Forecast Fusion Storm Risk",
        )
        self.entry = entry

    @property
    def native_value(self) -> str:
        """Return storm risk level: Brak, Niskie, Umiarkowane, Wysokie, Ekstremalne."""
        # 1. Check if Burze.dzis.net or custom storm verification sensor is configured
        verification_sensors: dict[str, str] = self.entry.options.get(
            CONF_VERIFICATION_SENSORS, self.entry.data.get(CONF_VERIFICATION_SENSORS, {})
        )
        storm_entity_id = verification_sensors.get("storm")
        if storm_entity_id:
            st = self.hass.states.get(storm_entity_id)
            if st and st.state not in ("unknown", "unavailable"):
                val_str = str(st.state).lower()
                if val_str in ("on", "true") or "warning" in val_str:
                    return "Wysokie"
                try:
                    dist = float(val_str)
                    if dist < 10.0:
                        return "Ekstremalne"
                    if dist < 30.0:
                        return "Wysokie"
                    if dist < 50.0:
                        return "Umiarkowane"
                except ValueError:
                    pass

        # 2. Check forecast condition & precip probability / wind gust in fused points
        if not self.coordinator.fused_forecast:
            return "Brak"

        storm_points = 0
        high_prob = False

        for point in self.coordinator.fused_forecast[:24]:
            cond = str(point.condition.value or "").lower()
            if any(w in cond for w in ("lightning", "thunderstorm", "storm")):
                storm_points += 2
            prob = point.precipitation_probability.value
            if isinstance(prob, (int, float)) and float(prob) > 75.0:
                high_prob = True

        if storm_points >= 4:
            return "Ekstremalne"
        if storm_points >= 2:
            return "Wysokie"
        if storm_points >= 1 or high_prob:
            return "Umiarkowane"

        return "Brak"

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return extra storm risk attributes."""
        verification_sensors: dict[str, str] = self.entry.options.get(
            CONF_VERIFICATION_SENSORS, self.entry.data.get(CONF_VERIFICATION_SENSORS, {})
        )
        storm_entity_id = verification_sensors.get("storm")
        storm_sensor_state = None
        if storm_entity_id:
            st = self.hass.states.get(storm_entity_id)
            if st:
                storm_sensor_state = st.state

        return {
            "storm_sensor_entity": storm_entity_id,
            "storm_sensor_state": storm_sensor_state,
            "fused_points_count": len(self.coordinator.fused_forecast),
        }


class ForecastFusionPerceivedTemperatureSensor(ForecastFusionBaseEntity, SensorEntity):
    """Sensor calculating Thermodynamic Perceived / Apparent Temperature (WeatherSense style)."""

    _attr_device_class = SensorDeviceClass.TEMPERATURE
    _attr_native_unit_of_measurement = UnitOfTemperature.CELSIUS
    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_icon = "mdi:thermometer-lines"

    def __init__(self, coordinator: ForecastFusionCoordinator, entry: ConfigEntry) -> None:
        """Initialize perceived temperature sensor."""
        super().__init__(
            coordinator,
            unique_id=f"{entry.entry_id}_perceived_temperature",
            name="Forecast Fusion Perceived Temperature",
        )

    @property
    def native_value(self) -> float | None:
        """Return calculated perceived temperature (°C)."""
        if not self.coordinator.fused_forecast:
            return None

        p = self.coordinator.fused_forecast[0]
        temp = float(p.temperature.value) if isinstance(p.temperature.value, (int, float)) else 20.0
        hum = float(p.humidity.value) if isinstance(p.humidity.value, (int, float)) else 50.0
        wind = float(p.wind_speed.value) if isinstance(p.wind_speed.value, (int, float)) else 0.0

        return calculate_perceived_temperature(temp_c=temp, humidity_pct=hum, wind_speed_ms=wind)

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return extra attributes like thermal perception category."""
        val = self.native_value
        perception = get_thermal_perception(val) if val is not None else "Nieznane"
        return {
            "thermal_perception": perception,
        }


class ForecastFusionThermalPerceptionSensor(ForecastFusionBaseEntity, SensorEntity):
    """Sensor providing human-readable Bio-climatic Thermal Comfort perception level."""

    _attr_icon = "mdi:account-heart-outline"

    def __init__(self, coordinator: ForecastFusionCoordinator, entry: ConfigEntry) -> None:
        """Initialize thermal perception sensor."""
        super().__init__(
            coordinator,
            unique_id=f"{entry.entry_id}_thermal_perception",
            name="Forecast Fusion Thermal Perception",
        )

    @property
    def native_value(self) -> str:
        """Return thermal perception category (e.g. Komfortowo, Zimno, Parno)."""
        if not self.coordinator.fused_forecast:
            return "Brak danych"

        p = self.coordinator.fused_forecast[0]
        temp = float(p.temperature.value) if isinstance(p.temperature.value, (int, float)) else 20.0
        hum = float(p.humidity.value) if isinstance(p.humidity.value, (int, float)) else 50.0
        wind = float(p.wind_speed.value) if isinstance(p.wind_speed.value, (int, float)) else 0.0

        pt = calculate_perceived_temperature(temp_c=temp, humidity_pct=hum, wind_speed_ms=wind)
        return get_thermal_perception(pt)
