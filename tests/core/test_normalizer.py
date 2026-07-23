"""Unit tests for normalizer module."""

from datetime import UTC, datetime

from custom_components.forecast_fusion.core.enums import ForecastType
from custom_components.forecast_fusion.core.normalizer import (
    compute_raw_hash,
    ensure_utc,
    normalize_forecast_point,
    normalize_forecast_snapshot,
    sanitize_float,
)


def test_ensure_utc():
    """Test timezone conversion to UTC."""
    dt_naive = datetime(2026, 7, 22, 10, 0, 0)
    dt_utc = ensure_utc(dt_naive)
    assert dt_utc.tzinfo == UTC
    assert dt_utc.hour == 10

    iso_str = "2026-07-22T12:00:00+02:00"
    dt_parsed = ensure_utc(iso_str)
    assert dt_parsed.tzinfo == UTC
    assert dt_parsed.hour == 10

    assert ensure_utc(None) is None
    assert ensure_utc("invalid_date") is None


def test_sanitize_float():
    """Test float sanitization and range bounds."""
    assert sanitize_float(25.5, -50.0, 50.0) == 25.5
    assert sanitize_float("18.2") == 18.2
    assert sanitize_float("invalid") is None
    assert sanitize_float(float("nan")) is None
    assert sanitize_float(float("inf")) is None
    assert sanitize_float(150.0, 0.0, 100.0) is None
    assert sanitize_float(-10.0, 0.0, 100.0) is None
    assert sanitize_float(None) is None


def test_normalize_forecast_point():
    """Test normalization of raw forecast point."""
    now = datetime.now(UTC)
    raw_point = {
        "datetime": "2026-07-22T14:00:00+00:00",
        "temperature": 22.5,
        "apparent_temperature": 23.0,
        "humidity": 65.0,
        "precipitation_probability": 15.0,
        "wind_speed": 4.5,
        "wind_bearing": 360.0,
        "condition": " Sunny ",
    }

    point = normalize_forecast_point("source_a", ForecastType.HOURLY, now, raw_point)
    assert point is not None
    assert point.source_id == "source_a"
    assert point.temperature_c == 22.5
    assert point.humidity_pct == 65.0
    assert point.wind_bearing_deg == 0.0  # 360 normalized to 0
    assert point.condition == "sunny"
    assert len(point.raw_hash) > 0


def test_normalize_forecast_snapshot():
    """Test normalization and sorting of forecast snapshot."""
    now = datetime.now(UTC)
    raw_points = [
        {"datetime": "2026-07-22T15:00:00+00:00", "temperature": 24.0},
        {"datetime": "2026-07-22T14:00:00+00:00", "temperature": 22.0},
    ]

    snapshot = normalize_forecast_snapshot("source_a", ForecastType.HOURLY, now, raw_points)
    assert snapshot is not None
    assert snapshot.source_id == "source_a"
    assert len(snapshot.points) == 2
    # Verify sorted by valid_at
    assert snapshot.points[0].temperature_c == 22.0
    assert snapshot.points[1].temperature_c == 24.0


def test_compute_raw_hash():
    """Test canonical hashing."""
    h1 = compute_raw_hash({"a": 1, "b": 2})
    h2 = compute_raw_hash({"b": 2, "a": 1})
    assert h1 == h2
    assert len(h1) == 64
