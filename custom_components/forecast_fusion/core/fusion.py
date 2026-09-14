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

DEFAULT_SIMILARITY_THRESHOLDS: dict[str, float] = {
    "temperature": 1.5,
    "apparent_temperature": 1.5,
    "humidity": 10.0,
    "precipitation_probability": 10.0,
    "precipitation_amount": 0.5,
    "wind_speed": 1.5,
    "wind_gust": 1.5,
    "cloud_cover": 15.0,
}


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


def check_source_similarity(
    values: list[float],
    threshold: float,
) -> bool:
    """Check if forecast values across sources have similar patterns (spread <= threshold)."""
    if len(values) <= 1:
        return True
    spread = max(values) - min(values)
    return spread <= threshold


def cap_weight_influence(
    contributions: list[SourceContribution],
    max_influence_pct: float = 0.20,
) -> list[SourceContribution]:
    """Cap the effective weight influence of better sources to max_influence_pct (default 20%)."""
    if not contributions:
        return []

    weights = [c.effective_weight for c in contributions]
    total_w = sum(weights)
    if total_w <= 0:
        return contributions

    n = len(contributions)
    baseline_w = total_w / n
    max_allowed_w = baseline_w * (1.0 + max_influence_pct)
    min_allowed_w = baseline_w * max(0.0, 1.0 - max_influence_pct)

    capped_contribs: list[SourceContribution] = []
    for c in contributions:
        capped_w = max(min_allowed_w, min(max_allowed_w, c.effective_weight))
        capped_contribs.append(
            SourceContribution(
                source_id=c.source_id,
                weight=c.weight,
                effective_weight=capped_w,
                raw_value=c.raw_value,
                quality_score=c.quality_score,
                sample_count=c.sample_count,
                freshness=c.freshness,
            )
        )
    return capped_contribs


def fuse_continuous_parameter_hybrid(
    contributions: list[SourceContribution],
    parameter_name: str = "temperature",
    max_influence_pct: float = 0.20,
    similarity_thresholds: dict[str, float] | None = None,
) -> tuple[float | None, str]:
    """Fuse a single continuous parameter from source contributions.

    - If values across sources show similar pattern (spread <= threshold): returns (unweighted median, 'median_unweighted').
    - Otherwise: applies weighted median capped to max 20% influence: returns (weighted median, 'weighted_median_capped_20').
    """
    pairs: list[tuple[float, float]] = []
    values: list[float] = []
    for c in contributions:
        if isinstance(c.raw_value, (int, float)) and not math.isnan(float(c.raw_value)):
            val = float(c.raw_value)
            values.append(val)
            pairs.append((val, c.effective_weight))

    if not pairs:
        return None, "none"

    thresholds = similarity_thresholds or DEFAULT_SIMILARITY_THRESHOLDS
    thresh = thresholds.get(parameter_name, 1.5)

    if check_source_similarity(values, thresh):
        unweighted_pairs = [(v, 1.0) for v in values]
        res = calculate_weighted_median(unweighted_pairs)
        return res, "median_unweighted"

    capped_contribs = cap_weight_influence(contributions, max_influence_pct)
    capped_pairs = [
        (float(c.raw_value), c.effective_weight)
        for c in capped_contribs
        if isinstance(c.raw_value, (int, float)) and not math.isnan(float(c.raw_value))
    ]
    res = calculate_weighted_median(capped_pairs)
    return res, "weighted_median_capped_20"


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
    max_influence_pct: float = 0.20,
) -> tuple[float, float, float, str]:
    """Execute two-stage precipitation fusion model.

    Returns:
    (precipitation_probability_pct, expected_precipitation_mm, conditional_amount_mm, method)
    """
    prob_val, method_prob = fuse_continuous_parameter_hybrid(
        contributions_prob,
        parameter_name="precipitation_probability",
        max_influence_pct=max_influence_pct,
    )
    prob_pct = max(0.0, min(1.0, (prob_val / 100.0) if prob_val is not None else 0.0))

    # Stage 2: conditional amount for sources predicting non-zero rain
    rainy_sources = [
        c
        for c in contributions_amount
        if isinstance(c.raw_value, (int, float)) and float(c.raw_value) > 0.0
    ]

    target_sources = rainy_sources if rainy_sources else contributions_amount
    cond_val, method_amount = fuse_continuous_parameter_hybrid(
        target_sources,
        parameter_name="precipitation_amount",
        max_influence_pct=max_influence_pct,
    )

    conditional_amount = max(0.0, cond_val or 0.0)
    expected_amount = prob_pct * conditional_amount
    used_method = (
        "median_unweighted"
        if (method_prob == "median_unweighted" and method_amount == "median_unweighted")
        else "weighted_median_capped_20"
    )

    return (prob_pct * 100.0, expected_amount, conditional_amount, used_method)


