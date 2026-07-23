"""Forecast fusion algorithms module (weighted median and two-stage precipitation)."""

import math
from collections import defaultdict
from datetime import datetime

from .models import (
    ForecastPoint,
    FusedForecastPoint,
    FusedValue,
    SourceContribution,
)


def calculate_weighted_median(
    weighted_values: list[tuple[float, float]],
) -> float | None:
    """Calculate weighted median from list of (value, weight) tuples.

    Invariant properties:
    - Order of inputs does not affect result (permutation invariant).
    - Result is bounded within [min(values), max(values)].
    """
    valid_pairs = [
        (v, w) for v, w in weighted_values if not (math.isnan(v) or math.isnan(w) or w < 0)
    ]
    if not valid_pairs:
        return None

    # Filter out 0 weight items unless all are 0
    total_weight = sum(w for _, w in valid_pairs)
    if total_weight <= 0:
        values = [v for v, _ in valid_pairs]
        values.sort()
        mid = len(values) // 2
        if len(values) % 2 == 1:
            return values[mid]
        return (values[mid - 1] + values[mid]) / 2.0

    # Sort by value
    sorted_pairs = sorted(valid_pairs, key=lambda pair: pair[0])

    half_weight = total_weight / 2.0
    cum_weight = 0.0

    for i, (val, weight) in enumerate(sorted_pairs):
        cum_weight += weight
        if math.isclose(cum_weight, half_weight, rel_tol=1e-9):
            if i + 1 < len(sorted_pairs):
                return (val + sorted_pairs[i + 1][0]) / 2.0
            return val
        if cum_weight > half_weight:
            return val

    return sorted_pairs[-1][0]


def calculate_weighted_mean(
    weighted_values: list[tuple[float, float]],
) -> float | None:
    """Calculate weighted mean from list of (value, weight) tuples."""
    valid_pairs = [(v, w) for v, w in weighted_values if w > 0 and not math.isnan(v)]
    if not valid_pairs:
        return None

    total_weight = sum(w for _, w in valid_pairs)
    if total_weight <= 0:
        return None

    weighted_sum = sum(v * w for v, w in valid_pairs)
    return weighted_sum / total_weight


def fuse_continuous_parameter(
    contributions: list[SourceContribution],
    method: str = "weighted_median",
) -> float | None:
    """Fuse a single continuous parameter from source contributions."""
    pairs: list[tuple[float, float]] = []
    for c in contributions:
        if isinstance(c.raw_value, (int, float)):
            pairs.append((float(c.raw_value), c.effective_weight))

    if not pairs:
        return None

    if method == "weighted_mean":
        return calculate_weighted_mean(pairs)

    return calculate_weighted_median(pairs)


def fuse_precipitation_two_stage(
    contributions_prob: list[SourceContribution],
    contributions_amount: list[SourceContribution],
) -> tuple[float, float, float]:
    """Execute two-stage precipitation fusion model.

    Returns:
    (precipitation_probability_pct, expected_precipitation_mm, conditional_amount_mm)
    """
    prob_val = fuse_continuous_parameter(contributions_prob, method="weighted_median")
    prob_pct = max(0.0, min(1.0, (prob_val / 100.0) if prob_val is not None else 0.0))

    # Stage 2: conditional amount for sources predicting non-zero rain
    rainy_sources = [
        c
        for c in contributions_amount
        if isinstance(c.raw_value, (int, float)) and float(c.raw_value) > 0.0
    ]

    if rainy_sources:
        conditional_amount = (
            fuse_continuous_parameter(rainy_sources, method="weighted_median") or 0.0
        )
    else:
        conditional_amount = (
            fuse_continuous_parameter(contributions_amount, method="weighted_median") or 0.0
        )

    conditional_amount = max(0.0, conditional_amount)
    expected_amount = prob_pct * conditional_amount

    return (prob_pct * 100.0, expected_amount, conditional_amount)


