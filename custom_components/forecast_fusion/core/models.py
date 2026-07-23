"""Domain models for forecast_fusion core package."""

from collections.abc import Mapping
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Any

from .enums import (
    ClothingCategory,
    ForecastType,
    ObservationQuality,
    ObservationSourceMode,
    WeatherParameter,
)


@dataclass(frozen=True, slots=True)
class ForecastPoint:
    """A single forecast point issued by a forecast source for a valid time."""

    source_id: str
    forecast_type: ForecastType
    fetched_at: datetime
    issued_at: datetime | None
    valid_at: datetime
    lead_time: timedelta

    temperature_c: float | None = None
    apparent_temperature_c: float | None = None
    dew_point_c: float | None = None
    humidity_pct: float | None = None
    pressure_hpa: float | None = None

    precipitation_probability_pct: float | None = None
    precipitation_mm: float | None = None
    snow_mm: float | None = None

    wind_speed_ms: float | None = None
    wind_gust_ms: float | None = None
    wind_bearing_deg: float | None = None

    cloud_cover_pct: float | None = None
    uv_index: float | None = None
    condition: str | None = None
    raw_hash: str = ""


@dataclass(frozen=True, slots=True)
class ForecastSnapshot:
    """A snapshot of a full forecast retrieved from a single source."""

    snapshot_id: str
    source_id: str
    fetched_at: datetime
    forecast_type: ForecastType
    points: tuple[ForecastPoint, ...]
    raw_hash: str


@dataclass(frozen=True, slots=True)
class Observation:
    """A ground truth observation recorded for a given time window."""

    observation_id: str
    parameter: WeatherParameter
    start_at: datetime
    end_at: datetime
    value: float | str | bool
    unit: str | None
    source_mode: ObservationSourceMode
    source_entity_id: str | None
    quality: ObservationQuality
    entered_at: datetime
    metadata: Mapping[str, Any]


@dataclass(frozen=True, slots=True)
class VerificationResult:
    """Verification result comparing a forecast point against an observation."""

    verification_id: str
    source_id: str
    parameter: WeatherParameter
    lead_time_bucket: str
    valid_at: datetime
    forecast_value: float | str | bool
    observed_value: float | str | bool
    error: float | None
    abs_error: float | None
    brier_score: float | None
    stability_delta: float | None
    correction_benefit: float | None
    verified_at: datetime


@dataclass(frozen=True, slots=True)
class SourceContribution:
    """Contribution breakdown for a source in forecast fusion."""

    source_id: str
    weight: float
    effective_weight: float
    raw_value: float | str | bool | None
    quality_score: float
    sample_count: int
    freshness: float


@dataclass(frozen=True, slots=True)
class FusedValue:
    """Fused result for a single weather parameter."""

    value: float | str | bool | None
    confidence: float
    lower_bound: float | None
    upper_bound: float | None
    contributing_sources: tuple[SourceContribution, ...]
    method: str
    reason_codes: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class FusedForecastPoint:
    """Complete fused forecast point for a given time."""

    valid_at: datetime
    temperature: FusedValue
    apparent_temperature: FusedValue
    humidity: FusedValue
    precipitation_probability: FusedValue
    precipitation_amount: FusedValue
    wind_speed: FusedValue
    wind_gust: FusedValue
    cloud_cover: FusedValue
    condition: FusedValue
    overall_confidence: float


@dataclass(frozen=True, slots=True)
class ClothingItem:
    """Defines a single clothing item."""

    item_id: str
    name: str
    category: ClothingCategory
    warmth_score: float
    wind_protection: float
    rain_protection: float
    breathability: float
    removable: bool = False
    active: bool = True
    allowed_activity_profiles: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class Outfit:
    """Defines a complete outfit composed of clothing items."""

    outfit_id: str
    name: str
    item_ids: tuple[str, ...]
    warmth_score: float
    wind_protection: float
    rain_protection: float
    breathability: float
    layer_count: int
    adjustable: bool = True
    active: bool = True
    allowed_contexts: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class ContextProfile:
    """Activity context profile defining environmental sensitivity."""

    profile_id: str
    name: str
    activity_intensity: float = 0.5
    wind_exposure: float = 1.0
    rain_sensitivity: float = 1.0
    heat_generation: float = 0.5
    cold_penalty: float = 1.0
    heat_penalty: float = 1.0


@dataclass(frozen=True, slots=True)
class ComfortFeedback:
    """User feedback for comfort experienced in a time window."""

    feedback_id: str
    user_profile_id: str
    start_at: datetime
    end_at: datetime
    period_id: str | None
    whole_day: bool
    recommended_outfit_id: str | None
    worn_outfit_id: str | None
    optimal_outfit_id: str | None
    comfort_score: int  # -3 (cold) to +3 (hot), 0 optimal
    context_profile_id: str | None
    transport_value: str | None
    forecast_snapshot_id: str | None
    confidence: float
    note: str | None
    created_at: datetime


@dataclass(frozen=True, slots=True)
class ComfortBoundary:
    """Learned comfort boundaries for a user profile context."""

    user_profile_id: str
    context_profile_id: str
    transport_value: str
    outfit_id: str
    lower_temp_c: float
    upper_temp_c: float
    uncertainty: float
    sample_count: int
    last_updated: datetime
