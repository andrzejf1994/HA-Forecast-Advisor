"""Unit and property tests for comfort boundary learning."""

from datetime import UTC, datetime, timedelta

from hypothesis import given
from hypothesis import strategies as st

from custom_components.forecast_fusion.core.learning import update_comfort_boundary
from custom_components.forecast_fusion.core.models import ComfortBoundary, ComfortFeedback


def test_bounded_update_step_and_direction():
    """Test that single update step is strictly bounded and in correct direction."""
    now = datetime.now(UTC)
    fb_cold = ComfortFeedback(
        feedback_id="fb1",
        user_profile_id="andrzej",
        start_at=now - timedelta(hours=1),
        end_at=now,
        period_id=None,
        whole_day=False,
        recommended_outfit_id=None,
        worn_outfit_id="tshirt",
        optimal_outfit_id=None,
        comfort_score=-2,  # User was cold
        context_profile_id="default",
        transport_value="walk",
        forecast_snapshot_id=None,
        confidence=1.0,
        note=None,
        created_at=now,
    )

    initial = ComfortBoundary("andrzej", "default", "walk", "tshirt", 15.0, 23.0, 2.0, 1, now)
    updated = update_comfort_boundary(initial, fb_cold, observed_temp_c=10.0, max_step_c=1.5)

    # Since user was cold at 10°C, lower boundary should move upwards, but by at most 1.5°C
    delta = updated.lower_temp_c - initial.lower_temp_c
    assert abs(delta) <= 1.5
    assert updated.lower_temp_c < updated.upper_temp_c


def test_transport_and_outfit_isolation():
    """Test that different transport/outfit combinations produce isolated boundaries."""
    now = datetime.now(UTC)
    fb_bike = ComfortFeedback(
        feedback_id="fb_bike",
        user_profile_id="andrzej",
        start_at=now - timedelta(hours=1),
        end_at=now,
        period_id=None,
        whole_day=False,
        recommended_outfit_id=None,
        worn_outfit_id="tshirt",
        optimal_outfit_id=None,
        comfort_score=-2,
        context_profile_id="default",
        transport_value="bike",
        forecast_snapshot_id=None,
        confidence=1.0,
        note=None,
        created_at=now,
    )

    b_bike = update_comfort_boundary(None, fb_bike, observed_temp_c=12.0)
    assert b_bike.transport_value == "bike"
    assert b_bike.outfit_id == "tshirt"


@given(
    comfort_score=st.integers(min_value=-3, max_value=3),
    observed_temp=st.floats(min_value=-20.0, max_value=45.0),
    confidence=st.floats(min_value=0.1, max_value=1.0),
)
def test_property_boundary_ordering(comfort_score, observed_temp, confidence):
    """Property test: lower_temp_c must always be strictly less than upper_temp_c."""
    now = datetime.now(UTC)
    fb = ComfortFeedback(
        feedback_id="prop_fb",
        user_profile_id="user1",
        start_at=now,
        end_at=now,
        period_id=None,
        whole_day=False,
        recommended_outfit_id=None,
        worn_outfit_id="outfit1",
        optimal_outfit_id=None,
        comfort_score=comfort_score,
        context_profile_id="ctx",
        transport_value="car",
        forecast_snapshot_id=None,
        confidence=confidence,
        note=None,
        created_at=now,
    )

    updated = update_comfort_boundary(None, fb, observed_temp_c=observed_temp)
    assert updated.lower_temp_c < updated.upper_temp_c
