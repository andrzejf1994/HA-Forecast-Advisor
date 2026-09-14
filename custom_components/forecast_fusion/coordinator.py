"""DataUpdateCoordinator for Forecast Fusion."""

import asyncio
import logging
from datetime import UTC, datetime, timedelta

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .const import CONF_FUSION_ALGORITHM, CONF_SOURCES, CONF_VERIFICATION_SENSORS, DOMAIN
from .core.enums import ForecastType, WeatherParameter
from .core.fusion import fuse_forecasts
from .core.models import ForecastPoint, ForecastSnapshot, FusedForecastPoint, FusedValue
from .managers.feedback_manager import FeedbackManager
from .managers.observation_manager import ObservationManager
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
        self.sources: list[str] = entry.options.get(CONF_SOURCES, entry.data.get(CONF_SOURCES, []))
        self.algorithm: str = entry.options.get(CONF_FUSION_ALGORITHM, "weighted_median")

        db_path = hass.config.path(f"{DOMAIN}.db")
        self.repo = SQLiteRepository(db_path)

        self.source_manager = SourceManager(hass)
        self.observation_manager = ObservationManager(hass, self.repo)
        self.feedback_manager = FeedbackManager(self.repo)
        self.fused_forecast: list[FusedForecastPoint] = []

    @property
    def overall_confidence(self) -> float:
        """Return average overall confidence across fused forecast points."""
        if not self.fused_forecast:
            return 1.0
        return sum(p.overall_confidence for p in self.fused_forecast) / len(self.fused_forecast)

    async def _sample_verification_sensors(self) -> None:
        """Sample configured ground-truth verification sensors."""
        verification_sensors: dict[str, str] = self.entry.options.get(
            CONF_VERIFICATION_SENSORS, self.entry.data.get(CONF_VERIFICATION_SENSORS, {})
        )
        now = datetime.now(UTC)
        start_at = now - timedelta(minutes=15)

        param_map = {
            "temperature": WeatherParameter.TEMPERATURE,
            "humidity": WeatherParameter.HUMIDITY,
            "precipitation": WeatherParameter.PRECIPITATION,
            "precipitation_binary": WeatherParameter.PRECIPITATION,
            "wind_speed": WeatherParameter.WIND_SPEED,
        }

        for param_key, param_enum in param_map.items():
            sensor_entity_id = verification_sensors.get(param_key)
            if sensor_entity_id:
                await self.observation_manager.record_entity_observation(
                    parameter=param_enum,
                    entity_id=sensor_entity_id,
                    start_at=start_at,
                    end_at=now,
                )

    async def _async_update_data(self) -> list[FusedForecastPoint]:
        """Fetch forecasts from sources, sample verification sensors, and fuse forecasts."""
        try:
            # Refresh sources list from options or data
            self.sources = self.entry.options.get(
                CONF_SOURCES, self.entry.data.get(CONF_SOURCES, [])
            )
            sources_list = [{"id": s, "entity_id": s} for s in self.sources]
            snapshots_dict = await self.source_manager.async_fetch_all_sources(sources_list)

            all_points: list[ForecastPoint] = []
            for snap in snapshots_dict.values():
                all_points.extend(snap.points)
                try:
                    await self.repo.save_snapshot(snap)
                except Exception as s_err:
                    _LOGGER.debug("Could not save forecast snapshot: %s", s_err)

            fused = fuse_forecasts(all_points, algorithm=self.algorithm)

            # If live sources were unavailable on startup, attempt restoring last cached fused forecast
            if not fused and not self.fused_forecast:
                try:
                    async with asyncio.timeout(2.0):
                        cached_snapshots = await self.repo.query_snapshots(
                            source_id="forecast_fusion", limit=1
                        )
                    if cached_snapshots:
                        latest = cached_snapshots[0]
                        restored: list[FusedForecastPoint] = []
                        for p in latest.points:
                            restored.append(
                                FusedForecastPoint(
                                    valid_at=p.valid_at,
                                    temperature=FusedValue(
                                        p.temperature_c, 1.0, None, None, (), "cached", ()
                                    ),
                                    apparent_temperature=FusedValue(
                                        p.apparent_temperature_c, 1.0, None, None, (), "cached", ()
                                    ),
                                    humidity=FusedValue(
                                        p.humidity_pct, 1.0, None, None, (), "cached", ()
                                    ),
                                    precipitation_probability=FusedValue(
                                        p.precipitation_probability_pct,
                                        1.0,
                                        None,
                                        None,
                                        (),
                                        "cached",
                                        (),
                                    ),
                                    precipitation_amount=FusedValue(
                                        p.precipitation_mm, 1.0, None, None, (), "cached", ()
                                    ),
                                    wind_speed=FusedValue(
                                        p.wind_speed_ms, 1.0, None, None, (), "cached", ()
                                    ),
                                    wind_gust=FusedValue(
                                        p.wind_gust_ms, 1.0, None, None, (), "cached", ()
                                    ),
                                    cloud_cover=FusedValue(
                                        p.cloud_cover_pct, 1.0, None, None, (), "cached", ()
                                    ),
                                    condition=FusedValue(
                                        p.condition, 1.0, None, None, (), "cached", ()
                                    ),
                                    overall_confidence=1.0,
                                )
                            )
                        fused = restored
                        _LOGGER.info(
                            "Restored %d cached fused forecast points from SQLite on startup",
                            len(fused),
                        )
                except Exception as c_err:
                    _LOGGER.debug("Could not restore cached fused forecast: %s", c_err)

            self.fused_forecast = fused

            # Save fused forecast as a historical snapshot in SQLite
            if fused:
                now = datetime.now(UTC)
                snap_id = f"fusion_{now.strftime('%Y%m%d%H%M%S')}"
                fused_points = []
                for fp in fused:
                    t_val = (
                        float(fp.temperature.value)
                        if isinstance(fp.temperature.value, (int, float))
                        else None
                    )
                    app_val = (
                        float(fp.apparent_temperature.value)
                        if isinstance(fp.apparent_temperature.value, (int, float))
                        else None
                    )
                    h_val = (
                        float(fp.humidity.value)
                        if isinstance(fp.humidity.value, (int, float))
                        else None
                    )
                    pp_val = (
                        float(fp.precipitation_probability.value)
                        if isinstance(fp.precipitation_probability.value, (int, float))
                        else None
                    )
                    pa_val = (
                        float(fp.precipitation_amount.value)
                        if isinstance(fp.precipitation_amount.value, (int, float))
                        else None
                    )
                    w_val = (
                        float(fp.wind_speed.value)
                        if isinstance(fp.wind_speed.value, (int, float))
                        else None
                    )
                    c_val = str(fp.condition.value) if fp.condition.value else None

                    fused_points.append(
                        ForecastPoint(
                            source_id="forecast_fusion",
                            forecast_type=ForecastType.HOURLY,
                            fetched_at=now,
                            issued_at=now,
                            valid_at=fp.valid_at,
                            lead_time=fp.valid_at - now if fp.valid_at >= now else timedelta(0),
                            temperature_c=t_val,
                            apparent_temperature_c=app_val,
                            humidity_pct=h_val,
                            precipitation_probability_pct=pp_val,
                            precipitation_mm=pa_val,
                            wind_speed_ms=w_val,
                            condition=c_val,
                            raw_hash="fused",
                        )
                    )

                fused_snapshot = ForecastSnapshot(
                    snapshot_id=snap_id,
                    source_id="forecast_fusion",
                    fetched_at=now,
                    forecast_type=ForecastType.HOURLY,
                    points=tuple(fused_points),
                    raw_hash="fused",
                )
                try:
                    await self.repo.save_snapshot(fused_snapshot)
                except Exception as f_err:
                    _LOGGER.debug("Could not save fused forecast snapshot: %s", f_err)

            # Sample ground-truth verification sensors
            await self._sample_verification_sensors()

            return fused
        except Exception as err:
            _LOGGER.exception("Error updating forecast fusion: %s", err)
            raise UpdateFailed(f"Error fetching forecasts: {err}") from err
