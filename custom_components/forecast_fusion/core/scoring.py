"""Source scoring and weight calculation module."""

import math

from .enums import SampleStatus


def calculate_sample_confidence(sample_count: int, established_threshold: int = 30) -> float:
    """Calculate sample confidence factor (0..1) based on sample count shrinkage."""
    if sample_count <= 0:
        return 0.0
    return min(1.0, sample_count / float(established_threshold))


def get_sample_status(sample_count: int) -> SampleStatus:
    """Categorize sample status based on sample count."""
    if sample_count < 10:
        return SampleStatus.INSUFFICIENT_DATA
    if sample_count < 30:
        return SampleStatus.PROVISIONAL
    return SampleStatus.ESTABLISHED


def calculate_raw_accuracy_score(
    mae: float | None,
    brier_score: float | None = None,
    temperature_scale: float = 3.0,
) -> float:
    """Calculate raw accuracy score in range (0..1] based on error metric."""
    if brier_score is not None:
        # Brier score is 0 (best) to 1 (worst)
        return max(0.01, 1.0 - min(1.0, brier_score))

    if mae is None:
        return 0.5  # Neutral default when no error data exists

    # Exponential decay score for continuous error
    return math.exp(-max(0.0, mae) / temperature_scale)


def calculate_effective_source_weight(
    initial_weight: float,
    mae: float | None = None,
    brier_score: float | None = None,
    sample_count: int = 0,
    freshness: float = 1.0,  # 1.0 newest, decreases with age
    is_healthy: bool = True,
    established_threshold: int = 30,
) -> float:
    """Calculate unnormalized effective weight for a single source."""
    if not is_healthy:
        return 0.0

    sample_conf = calculate_sample_confidence(sample_count, established_threshold)
    accuracy_score = calculate_raw_accuracy_score(mae, brier_score)

    # Shrinkage towards initial user weight for small samples
    learned_weight = (1.0 - sample_conf) * initial_weight + sample_conf * accuracy_score

    effective = learned_weight * max(0.0, min(1.0, freshness))
    return max(0.0, effective)


def normalize_weights(source_weights: dict[str, float]) -> dict[str, float]:
    """Normalize a dictionary of source weights so their sum equals 1.0."""
    total = sum(source_weights.values())
    if total <= 0.0:
        n = len(source_weights)
        if n == 0:
            return {}
        equal_weight = 1.0 / n
        return dict.fromkeys(source_weights, equal_weight)

    return {k: v / total for k, v in source_weights.items()}
