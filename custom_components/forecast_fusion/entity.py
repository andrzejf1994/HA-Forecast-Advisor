"""Base entity class for Forecast Fusion."""

from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .coordinator import ForecastFusionCoordinator


class ForecastFusionBaseEntity(CoordinatorEntity[ForecastFusionCoordinator]):
    """Base entity class for Forecast Fusion integration."""

    _attr_has_entity_name = True

    def __init__(
        self,
        coordinator: ForecastFusionCoordinator,
        unique_id: str,
        name: str | None,
    ) -> None:
        """Initialize base entity."""
        super().__init__(coordinator)
        self._attr_unique_id = unique_id
        self._attr_name = name
        entry_id = (
            coordinator.config_entry.entry_id if coordinator.config_entry else "forecast_fusion"
        )
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, entry_id)},
            name="Forecast Fusion System",
            manufacturer="Forecast Fusion",
            model="Forecast Fusion Engine",
            sw_version="0.1.0",
        )