def fuse_forecasts(
    points: list[ForecastPoint],
    algorithm: str = "weighted_median",
    max_influence_pct: float = 0.20,
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
        temp_fused, temp_method = fuse_continuous_parameter_hybrid(
            temp_contribs, "temperature", max_influence_pct
        )

        app_temp_contribs = [
            SourceContribution(p.source_id, 1.0, 1.0, p.apparent_temperature_c, 1.0, 1, 1.0)
            for p in pts
            if p.apparent_temperature_c is not None
        ]
        app_temp_fused, app_temp_method = fuse_continuous_parameter_hybrid(
            app_temp_contribs, "apparent_temperature", max_influence_pct
        )

        humidity_contribs = [
            SourceContribution(p.source_id, 1.0, 1.0, p.humidity_pct, 1.0, 1, 1.0)
            for p in pts
            if p.humidity_pct is not None
        ]
        humidity_fused, humidity_method = fuse_continuous_parameter_hybrid(
            humidity_contribs, "humidity", max_influence_pct
        )

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

        prob_pct, exp_precip, _, precip_method = fuse_precipitation_two_stage(
            prob_contribs, amount_contribs, max_influence_pct
        )

        wind_speed_contribs = [
            SourceContribution(p.source_id, 1.0, 1.0, p.wind_speed_ms, 1.0, 1, 1.0)
            for p in pts
            if p.wind_speed_ms is not None
        ]
        wind_speed_fused, wind_speed_method = fuse_continuous_parameter_hybrid(
            wind_speed_contribs, "wind_speed", max_influence_pct
        )

        wind_gust_contribs = [
            SourceContribution(p.source_id, 1.0, 1.0, p.wind_gust_ms, 1.0, 1, 1.0)
            for p in pts
            if p.wind_gust_ms is not None
        ]
        wind_gust_fused, wind_gust_method = fuse_continuous_parameter_hybrid(
            wind_gust_contribs, "wind_gust", max_influence_pct
        )

        cloud_cover_contribs = [
            SourceContribution(p.source_id, 1.0, 1.0, p.cloud_cover_pct, 1.0, 1, 1.0)
            for p in pts
            if p.cloud_cover_pct is not None
        ]
        cloud_cover_fused, cloud_cover_method = fuse_continuous_parameter_hybrid(
            cloud_cover_contribs, "cloud_cover", max_influence_pct
        )

        cond_val = pts[0].condition if pts else None

        fused_pt = FusedForecastPoint(
            valid_at=valid_at,
            temperature=FusedValue(
                temp_fused, 1.0, None, None, tuple(temp_contribs), temp_method, ()
            ),
            apparent_temperature=FusedValue(
                app_temp_fused, 1.0, None, None, tuple(app_temp_contribs), app_temp_method, ()
            ),
            humidity=FusedValue(
                humidity_fused, 1.0, None, None, tuple(humidity_contribs), humidity_method, ()
            ),
            precipitation_probability=FusedValue(
                prob_pct, 1.0, None, None, tuple(prob_contribs), precip_method, ()
            ),
            precipitation_amount=FusedValue(
                exp_precip, 1.0, None, None, tuple(amount_contribs), precip_method, ()
            ),
            wind_speed=FusedValue(
                wind_speed_fused, 1.0, None, None, tuple(wind_speed_contribs), wind_speed_method, ()
            ),
            wind_gust=FusedValue(
                wind_gust_fused, 1.0, None, None, tuple(wind_gust_contribs), wind_gust_method, ()
            ),
            cloud_cover=FusedValue(
                cloud_cover_fused,
                1.0,
                None,
                None,
                tuple(cloud_cover_contribs),
                cloud_cover_method,
                (),
            ),
            condition=FusedValue(cond_val, 1.0, None, None, (), algorithm, ()),
            overall_confidence=1.0,
        )
        fused_result.append(fused_pt)

    return fused_result
