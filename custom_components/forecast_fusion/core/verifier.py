"""Forecast verifier module for matching forecasts with ground truth observations."""

import hashlib
from datetime import UTC, datetime
from typing import Any

from .enums import WeatherParameter
from .metrics import (
    calculate_bias,
    calculate_brier_score,
    calculate_correction_benefit,
    calculate_mae,
    calculate_stability_delta,
)
from .models import ForecastPoint, Observation, VerificationResult


def match_lead_time_bucket(
    lead_time_seconds: float,
    buckets: list[dict[str, Any]],
) -> str:
    """Match lead time in seconds to configured lead time bucket ID."""
    lead_minutes = lead_time_seconds / 60.0

    for bucket in buckets:
        min_m = float(bucket.get("minimum_minutes", 0))
        max_m = float(bucket.get("maximum_minutes", 10080))
        bucket_id = str(bucket.get("id", "default"))

        if min_m <= lead_minutes < max_m:
            return bucket_id

    return "unknown"


def extract_parameter_value(
    point: ForecastPoint, parameter: WeatherParameter
) -> float | str | bool | None:
    """Extract parameter value from ForecastPoint."""
    match parameter:
        case WeatherParameter.TEMPERATURE:
            return point.temperature_c
        case WeatherParameter.APPARENT_TEMPERATURE:
            return point.apparent_temperature_c
        case WeatherParameter.DEW_POINT:
            return point.dew_point_c
        case WeatherParameter.HUMIDITY:
            return point.humidity_pct
        case WeatherParameter.PRESSURE:
            return point.pressure_hpa
        case WeatherParameter.PRECIPITATION_PROBABILITY:
            return point.precipitation_probability_pct
        case WeatherParameter.PRECIPITATION:
            return point.precipitation_mm
        case WeatherParameter.SNOW:
            return point.snow_mm
        case WeatherParameter.WIND_SPEED:
            return point.wind_speed_ms
        case WeatherParameter.WIND_GUST:
            return point.wind_gust_ms
        case WeatherParameter.WIND_BEARING:
            return point.wind_bearing_deg
        case WeatherParameter.CLOUD_COVER:
            return point.cloud_cover_pct
        case WeatherParameter.UV_INDEX:
            return point.uv_index
        case WeatherParameter.CONDITION:
            return point.condition


def verify_forecast_point(
    point: ForecastPoint,
    observation: Observation,
    prev_point: ForecastPoint | None = None,
    buckets: list[dict[str, Any]] | None = None,
) -> VerificationResult | None:
    """Verify a single forecast point against an observation."""
    if point.valid_at < observation.start_at or point.valid_at > observation.end_at:
        return None

    # Discard forecasts fetched AFTER the observation start time
    if point.fetched_at > observation.start_at:
        return None

    forecast_val = extract_parameter_value(point, observation.parameter)
    if forecast_val is None:
        return None

    observed_val = observation.value
    bucket_list = buckets or [
        {"id": "0_3h", "minimum_minutes": 0, "maximum_minutes": 180},
        {"id": "3_12h", "minimum_minutes": 180, "maximum_minutes": 720},
        {"id": "12_24h", "minimum_minutes": 720, "maximum_minutes": 1440},
    ]

    bucket_id = match_lead_time_bucket(point.lead_time.total_seconds(), bucket_list)

    error: float | None = None
    abs_error: float | None = None
    brier: float | None = None
    stability: float | None = None
    corr_benefit: float | None = None

    if isinstance(forecast_val, (int, float)) and isinstance(observed_val, (int, float)):
        f_num = float(forecast_val)
        o_num = float(observed_val)

        if observation.parameter == WeatherParameter.PRECIPITATION_PROBABILITY:
            brier = calculate_brier_score(f_num, bool(o_num > 0 or observed_val is True))
        else:
            error = calculate_bias(f_num, o_num)
            abs_error = calculate_mae(f_num, o_num)

        if prev_point is not None:
            prev_val = extract_parameter_value(prev_point, observation.parameter)
            if isinstance(prev_val, (int, float)):
                p_num = float(prev_val)
                stability = calculate_stability_delta(f_num, p_num)
                corr_benefit = calculate_correction_benefit(f_num, p_num, o_num)

    elif observation.parameter == WeatherParameter.PRECIPITATION_PROBABILITY:
        if isinstance(forecast_val, (int, float)) and isinstance(observed_val, bool):
            brier = calculate_brier_score(float(forecast_val), observed_val)

    now = datetime.now(UTC)
    raw_id_str = f"{point.source_id}_{observation.parameter.value}_{point.valid_at.isoformat()}_{point.fetched_at.isoformat()}"
    ver_id = hashlib.sha256(raw_id_str.encode("utf-8")).hexdigest()[:16]

    return VerificationResult(
        verification_id=ver_id,
        source_id=point.source_id,
        parameter=observation.parameter,
        lead_time_bucket=bucket_id,
        valid_at=point.valid_at,
        forecast_value=forecast_val,
        observed_value=observed_val,
        error=error,
        abs_error=abs_error,
        brier_score=brier,
        stability_delta=stability,
        correction_benefit=corr_benefit,
        verified_at=now,
    )
