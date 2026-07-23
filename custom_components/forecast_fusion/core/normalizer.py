"""Forecast data normalization and validation module."""

import hashlib
import json
import math
from datetime import UTC, datetime
from typing import Any

from .enums import ForecastType
from .models import ForecastPoint, ForecastSnapshot


def ensure_utc(dt: datetime | str | None) -> datetime | None:
    """Ensure datetime is timezone-aware UTC."""
    if dt is None:
        return None
    if isinstance(dt, str):
        try:
            parsed = datetime.fromisoformat(dt)
        except ValueError:
            return None
        dt = parsed
    if dt.tzinfo is None:
        return dt.replace(tzinfo=UTC)
    return dt.astimezone(UTC)


def sanitize_float(
    val: Any,
    min_val: float | None = None,
    max_val: float | None = None,
) -> float | None:
    """Sanitize float value, discarding NaN, infinity, or values out of range."""
    if val is None:
        return None
    try:
        fval = float(val)
    except (ValueError, TypeError):
        return None
    if math.isnan(fval) or math.isinf(fval):
        return None
    if min_val is not None and fval < min_val:
        return None
    if max_val is not None and fval > max_val:
        return None
    return fval


def compute_raw_hash(data: Any) -> str:
    """Compute sha256 hash of canonical serialized forecast data."""
    try:
        canonical_str = json.dumps(data, sort_keys=True, default=str)
        return hashlib.sha256(canonical_str.encode("utf-8")).hexdigest()
    except Exception:
        return ""


def normalize_forecast_point(
    source_id: str,
    forecast_type: ForecastType,
    fetched_at: datetime,
    raw_point: dict[str, Any],
) -> ForecastPoint | None:
    """Normalize a raw forecast point dictionary from weather.get_forecasts response."""
    raw_valid_at = raw_point.get("datetime") or raw_point.get("valid_at")
    valid_at = ensure_utc(raw_valid_at)
    if valid_at is None:
        return None

    raw_issued_at = raw_point.get("issued_at")
    issued_at = ensure_utc(raw_issued_at)
    fetched_utc = ensure_utc(fetched_at) or datetime.now(UTC)

    reference_time = issued_at if issued_at is not None else fetched_utc
    lead_time = valid_at - reference_time

    # Normalize fields
    temp = sanitize_float(raw_point.get("temperature"), -100.0, 70.0)
    app_temp = sanitize_float(raw_point.get("apparent_temperature"), -100.0, 70.0)
    dew_point = sanitize_float(raw_point.get("dew_point"), -100.0, 70.0)
    humidity = sanitize_float(raw_point.get("humidity"), 0.0, 100.0)
    pressure = sanitize_float(raw_point.get("pressure"), 500.0, 1100.0)

    precip_prob = sanitize_float(raw_point.get("precipitation_probability"), 0.0, 100.0)
    precip_mm = sanitize_float(raw_point.get("precipitation"), 0.0, 1000.0)
    snow_mm = sanitize_float(raw_point.get("snow"), 0.0, 1000.0)

    # Wind speed in m/s
    wind_speed = sanitize_float(raw_point.get("wind_speed"), 0.0, 150.0)
    wind_gust = sanitize_float(raw_point.get("wind_gust"), 0.0, 200.0)
    wind_bearing = sanitize_float(raw_point.get("wind_bearing"), 0.0, 360.0)
    if wind_bearing is not None and wind_bearing == 360.0:
        wind_bearing = 0.0

    cloud_cover = sanitize_float(raw_point.get("cloud_coverage"), 0.0, 100.0)
    uv_index = sanitize_float(raw_point.get("uv_index"), 0.0, 25.0)

    raw_cond = raw_point.get("condition")
    condition = raw_cond.strip().lower() if isinstance(raw_cond, str) else None

    raw_hash = compute_raw_hash(raw_point)

    return ForecastPoint(
        source_id=source_id,
        forecast_type=forecast_type,
        fetched_at=fetched_utc,
        issued_at=issued_at,
        valid_at=valid_at,
        lead_time=lead_time,
        temperature_c=temp,
        apparent_temperature_c=app_temp,
        dew_point_c=dew_point,
        humidity_pct=humidity,
        pressure_hpa=pressure,
        precipitation_probability_pct=precip_prob,
        precipitation_mm=precip_mm,
        snow_mm=snow_mm,
        wind_speed_ms=wind_speed,
        wind_gust_ms=wind_gust,
        wind_bearing_deg=wind_bearing,
        cloud_cover_pct=cloud_cover,
        uv_index=uv_index,
        condition=condition,
        raw_hash=raw_hash,
    )


def normalize_forecast_snapshot(
    source_id: str,
    forecast_type: ForecastType,
    fetched_at: datetime,
    raw_points: list[dict[str, Any]],
) -> ForecastSnapshot | None:
    """Normalize a raw forecast snapshot array into a ForecastSnapshot."""
    fetched_utc = ensure_utc(fetched_at) or datetime.now(UTC)
    points_list: list[ForecastPoint] = []

    for item in raw_points:
        point = normalize_forecast_point(source_id, forecast_type, fetched_utc, item)
        if point is not None:
            points_list.append(point)

    if not points_list:
        return None

    # Sort points by valid_at
    points_list.sort(key=lambda p: p.valid_at)
    tuple_points = tuple(points_list)
    raw_hash = compute_raw_hash([p.raw_hash for p in tuple_points])
    snapshot_id = f"{source_id}_{forecast_type.value}_{fetched_utc.strftime('%Y%m%dT%H%M%SZ')}"

    return ForecastSnapshot(
        snapshot_id=snapshot_id,
        source_id=source_id,
        fetched_at=fetched_utc,
        forecast_type=forecast_type,
        points=tuple_points,
        raw_hash=raw_hash,
    )
