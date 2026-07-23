"""Unit tests for uncertainty quantification."""

from custom_components.forecast_fusion.core.models import SourceContribution
from custom_components.forecast_fusion.core.uncertainty import (
    build_fused_value,
    calculate_effective_source_count,
)


def test_effective_source_count():
    """Test effective source count calculation."""
    # Equal weights -> N_eff = 3
    assert round(calculate_effective_source_count([0.333, 0.333, 0.333]), 1) == 3.0
    # Dominant weight -> N_eff ~ 1
    assert round(calculate_effective_source_count([0.98, 0.01, 0.01]), 1) == 1.0


def test_build_fused_value_confidence():
    """Test building FusedValue with confidence score."""
    c1 = SourceContribution("s1", 0.5, 0.5, 20.0, 0.9, 30, 1.0)
    c2 = SourceContribution("s2", 0.5, 0.5, 21.0, 0.8, 30, 1.0)

    fused = build_fused_value(20.5, (c1, c2))
    assert fused.value == 20.5
    assert fused.confidence > 0.5
    assert fused.lower_bound == 20.0
    assert fused.upper_bound == 21.0
