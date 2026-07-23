"""Weather platform for Forecast Fusion."""

from typing import Any

from homeassistant.components.weather import (
    Forecast,
    WeatherEntity,
    WeatherEntityFeature,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import (
    UnitOfPrecipitationDepth,
    UnitOfPressure,
    UnitOfSpeed,
    UnitOfTemperature,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .coordinator import ForecastFusionCoordinator, ForecastFusionRuntimeData
from .entity import ForecastFusionBaseEntity


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Forecast Fusion weather entity."""
    runtime_data: ForecastFusionRuntimeData = entry.runtime_data
    coordinator = runtime_data.coordinator

    entity = ForecastFusionWeatherEntity(coordinator, entry)
    async_add_entities([entity])


class ForecastFusionWeatherEntity(ForecastFusionBaseEntity, WeatherEntity):
    """Forecast Fusion fused weather entity."""

    _attr_supported_features = WeatherEntityFeature.FORECAST_HOURLY
    _attr_native_temperature_unit = UnitOfTemperature.CELSIUS
    _attr_native_precipitation_unit = UnitOfPrecipitationDepth.MILLIMETERS
    _attr_native_pressure_unit = UnitOfPressure.HPA
    _attr_native_wind_speed_unit = UnitOfSpeed.METERS_PER_SECOND

    def __init__(self, coordinator: ForecastFusionCoordinator, entry: ConfigEntry) -> None:
        """Initialize weather entity."""
        super().__init__(
            coordinator,
            unique_id=f"{entry.entry_id}_fused_weather",
            name="Forecast Fusion Weather",
        )

    @property
    def native_temperature(self) -> float | None:
        """Return fused current temperature."""
        if not self.coordinator.fused_forecast:
            return None
        val = self.coordinator.fused_forecast[0].temperature.value
        return float(val) if isinstance(val, (int, float)) else None

    @property
    def native_apparent_temperature(self) -> float | None:
        """Return fused apparent temperature."""
        if not self.coordinator.fused_forecast:
            return None
        val = self.coordinator.fused_forecast[0].apparent_temperature.value
        return float(val) if isinstance(val, (int, float)) else None

    @property
    def humidity(self) -> float | None:
        """Return fused humidity."""
        if not self.coordinator.fused_forecast:
            return None
        val = self.coordinator.fused_forecast[0].humidity.value
        return float(val) if isinstance(val, (int, float)) else None

    @property
    def native_wind_speed(self) -> float | None:
        """Return fused wind speed."""
        if not self.coordinator.fused_forecast:
            return None
        val = self.coordinator.fused_forecast[0].wind_speed.value
        return float(val) if isinstance(val, (int, float)) else None

    @property
    def condition(self) -> str | None:
        """Return fused weather condition."""
        if not self.coordinator.fused_forecast:
            return None
        val = self.coordinator.fused_forecast[0].condition.value
        return str(val) if val is not None else None

    async def async_forecast_hourly(self) -> list[Forecast] | None:
        """Return hourly forecast list."""
        if not self.coordinator.fused_forecast:
            return []

        forecast_list: list[Forecast] = []
        for point in self.coordinator.fused_forecast:
            f_dict: dict[str, Any] = {
                "datetime": point.valid_at.isoformat(),
            }
            if isinstance(point.temperature.value, (int, float)):
                f_dict["native_temperature"] = float(point.temperature.value)
            if isinstance(point.apparent_temperature.value, (int, float)):
                f_dict["native_apparent_temperature"] = float(point.apparent_temperature.value)
            if isinstance(point.precipitation_probability.value, (int, float)):
                f_dict["precipitation_probability"] = int(
                    float(point.precipitation_probability.value)
                )
            if isinstance(point.precipitation_amount.value, (int, float)):
                f_dict["native_precipitation"] = float(point.precipitation_amount.value)
            if isinstance(point.wind_speed.value, (int, float)):
                f_dict["native_wind_speed"] = float(point.wind_speed.value)
            if point.condition.value is not None:
                f_dict["condition"] = str(point.condition.value)

            forecast_list.append(f_dict)  # type: ignore[arg-type]

        return forecast_list