def fuse_forecasts(
    points: list[ForecastPoint],
    algorithm: str = "weighted_median",
) -> list[FusedForecastPoint]:
    """Group normalized points by valid_at and produce fused forecast points."""
    grouped: dict[datetime, list[ForecastPoint]] = defaultdict(list)
    for p in points:
        grouped[p.valid_at].append(p)

    fused_result: list[FusedForecastPoint] = []
    for valid_at, pts in sorted(grouped.items()):
        temp_contribs = [
            SourceContribution(p.source_id, 1.0, 1.0, p.temperature_c, 1.0, 1, 1.0)
            for p in pts
            if p.temperature_c is not None
        ]
        temp_fused = fuse_continuous_parameter(temp_contribs, method=algorithm)

        app_temp_contribs = [
            SourceContribution(p.source_id, 1.0, 1.0, p.apparent_temperature_c, 1.0, 1, 1.0)
            for p in pts
            if p.apparent_temperature_c is not None
        ]
        app_temp_fused = fuse_continuous_parameter(app_temp_contribs, method=algorithm)

        humidity_contribs = [
            SourceContribution(p.source_id, 1.0, 1.0, p.humidity_pct, 1.0, 1, 1.0)
            for p in pts
            if p.humidity_pct is not None
        ]
        humidity_fused = fuse_continuous_parameter(humidity_contribs, method=algorithm)

        prob_contribs = [
            SourceContribution(p.source_id, 1.0, 1.0, p.precipitation_probability_pct, 1.0, 1, 1.0)
            for p in pts
            if p.precipitation_probability_pct is not None
        ]
        amount_contribs = [
            SourceContribution(p.source_id, 1.0, 1.0, p.precipitation_mm, 1.0, 1, 1.0)
            for p in pts
            if p.precipitation_mm is not None
        ]

        prob_pct, exp_precip, _ = fuse_precipitation_two_stage(prob_contribs, amount_contribs)

        wind_speed_contribs = [
            SourceContribution(p.source_id, 1.0, 1.0, p.wind_speed_ms, 1.0, 1, 1.0)
            for p in pts
            if p.wind_speed_ms is not None
        ]
        wind_speed_fused = fuse_continuous_parameter(wind_speed_contribs, method=algorithm)

        wind_gust_contribs = [
            SourceContribution(p.source_id, 1.0, 1.0, p.wind_gust_ms, 1.0, 1, 1.0)
            for p in pts
            if p.wind_gust_ms is not None
        ]
        wind_gust_fused = fuse_continuous_parameter(wind_gust_contribs, method=algorithm)

        cloud_cover_contribs = [
            SourceContribution(p.source_id, 1.0, 1.0, p.cloud_cover_pct, 1.0, 1, 1.0)
            for p in pts
            if p.cloud_cover_pct is not None
        ]
        cloud_cover_fused = fuse_continuous_parameter(cloud_cover_contribs, method=algorithm)

        cond_val = pts[0].condition if pts else None

        fused_pt = FusedForecastPoint(
            valid_at=valid_at,
            temperature=FusedValue(temp_fused, 1.0, None, None, (), algorithm, ()),
            apparent_temperature=FusedValue(app_temp_fused, 1.0, None, None, (), algorithm, ()),
            humidity=FusedValue(humidity_fused, 1.0, None, None, (), algorithm, ()),
            precipitation_probability=FusedValue(prob_pct, 1.0, None, None, (), algorithm, ()),
            precipitation_amount=FusedValue(exp_precip, 1.0, None, None, (), algorithm, ()),
            wind_speed=FusedValue(wind_speed_fused, 1.0, None, None, (), algorithm, ()),
            wind_gust=FusedValue(wind_gust_fused, 1.0, None, None, (), algorithm, ()),
            cloud_cover=FusedValue(cloud_cover_fused, 1.0, None, None, (), algorithm, ()),
            condition=FusedValue(cond_val, 1.0, None, None, (), algorithm, ()),
            overall_confidence=1.0,
        )
        fused_result.append(fused_pt)

    return fused_result
