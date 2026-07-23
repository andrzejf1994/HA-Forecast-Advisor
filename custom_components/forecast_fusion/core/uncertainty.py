"""Uncertainty quantification and confidence scoring module."""

import math

from .models import FusedValue, SourceContribution


def calculate_effective_source_count(weights: list[float]) -> float:
    """Calculate effective number of sources N_eff = 1 / sum(w_i^2)."""
    valid = [w for w in weights if w > 0.0]
    if not valid:
        return 0.0

    total = sum(valid)
    norm_w = [w / total for w in valid]
    sum_sq = sum(w * w for w in norm_w)
    if sum_sq <= 0:
        return 0.0

    return 1.0 / sum_sq


def calculate_source_variance(
    contributions: list[SourceContribution],
    fused_value: float | None,
) -> float:
    """Calculate weighted variance among source values."""
    if fused_value is None:
        return 0.0

    valid_items = [
        (float(c.raw_value), c.effective_weight)
        for c in contributions
        if isinstance(c.raw_value, (int, float)) and c.effective_weight > 0
    ]

    if not valid_items:
        return 0.0

    total_weight = sum(w for _, w in valid_items)
    if total_weight <= 0:
        return 0.0

    weighted_sq_diff = sum(w * ((v - fused_value) ** 2) for v, w in valid_items)
    return weighted_sq_diff / total_weight


def build_fused_value(
    fused_val: float | str | bool | None,
    contributions: tuple[SourceContribution, ...],
    method: str = "weighted_median",
) -> FusedValue:
    """Build FusedValue with confidence score, bounds, and reason codes."""
    if fused_val is None:
        return FusedValue(
            value=None,
            confidence=0.0,
            lower_bound=None,
            upper_bound=None,
            contributing_sources=contributions,
            method=method,
            reason_codes=("NO_AVAILABLE_SOURCES",),
        )

    reasons: list[str] = []
    valid_numeric = [
        (float(c.raw_value), c.effective_weight)
        for c in contributions
        if isinstance(c.raw_value, (int, float))
    ]

    n_sources = len(valid_numeric)
    if n_sources == 0:
        return FusedValue(
            value=fused_val,
            confidence=0.0,
            lower_bound=None,
            upper_bound=None,
            contributing_sources=contributions,
            method=method,
            reason_codes=("NO_NUMERIC_SOURCES",),
        )

    weights = [w for _, w in valid_numeric]
    n_eff = calculate_effective_source_count(weights)

    if n_sources < 2:
        reasons.append("SINGLE_SOURCE_ONLY")
    elif n_eff < 1.5:
        reasons.append("LOW_EFFECTIVE_SOURCE_COUNT")

    std_dev = 0.0
    lower_bound: float | None = None
    upper_bound: float | None = None

    if isinstance(fused_val, (int, float)):
        f_num = float(fused_val)
        variance = calculate_source_variance(list(contributions), f_num)
        std_dev = math.sqrt(variance)

        vals = [v for v, _ in valid_numeric]
        lower_bound = min(vals)
        upper_bound = max(vals)

        if std_dev > 3.0:
            reasons.append("HIGH_SOURCE_DISAGREEMENT")

    # Base confidence from effective source count and agreement
    source_conf = min(1.0, n_eff / 3.0)
    agreement_conf = math.exp(-std_dev / 5.0) if isinstance(fused_val, (int, float)) else 1.0
    overall_conf = max(0.0, min(1.0, 0.6 * source_conf + 0.4 * agreement_conf))

    return FusedValue(
        value=fused_val,
        confidence=round(overall_conf, 3),
        lower_bound=lower_bound,
        upper_bound=upper_bound,
        contributing_sources=contributions,
        method=method,
        reason_codes=tuple(reasons),
    )
