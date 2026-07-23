"""Unit tests and property tests for weighted median and fusion algorithms."""

from hypothesis import given
from hypothesis import strategies as st

from custom_components.forecast_fusion.core.fusion import (
    calculate_weighted_median,
    fuse_precipitation_two_stage,
)
from custom_components.forecast_fusion.core.models import SourceContribution


def test_weighted_median_basic():
    """Test basic weighted median calculation."""
    # (val, weight)
    pairs = [(10.0, 1.0), (20.0, 1.0), (30.0, 1.0)]
    assert calculate_weighted_median(pairs) == 20.0

    # Dominant weight
    pairs_dom = [(10.0, 1.0), (20.0, 10.0), (30.0, 1.0)]
    assert calculate_weighted_median(pairs_dom) == 20.0


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

    prob_pct, exp_mm, cond_mm = fuse_precipitation_two_stage(c_prob, c_amount)
    assert 60.0 <= prob_pct <= 80.0
    assert 3.0 <= cond_mm <= 5.0
    assert exp_mm > 0.0


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
