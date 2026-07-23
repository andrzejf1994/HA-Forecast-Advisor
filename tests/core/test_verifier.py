"""Unit tests for forecast verifier."""

from datetime import UTC, datetime, timedelta

from custom_components.forecast_fusion.core.enums import (
    ForecastType,
    ObservationQuality,
    ObservationSourceMode,
    WeatherParameter,
)
from custom_components.forecast_fusion.core.models import (
    ForecastPoint,
    Observation,
)
from custom_components.forecast_fusion.core.verifier import verify_forecast_point


def test_verify_forecast_point_temperature():
    """Test temperature verification against observation."""
    now = datetime.now(UTC)
    valid_at = now + timedelta(hours=2)
    fetched_at = now - timedelta(hours=1)

    point = ForecastPoint(
        source_id="src1",
        forecast_type=ForecastType.HOURLY,
        fetched_at=fetched_at,
        issued_at=fetched_at,
        valid_at=valid_at,
        lead_time=timedelta(hours=3),
        temperature_c=25.0,
        raw_hash="hash1",
    )

    prev_point = ForecastPoint(
        source_id="src1",
        forecast_type=ForecastType.HOURLY,
        fetched_at=fetched_at - timedelta(hours=1),
        issued_at=fetched_at - timedelta(hours=1),
        valid_at=valid_at,
        lead_time=timedelta(hours=4),
        temperature_c=22.0,
        raw_hash="hash_prev",
    )

    obs = Observation(
        observation_id="obs1",
        parameter=WeatherParameter.TEMPERATURE,
        start_at=valid_at - timedelta(minutes=30),
        end_at=valid_at + timedelta(minutes=30),
        value=23.0,
        unit="°C",
        source_mode=ObservationSourceMode.ENTITY,
        source_entity_id="sensor.temp",
        quality=ObservationQuality.MEASURED_PRECISE,
        entered_at=now,
        metadata={},
    )

    res = verify_forecast_point(point, obs, prev_point=prev_point)
    assert res is not None
    assert res.source_id == "src1"
    assert res.error == 2.0  # 25 - 23
    assert res.abs_error == 2.0
    assert res.stability_delta == 3.0  # |25 - 22|
    assert res.correction_benefit == -1.0  # |22 - 23| - |25 - 23| = 1 - 2 = -1


def test_verify_forecast_point_post_observation_discard():
    """Test that forecasts fetched AFTER observation start are discarded."""
    now = datetime.now(UTC)
    obs_start = now - timedelta(hours=2)
    obs_end = now - timedelta(hours=1)

    # Forecast fetched AFTER observation started
    point = ForecastPoint(
        source_id="src1",
        forecast_type=ForecastType.HOURLY,
        fetched_at=obs_start + timedelta(minutes=10),
        issued_at=None,
        valid_at=obs_start + timedelta(minutes=15),
        lead_time=timedelta(minutes=5),
        temperature_c=20.0,
        raw_hash="hash",
    )

    obs = Observation(
        observation_id="obs1",
        parameter=WeatherParameter.TEMPERATURE,
        start_at=obs_start,
        end_at=obs_end,
        value=20.0,
        unit="°C",
        source_mode=ObservationSourceMode.ENTITY,
        source_entity_id="sensor.temp",
        quality=ObservationQuality.MEASURED_PRECISE,
        entered_at=now,
        metadata={},
    )

    res = verify_forecast_point(point, obs)
    assert res is None
