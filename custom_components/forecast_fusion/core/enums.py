"""Domain enums for forecast_fusion core package."""

from enum import StrEnum


class ForecastType(StrEnum):
    """Supported forecast types."""

    HOURLY = "hourly"
    DAILY = "daily"
    TWICE_DAILY = "twice_daily"


class WeatherParameter(StrEnum):
    """Weather parameters tracked and evaluated."""

    TEMPERATURE = "temperature"
    APPARENT_TEMPERATURE = "apparent_temperature"
    DEW_POINT = "dew_point"
    HUMIDITY = "humidity"
    PRESSURE = "pressure"
    PRECIPITATION_PROBABILITY = "precipitation_probability"
    PRECIPITATION = "precipitation"
    SNOW = "snow"
    WIND_SPEED = "wind_speed"
    WIND_GUST = "wind_gust"
    WIND_BEARING = "wind_bearing"
    CLOUD_COVER = "cloud_cover"
    UV_INDEX = "uv_index"
    CONDITION = "condition"


class ObservationSourceMode(StrEnum):
    """Observation source modes."""

    ENTITY = "entity"
    WEATHER_ENTITY_CURRENT = "weather_entity_current"
    MANUAL = "manual"
    DERIVED = "derived"
    DISABLED = "disabled"


class ObservationQuality(StrEnum):
    """Observation quality levels."""

    MEASURED_PRECISE = "measured_precise"
    MEASURED_APPROXIMATE = "measured_approximate"
    MANUAL_OBSERVATION = "manual_observation"
    ESTIMATED = "estimated"
    DERIVED = "derived"


class SampleStatus(StrEnum):
    """Sample status for historical scoring reliability."""

    INSUFFICIENT_DATA = "insufficient_data"  # < 10 samples
    PROVISIONAL = "provisional"  # 10..29 samples
    ESTABLISHED = "established"  # >= 30 samples


class ClothingCategory(StrEnum):
    """Clothing categories."""

    UPPER_BASE = "upper_base"
    UPPER_MID = "upper_mid"
    OUTER = "outer"
    LOWER = "lower"
    FOOTWEAR = "footwear"
    HEAD = "head"
    HANDS = "hands"
    NECK = "neck"
    ACCESSORY = "accessory"


class WholeDayStrategy(StrEnum):
    """Whole day optimization strategies."""

    MINIMIZE_TOTAL_DISCOMFORT = "minimize_total_discomfort"
    AVOID_COLD = "avoid_cold"
    AVOID_HEAT = "avoid_heat"
    WORST_PERIOD_FIRST = "worst_period_first"
    LONGEST_PERIOD_FIRST = "longest_period_first"
    MINIMUM_LAYERS = "minimum_layers"
    MAXIMUM_ADJUSTABILITY = "maximum_adjustability"


class AiProviderType(StrEnum):
    """Supported AI provider types."""

    DISABLED = "disabled"
    HA_CONVERSATION = "ha_conversation"
    OPENAI_COMPATIBLE = "openai_compatible"
    OPENAI = "openai"
    OLLAMA = "ollama"
