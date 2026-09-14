"""Button platform for Forecast Fusion."""

import logging

from homeassistant.components.button import ButtonEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .coordinator import ForecastFusionCoordinator, ForecastFusionRuntimeData
from .entity import ForecastFusionBaseEntity

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Forecast Fusion button entities."""
    runtime_data: ForecastFusionRuntimeData = entry.runtime_data
    coordinator = runtime_data.coordinator

    async_add_entities([ForecastFusionResetDatabaseButton(coordinator, entry)])


class ForecastFusionResetDatabaseButton(ForecastFusionBaseEntity, ButtonEntity):
    """Diagnostic button entity to reset Forecast Fusion database."""

    _attr_entity_category = EntityCategory.DIAGNOSTIC
    _attr_entity_registry_enabled_default = False
    _attr_icon = "mdi:database-remove"

    def __init__(self, coordinator: ForecastFusionCoordinator, entry: ConfigEntry) -> None:
        """Initialize reset database button."""
        super().__init__(
            coordinator,
            unique_id=f"{entry.entry_id}_reset_database",
            name=None,
        )
        self._attr_translation_key = "reset_database"
        self.entry = entry

    async def async_press(self) -> None:
        """Handle button press to reset SQLite database."""
        _LOGGER.warning("Diagnostic action triggered: Resetting Forecast Fusion database")
        await self.coordinator.repo.reset_database()
        self.coordinator.fused_forecast = []
        await self.coordinator.async_request_refresh()
