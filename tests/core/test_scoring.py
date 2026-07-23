"""Unit tests for scoring module."""

from custom_components.forecast_fusion.core.enums import SampleStatus
from custom_components.forecast_fusion.core.scoring import (
    calculate_effective_source_weight,
    calculate_raw_accuracy_score,
    calculate_sample_confidence,
    get_sample_status,
    normalize_weights,
)


def test_calculate_sample_confidence_and_status():
    """Test sample count shrinkage and status classification."""
    assert calculate_sample_confidence(0) == 0.0
    assert calculate_sample_confidence(15) == 0.5
    assert calculate_sample_confidence(30) == 1.0
    assert calculate_sample_confidence(50) == 1.0

    assert get_sample_status(5) == SampleStatus.INSUFFICIENT_DATA
    assert get_sample_status(15) == SampleStatus.PROVISIONAL
    assert get_sample_status(35) == SampleStatus.ESTABLISHED


def test_calculate_raw_accuracy_score():
    """Test raw accuracy score calculation."""
    assert round(calculate_raw_accuracy_score(0.0), 2) == 1.0
    assert round(calculate_raw_accuracy_score(3.0), 2) == 0.37
    assert calculate_raw_accuracy_score(None, brier_score=0.0) == 1.0
    assert calculate_raw_accuracy_score(None, brier_score=1.0) == 0.01


def test_calculate_effective_source_weight_unhealthy():
    """Test that unhealthy source receives 0 weight."""
    w = calculate_effective_source_weight(1.0, mae=0.5, is_healthy=False)
    assert w == 0.0


def test_normalize_weights():
    """Test weight normalization."""
    weights = {"s1": 2.0, "s2": 3.0, "s3": 5.0}
    norm = normalize_weights(weights)
    assert norm["s1"] == 0.2
    assert norm["s2"] == 0.3
    assert norm["s3"] == 0.5
