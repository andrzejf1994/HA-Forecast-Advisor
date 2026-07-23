"""Constants for the Forecast Fusion & Personal Comfort integration."""

from typing import Final

DOMAIN: Final[str] = "forecast_fusion"

# Configuration keys
CONF_SOURCES: Final[str] = "sources"
CONF_WEATHER_ENTITY_ID: Final[str] = "weather_entity_id"
CONF_POLL_INTERVAL_MINUTES: Final[str] = "poll_interval_minutes"
CONF_INITIAL_WEIGHT: Final[str] = "initial_weight"
CONF_INCLUDED_FIELDS: Final[str] = "included_fields"
CONF_RETENTION: Final[str] = "retention"
CONF_OBSERVATIONS: Final[str] = "observations"
CONF_FUSION_ALGORITHM: Final[str] = "fusion_algorithm"
CONF_VERIFICATION_SENSORS: Final[str] = "verification_sensors"
CONF_AI_TASK_ENGINE: Final[str] = "ai_task_engine"

# Defaults
DEFAULT_POLL_INTERVAL_MINUTES: Final[int] = 30
DEFAULT_INITIAL_WEIGHT: Final[float] = 1.0
DEFAULT_RAW_FORECASTS_RETENTION_DAYS: Final[int] = 90
DEFAULT_OBSERVATIONS_RETENTION_DAYS: Final[int] = 365
DEFAULT_VERIFICATION_RESULTS_RETENTION_DAYS: Final[int] = 365
DEFAULT_COMFORT_FEEDBACK_RETENTION_DAYS: Final[int] = 0  # 0 means indefinite
DEFAULT_AGGREGATED_STATISTICS_RETENTION_DAYS: Final[int] = 0

# Storage
STORAGE_KEY: Final[str] = "forecast_fusion.storage"
STORAGE_VERSION: Final[int] = 1
DB_FILENAME: Final[str] = "forecast_fusion.db"

# Services
SERVICE_REFRESH: Final[str] = "refresh"
SERVICE_RECORD_OBSERVATION: Final[str] = "record_observation"
SERVICE_RECORD_COMFORT_FEEDBACK: Final[str] = "record_comfort_feedback"
SERVICE_RECALCULATE: Final[str] = "recalculate"
SERVICE_CLEANUP: Final[str] = "cleanup"
SERVICE_EXPORT_DATA: Final[str] = "export_data"
SERVICE_GENERATE_AI_ANALYSIS: Final[str] = "generate_ai_analysis"

# Events
EVENT_FORECAST_UPDATED: Final[str] = "forecast_fusion_forecast_updated"
EVENT_SIGNIFICANT_CHANGE: Final[str] = "forecast_fusion_significant_change"
EVENT_FEEDBACK_RECORDED: Final[str] = "forecast_fusion_feedback_recorded"
EVENT_MODEL_UPDATED: Final[str] = "forecast_fusion_model_updated"
EVENT_SOURCE_UNHEALTHY: Final[str] = "forecast_fusion_source_unhealthy"
EVENT_RECOMMENDATION_CHANGED: Final[str] = "forecast_fusion_recommendation_changed"

# Default Lead Time Buckets (in minutes)
DEFAULT_LEAD_TIME_BUCKETS: Final[list[dict[str, int | str]]] = [
    {"id": "0_3h", "minimum_minutes": 0, "maximum_minutes": 180},
    {"id": "3_12h", "minimum_minutes": 180, "maximum_minutes": 720},
    {"id": "12_24h", "minimum_minutes": 720, "maximum_minutes": 1440},
    {"id": "24_48h", "minimum_minutes": 1440, "maximum_minutes": 2880},
    {"id": "48h_plus", "minimum_minutes": 2880, "maximum_minutes": 10080},
]
