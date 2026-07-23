"""Period aggregation and time calculations with DST safety."""

from dataclasses import dataclass
from datetime import datetime, time, timezone

from .models import FusedForecastPoint


@dataclass(frozen=True, slots=True)
class PeriodDefinition:
    """Defines a time period for forecast aggregation."""

    period_id: str
    name: str
    start_time: time
    end_time: time
    weekdays: tuple[int, ...] = (0, 1, 2, 3, 4, 5, 6)  # 0=Mon..6=Sun
    crosses_midnight: bool = False
    enabled: bool = True


@dataclass(frozen=True, slots=True)
class PeriodForecastSummary:
    """Aggregated metrics for a given period."""

    period_id: str
    start_at: datetime
    end_at: datetime
    temp_min_c: float | None
    temp_max_c: float | None
    temp_avg_c: float | None
    apparent_temp_min_c: float | None
    precip_prob_max_pct: float | None
    precip_total_mm: float | None
    wind_speed_max_ms: float | None
    wind_gust_max_ms: float | None
    min_confidence: float
    dominant_condition: str | None


def is_point_in_period(
    valid_at: datetime,
    period: PeriodDefinition,
    target_tz: timezone | None = None,
) -> bool:
    """Check if valid_at datetime falls within period definition."""
    if not period.enabled:
        return False

    dt_eval = valid_at.astimezone(target_tz) if target_tz is not None else valid_at
    if dt_eval.weekday() not in period.weekdays:
        return False

    t = dt_eval.time()
    if not period.crosses_midnight:
        return period.start_time <= t <= period.end_time

    return t >= period.start_time or t <= period.end_time


def aggregate_period_forecast(
    period: PeriodDefinition,
    start_at: datetime,
    end_at: datetime,
    fused_points: list[FusedForecastPoint],
) -> PeriodForecastSummary:
    """Aggregate fused forecast points into a PeriodForecastSummary."""
    period_points = [
        p
        for p in fused_points
        if start_at <= p.valid_at <= end_at and is_point_in_period(p.valid_at, period)
    ]

    if not period_points:
        return PeriodForecastSummary(
            period_id=period.period_id,
            start_at=start_at,
            end_at=end_at,
            temp_min_c=None,
            temp_max_c=None,
            temp_avg_c=None,
            apparent_temp_min_c=None,
            precip_prob_max_pct=None,
            precip_total_mm=None,
            wind_speed_max_ms=None,
            wind_gust_max_ms=None,
            min_confidence=0.0,
            dominant_condition=None,
        )

    temps = [
        float(p.temperature.value)
        for p in period_points
        if isinstance(p.temperature.value, (int, float))
    ]
    app_temps = [
        float(p.apparent_temperature.value)
        for p in period_points
        if isinstance(p.apparent_temperature.value, (int, float))
    ]
    precip_probs = [
        float(p.precipitation_probability.value)
        for p in period_points
        if isinstance(p.precipitation_probability.value, (int, float))
    ]
    precip_amounts = [
        float(p.precipitation_amount.value)
        for p in period_points
        if isinstance(p.precipitation_amount.value, (int, float))
    ]
    wind_speeds = [
        float(p.wind_speed.value)
        for p in period_points
        if isinstance(p.wind_speed.value, (int, float))
    ]
    wind_gusts = [
        float(p.wind_gust.value)
        for p in period_points
        if isinstance(p.wind_gust.value, (int, float))
    ]
    confidences = [p.overall_confidence for p in period_points]

    conditions = [str(p.condition.value) for p in period_points if p.condition.value is not None]
    dominant_cond: str | None = None
    if conditions:
        from collections import Counter

        dominant_cond = Counter(conditions).most_common(1)[0][0]

    return PeriodForecastSummary(
        period_id=period.period_id,
        start_at=start_at,
        end_at=end_at,
        temp_min_c=min(temps) if temps else None,
        temp_max_c=max(temps) if temps else None,
        temp_avg_c=sum(temps) / len(temps) if temps else None,
        apparent_temp_min_c=min(app_temps) if app_temps else None,
        precip_prob_max_pct=max(precip_probs) if precip_probs else None,
        precip_total_mm=sum(precip_amounts) if precip_amounts else None,
        wind_speed_max_ms=max(wind_speeds) if wind_speeds else None,
        wind_gust_max_ms=max(wind_gusts) if wind_gusts else None,
        min_confidence=min(confidences) if confidences else 0.0,
        dominant_condition=dominant_cond,
    )
