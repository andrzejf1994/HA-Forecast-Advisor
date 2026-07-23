"""DataUpdateCoordinator for Forecast Fusion."""

import logging
from datetime import timedelta

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .const import CONF_FUSION_ALGORITHM, CONF_SOURCES, DOMAIN
from .core.fusion import fuse_forecasts
from .core.models import ForecastPoint, FusedForecastPoint
from .managers.source_manager import SourceManager
from .repositories.sqlite import SQLiteRepository

_LOGGER = logging.getLogger(__name__)


class ForecastFusionRuntimeData:
    """Class to hold Forecast Fusion runtime data."""

    def __init__(self, coordinator: "ForecastFusionCoordinator") -> None:
        """Initialize runtime data."""
        self.coordinator = coordinator


class ForecastFusionCoordinator(DataUpdateCoordinator[list[FusedForecastPoint]]):
    """Coordinator to manage fetching and fusing forecast data."""

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry) -> None:
        """Initialize coordinator."""
        super().__init__(
            hass,
            _LOGGER,
            config_entry=entry,
            name=DOMAIN,
            update_interval=timedelta(minutes=15),
        )
        self.entry = entry
        self.sources: list[str] = entry.data.get(CONF_SOURCES, [])
        self.algorithm: str = entry.options.get(CONF_FUSION_ALGORITHM, "weighted_median")

        db_path = hass.config.path(f"{DOMAIN}.db")
        self.repo = SQLiteRepository(db_path)

        self.source_manager = SourceManager(hass)
        self.fused_forecast: list[FusedForecastPoint] = []

    @property
    def overall_confidence(self) -> float:
        """Return average overall confidence across fused forecast points."""
        if not self.fused_forecast:
            return 1.0
        return sum(p.overall_confidence for p in self.fused_forecast) / len(self.fused_forecast)

    async def _async_update_data(self) -> list[FusedForecastPoint]:
        """Fetch forecasts from sources and fuse them."""
        try:
            sources_list = [{"id": s, "entity_id": s} for s in self.sources]
            snapshots_dict = await self.source_manager.async_fetch_all_sources(sources_list)

            all_points: list[ForecastPoint] = []
            for snap in snapshots_dict.values():
                all_points.extend(snap.points)

            fused = fuse_forecasts(all_points, algorithm=self.algorithm)
            self.fused_forecast = fused
            return fused
        except Exception as err:
            _LOGGER.exception("Error updating forecast fusion: %s", err)
            raise UpdateFailed(f"Error fetching forecasts: {err}") from err
