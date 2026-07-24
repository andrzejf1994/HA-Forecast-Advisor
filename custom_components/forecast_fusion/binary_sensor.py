"""Binary sensor platform for Forecast Fusion."""

from homeassistant.components.binary_sensor import BinarySensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import CONF_VERIFICATION_SENSORS
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
    storm_sensor = ForecastFusionStormAlertBinarySensor(coordinator, entry)
    async_add_entities([umbrella_sensor, storm_sensor])


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


class ForecastFusionStormAlertBinarySensor(ForecastFusionBaseEntity, BinarySensorEntity):
    """Binary sensor indicating active storm warning or forecasted thunderstorm."""

    _attr_icon = "mdi:weather-lightning"

    def __init__(self, coordinator: ForecastFusionCoordinator, entry: ConfigEntry) -> None:
        """Initialize storm alert binary sensor."""
        super().__init__(
            coordinator,
            unique_id=f"{entry.entry_id}_storm_alert",
            name="Forecast Fusion Storm Alert",
        )
        self.entry = entry

    @property
    def is_on(self) -> bool:
        """Return True if a storm/lightning is forecasted or reported by verification sensors."""
        # 1. Check custom verification sensors (lightning e.g. Blitzortung and storm e.g. Burze.dzis.net)
        verification_sensors: dict[str, str] = self.entry.options.get(
            CONF_VERIFICATION_SENSORS, self.entry.data.get(CONF_VERIFICATION_SENSORS, {})
        )
        lightning_entity_id = verification_sensors.get("lightning")
        storm_entity_id = verification_sensors.get("storm")

        for ent_id in (lightning_entity_id, storm_entity_id):
            if ent_id:
                st = self.hass.states.get(ent_id)
                if st and st.state not in ("unknown", "unavailable"):
                    val_str = str(st.state).lower()
                    if val_str in ("on", "true") or "warning" in val_str:
                        return True
                    try:
                        dist = float(val_str)
                        if dist < 30.0:
                            return True
                    except ValueError:
                        pass

        # 2. Check forecast condition for thunderstorm / lightning
        if not self.coordinator.fused_forecast:
            return False

        for point in self.coordinator.fused_forecast[:24]:
            cond = str(point.condition.value or "").lower()
            if any(w in cond for w in ("lightning", "thunderstorm", "storm")):
                return True

        return False
