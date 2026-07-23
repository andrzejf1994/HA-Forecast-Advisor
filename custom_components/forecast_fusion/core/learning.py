"""Personal comfort boundary learning module."""

from datetime import UTC, datetime

from .models import ComfortBoundary, ComfortFeedback


def update_comfort_boundary(
    existing: ComfortBoundary | None,
    feedback: ComfortFeedback,
    observed_temp_c: float,
    base_alpha: float = 0.2,
    max_step_c: float = 1.5,
) -> ComfortBoundary:
    """Update comfort boundary for a specific user x context x transport x outfit model.

    Enforces:
    - Bounded single update step (max_step_c).
    - Isolation per user, context, transport, and outfit.
    - Ordered lower and upper boundaries.
    """
    now = datetime.now(UTC)
    user_id = feedback.user_profile_id
    context_id = feedback.context_profile_id or "default"
    transport = feedback.transport_value or "default"
    outfit_id = feedback.worn_outfit_id or feedback.optimal_outfit_id or "default"

    if existing is None:
        # Default initial boundary
        lower = 15.0
        upper = 23.0
        uncertainty = 3.0
        sample_count = 0
    else:
        lower = existing.lower_temp_c
        upper = existing.upper_temp_c
        uncertainty = existing.uncertainty
        sample_count = existing.sample_count

    # Calculate effective learning rate (alpha)
    weight = (
        1.0 if not feedback.whole_day else 0.5
    )  # Range feedback has higher weight than whole-day
    alpha = base_alpha * max(0.1, min(1.0, feedback.confidence)) * weight

    # Comfort score: -3 (too cold) .. +3 (too hot), 0 optimal
    c_score = feedback.comfort_score

    if c_score < 0:
        # User was cold: current lower bound was too low for this outfit -> raise lower bound
        target = observed_temp_c
        step = (target - lower) * alpha
        # Bound step to max_step_c
        bounded_step = max(-max_step_c, min(max_step_c, step))
        lower += bounded_step

    elif c_score > 0:
        # User was hot: current upper bound was too high for this outfit -> lower upper bound
        target = observed_temp_c
        step = (target - upper) * alpha
        bounded_step = max(-max_step_c, min(max_step_c, step))
        upper += bounded_step

    else:
        # Comfortable: reduce uncertainty
        uncertainty = max(0.5, uncertainty * 0.9)

    # Ensure lower < upper
    if lower >= upper:
        upper = lower + 1.0

    return ComfortBoundary(
        user_profile_id=user_id,
        context_profile_id=context_id,
        transport_value=transport,
        outfit_id=outfit_id,
        lower_temp_c=round(lower, 2),
        upper_temp_c=round(upper, 2),
        uncertainty=round(uncertainty, 2),
        sample_count=sample_count + 1,
        last_updated=now,
    )
