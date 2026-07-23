"""Unit tests for verification metrics."""

from custom_components.forecast_fusion.core.metrics import (
    aggregate_continuous_metrics,
    calculate_balanced_accuracy,
    calculate_bias,
    calculate_brier_score,
    calculate_correction_benefit,
    calculate_mae,
    calculate_stability_delta,
)


def test_calculate_mae():
    """Test MAE calculation."""
    assert calculate_mae(25.0, 20.0) == 5.0
    assert calculate_mae(18.0, 22.0) == 4.0


def test_calculate_bias():
    """Test bias calculation."""
    assert calculate_bias(25.0, 20.0) == 5.0
    assert calculate_bias(18.0, 22.0) == -4.0


def test_calculate_brier_score():
    """Test Brier score for probability vs binary event."""
    assert calculate_brier_score(100.0, True) == 0.0
    assert calculate_brier_score(0.0, True) == 1.0
    assert calculate_brier_score(50.0, True) == 0.25
    assert calculate_brier_score(0.0, False) == 0.0


def test_calculate_stability_and_benefit():
    """Test stability delta and correction benefit."""
    # Previous forecast: 20, new forecast: 22, observed: 23
    # Prev error: 3, new error: 1 => benefit: +2
    assert calculate_stability_delta(22.0, 20.0) == 2.0
    assert calculate_correction_benefit(22.0, 20.0, 23.0) == 2.0


def test_calculate_balanced_accuracy():
    """Test balanced accuracy for condition strings."""
    actuals = ["sunny", "sunny", "rainy", "cloudy"]
    preds = ["sunny", "cloudy", "rainy", "cloudy"]
    # sunny: 1/2 = 0.5, rainy: 1/1 = 1.0, cloudy: 1/1 = 1.0 => avg = 2.5/3 = ~0.833
    acc = calculate_balanced_accuracy(actuals, preds)
    assert round(acc, 2) == 0.83


def test_aggregate_continuous_metrics():
    """Test aggregation of errors."""
    errors = [2.0, -1.0, 3.0]
    biases = [2.0, -1.0, 3.0]
    agg = aggregate_continuous_metrics(errors, biases)
    assert agg["mae"] == 2.0
    assert round(agg["bias"], 2) == 1.33
    assert agg["median_error"] == 2.0
