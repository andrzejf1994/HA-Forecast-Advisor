"""Sensor platform for Forecast Fusion."""

from homeassistant.components.sensor import SensorEntity, SensorStateClass
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import PERCENTAGE
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .coordinator import ForecastFusionCoordinator, ForecastFusionRuntimeData
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
    async_add_entities([confidence_sensor])


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
