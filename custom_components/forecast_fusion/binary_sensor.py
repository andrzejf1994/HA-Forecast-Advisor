"""Binary sensor platform for Forecast Fusion."""

from homeassistant.components.binary_sensor import BinarySensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .coordinator import ForecastFusionCoordinator, ForecastFusionRuntimeData
from .entity import ForecastFusionBaseEntity


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Forecast Fusion binary sensors."""
    runtime_data: ForecastFusionRuntimeData = entry.runtime_data
    coordinator = runtime_data.coordinator

    umbrella_sensor = ForecastFusionUmbrellaBinarySensor(coordinator, entry)
    async_add_entities([umbrella_sensor])


class ForecastFusionUmbrellaBinarySensor(ForecastFusionBaseEntity, BinarySensorEntity):
    """Binary sensor indicating whether an umbrella is recommended today."""

    def __init__(self, coordinator: ForecastFusionCoordinator, entry: ConfigEntry) -> None:
        """Initialize binary sensor."""
        super().__init__(
            coordinator,
            unique_id=f"{entry.entry_id}_umbrella_recommended",
            name="Forecast Fusion Umbrella Recommended",
        )

    @property
    def is_on(self) -> bool | None:
        """Return True if rain probability > 40% or rain amount > 1.0mm in next 24h."""
        if not self.coordinator.fused_forecast:
            return False

        for point in self.coordinator.fused_forecast[:24]:
            prob = point.precipitation_probability.value
            amt = point.precipitation_amount.value
            if isinstance(prob, (int, float)) and float(prob) > 40.0:
                return True
            if isinstance(amt, (int, float)) and float(amt) > 1.0:
                return True

        return False
