"""Unit tests and property tests for weighted median and fusion algorithms."""

from datetime import UTC, datetime

import pytest
from hypothesis import given
from hypothesis import strategies as st

from custom_components.forecast_fusion.core.enums import ForecastType
from custom_components.forecast_fusion.core.fusion import (
    calculate_weighted_median,
    cap_weight_influence,
    check_source_similarity,
    fuse_continuous_parameter_hybrid,
    fuse_forecasts,
    fuse_precipitation_two_stage,
)
from custom_components.forecast_fusion.core.models import ForecastPoint, SourceContribution


def test_weighted_median_basic():
    """Test basic weighted median calculation."""
    # (val, weight)
    pairs = [(10.0, 1.0), (20.0, 1.0), (30.0, 1.0)]
    assert calculate_weighted_median(pairs) == 20.0

    # Dominant weight
    pairs_dom = [(10.0, 1.0), (20.0, 10.0), (30.0, 1.0)]
    assert calculate_weighted_median(pairs_dom) == 20.0


def test_check_source_similarity():
    """Test similarity checking for forecast values."""
    # Values close together (spread <= 1.5)
    assert check_source_similarity([20.0, 20.5, 21.0], threshold=1.5) is True
    # Values divergent (spread > 1.5)
    assert check_source_similarity([20.0, 22.0, 25.0], threshold=1.5) is False


def test_cap_weight_influence():
    """Test capping weight advantage of better source to max 20% over baseline."""
    contribs = [
        SourceContribution("s1", 1.0, 2.0, 20.0, 0.9, 50, 1.0),  # dominant weight 2.0
        SourceContribution("s2", 1.0, 1.0, 22.0, 0.5, 50, 1.0),  # baseline 1.0
    ]
    # Total weight = 3.0, n = 2 -> baseline = 1.5
    # max_allowed = 1.5 * 1.2 = 1.8
    # min_allowed = 1.5 * 0.8 = 1.2
    capped = cap_weight_influence(contribs, max_influence_pct=0.20)
    assert capped[0].effective_weight == pytest.approx(1.8)
    assert capped[1].effective_weight == pytest.approx(1.2)


def test_hybrid_fusion_similar_pattern():
    """Test that when sources show similar patterns, unweighted median is selected."""
    contribs = [
        SourceContribution("s1", 1.0, 5.0, 20.0, 0.9, 50, 1.0),
        SourceContribution("s2", 1.0, 1.0, 21.0, 0.5, 50, 1.0),
    ]
    # Temp spread is 1.0 <= threshold 1.5 -> unweighted median (20.5)
    val, method = fuse_continuous_parameter_hybrid(contribs, parameter_name="temperature")
    assert method == "median_unweighted"
    assert val == 20.5


def test_hybrid_fusion_divergent_pattern():
    """Test that when sources diverge, 20% capped weighted median is selected."""
    contribs = [
        SourceContribution("s1", 1.0, 5.0, 20.0, 0.9, 50, 1.0),
        SourceContribution("s2", 1.0, 1.0, 25.0, 0.5, 50, 1.0),
    ]
    # Temp spread is 5.0 > threshold 1.5 -> weighted median capped
    val, method = fuse_continuous_parameter_hybrid(contribs, parameter_name="temperature")
    assert method == "weighted_median_capped_20"
    assert val is not None


def test_two_stage_precipitation():
    """Test two-stage precipitation fusion."""
    c_prob = [
        SourceContribution("s1", 0.5, 0.5, 80.0, 0.8, 30, 1.0),
        SourceContribution("s2", 0.5, 0.5, 60.0, 0.7, 30, 1.0),
    ]
    c_amount = [
        SourceContribution("s1", 0.5, 0.5, 5.0, 0.8, 30, 1.0),
        SourceContribution("s2", 0.5, 0.5, 3.0, 0.7, 30, 1.0),
    ]

    prob_pct, exp_mm, cond_mm, method = fuse_precipitation_two_stage(c_prob, c_amount)
    assert 60.0 <= prob_pct <= 80.0
    assert 3.0 <= cond_mm <= 5.0
    assert exp_mm > 0.0
    assert method in ("median_unweighted", "weighted_median_capped_20")


def test_fuse_forecasts_hybrid():
    """Test full forecast points fusion with hybrid method tracking."""
    now = datetime.now(UTC)
    pts = [
        ForecastPoint(
            source_id="s1",
            forecast_type=ForecastType.HOURLY,
            fetched_at=now,
            issued_at=now,
            valid_at=now,
            lead_time=st.just(None),
            temperature_c=20.0,
            humidity_pct=50.0,
        ),
        ForecastPoint(
            source_id="s2",
            forecast_type=ForecastType.HOURLY,
            fetched_at=now,
            issued_at=now,
            valid_at=now,
            lead_time=st.just(None),
            temperature_c=20.5,
            humidity_pct=52.0,
        ),
    ]
    fused = fuse_forecasts(pts)
    assert len(fused) == 1
    assert fused[0].temperature.value == 20.25
    assert fused[0].temperature.method == "median_unweighted"


@given(
    values=st.lists(st.floats(min_value=-50.0, max_value=50.0), min_size=1, max_size=10),
    weights=st.lists(st.floats(min_value=0.01, max_value=10.0), min_size=1, max_size=10),
)
def test_property_weighted_median_bounds(values, weights):
    """Property test: weighted median must always be within [min(values), max(values)]."""
    n = min(len(values), len(weights))
    pairs = list(zip(values[:n], weights[:n], strict=False))

    result = calculate_weighted_median(pairs)
    assert result is not None
    assert min(values[:n]) <= result <= max(values[:n])
