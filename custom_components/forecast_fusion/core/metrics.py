"""Verification metrics calculation module."""


def calculate_mae(forecast: float, observed: float) -> float:
    """Calculate Mean Absolute Error for a single pair."""
    return abs(forecast - observed)


def calculate_bias(forecast: float, observed: float) -> float:
    """Calculate forecast bias (forecast - observed)."""
    return forecast - observed


def calculate_brier_score(prob_pct: float, occurred: bool) -> float:
    """Calculate Brier score for probability (0..100) vs binary occurrence."""
    p = max(0.0, min(1.0, prob_pct / 100.0))
    o = 1.0 if occurred else 0.0
    return (p - o) ** 2


def calculate_stability_delta(new_forecast: float, prev_forecast: float) -> float:
    """Calculate stability delta between consecutive forecast issues."""
    return abs(new_forecast - prev_forecast)


def calculate_correction_benefit(
    new_forecast: float,
    prev_forecast: float,
    observed: float,
) -> float:
    """Calculate correction benefit of a forecast update relative to observation."""
    prev_err = abs(prev_forecast - observed)
    new_err = abs(new_forecast - observed)
    return prev_err - new_err


def calculate_balanced_accuracy(actuals: list[str], predictions: list[str]) -> float:
    """Calculate balanced accuracy for categorical weather conditions."""
    if not actuals or len(actuals) != len(predictions):
        return 0.0

    categories = set(actuals)
    recalls: list[float] = []

    for cat in categories:
        tp = sum(
            1 for act, pred in zip(actuals, predictions, strict=False) if act == cat and pred == cat
        )
        total_cat = sum(1 for act in actuals if act == cat)
        if total_cat > 0:
            recalls.append(tp / total_cat)

    return sum(recalls) / len(recalls) if recalls else 0.0


def aggregate_continuous_metrics(errors: list[float], biases: list[float]) -> dict[str, float]:
    """Aggregate MAE, Mean Bias, and Error Median from list of errors."""
    if not errors:
        return {"mae": 0.0, "bias": 0.0, "median_error": 0.0}

    mae = sum(abs(e) for e in errors) / len(errors)
    mean_bias = sum(biases) / len(biases) if biases else 0.0

    sorted_errors = sorted(errors)
    n = len(sorted_errors)
    if n % 2 == 1:
        median_err = sorted_errors[n // 2]
    else:
        median_err = (sorted_errors[n // 2 - 1] + sorted_errors[n // 2]) / 2.0

    return {
        "mae": mae,
        "bias": mean_bias,
        "median_error": median_err,
    }
