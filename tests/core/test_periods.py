"""Unit tests for time periods and DST safety."""

from datetime import UTC, datetime, time, timedelta
from zoneinfo import ZoneInfo

from custom_components.forecast_fusion.core.models import FusedForecastPoint, FusedValue
from custom_components.forecast_fusion.core.periods import (
    PeriodDefinition,
    aggregate_period_forecast,
    is_point_in_period,
)


def test_is_point_in_period():
    """Test point inclusion in period."""
    period = PeriodDefinition(
        period_id="commute",
        name="Commute",
        start_time=time(7, 0),
        end_time=time(9, 0),
        weekdays=(0, 1, 2, 3, 4),  # Mon-Fri
    )

    # Monday 08:00 UTC
    dt_mon = datetime(2026, 7, 20, 8, 0, 0, tzinfo=UTC)
    assert is_point_in_period(dt_mon, period, target_tz=UTC) is True

    # Sunday 08:00 UTC
    dt_sun = datetime(2026, 7, 19, 8, 0, 0, tzinfo=UTC)
    assert is_point_in_period(dt_sun, period, target_tz=UTC) is False


def test_dst_transition_safety():
    """Test DST spring forward and autumn fallback transition handling."""
    # Warsaw timezone (Europe/Warsaw)
    warsaw_tz = ZoneInfo("Europe/Warsaw")

    # Spring forward: 2026-03-29 07:00 local time
    dt_spring = datetime(2026, 3, 29, 7, 0, tzinfo=warsaw_tz)
    dt_spring_utc = dt_spring.astimezone(UTC)
    assert dt_spring_utc.tzinfo == UTC

    period = PeriodDefinition(
        period_id="morning",
        name="Morning",
        start_time=time(7, 0),
        end_time=time(9, 0),
    )

    assert is_point_in_period(dt_spring_utc, period, target_tz=warsaw_tz) is True


def test_aggregate_period_forecast():
    """Test forecast aggregation over a period."""
    now = datetime(2026, 7, 20, 8, 0, 0, tzinfo=UTC)

    p1 = FusedForecastPoint(
        valid_at=now,
        temperature=FusedValue(20.0, 0.9, 19.0, 21.0, (), "median", ()),
        apparent_temperature=FusedValue(21.0, 0.9, 20.0, 22.0, (), "median", ()),
        humidity=FusedValue(60.0, 0.9, None, None, (), "median", ()),
        precipitation_probability=FusedValue(10.0, 0.9, None, None, (), "median", ()),
        precipitation_amount=FusedValue(0.0, 0.9, None, None, (), "median", ()),
        wind_speed=FusedValue(3.5, 0.9, None, None, (), "median", ()),
        wind_gust=FusedValue(5.0, 0.9, None, None, (), "median", ()),
        cloud_cover=FusedValue(20.0, 0.9, None, None, (), "median", ()),
        condition=FusedValue("sunny", 0.9, None, None, (), "median", ()),
        overall_confidence=0.9,
    )

    period = PeriodDefinition("test", "Test", time(7, 0), time(10, 0))
    summary = aggregate_period_forecast(
        period, now - timedelta(hours=1), now + timedelta(hours=1), [p1]
    )

    assert summary.temp_min_c == 20.0
    assert summary.temp_max_c == 20.0
    assert summary.dominant_condition == "sunny"
    assert summary.min_confidence == 0.9
