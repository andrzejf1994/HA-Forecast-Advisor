"""Feedback manager for recording comfort feedback and triggering boundary learning."""

import hashlib
import logging
from datetime import UTC, datetime

from ..core.learning import update_comfort_boundary
from ..core.models import ComfortBoundary, ComfortFeedback
from ..core.normalizer import ensure_utc
from ..repositories.sqlite import SQLiteRepository

_LOGGER = logging.getLogger(__name__)


class FeedbackManager:
    """Manager for recording feedback and learning comfort boundaries."""

    def __init__(self, repo: SQLiteRepository) -> None:
        """Initialize FeedbackManager."""
        self.repo = repo
        self.boundaries: dict[str, ComfortBoundary] = {}

    def _make_boundary_key(
        self, user_id: str, context_id: str, transport: str, outfit_id: str
    ) -> str:
        return f"{user_id}_{context_id}_{transport}_{outfit_id}"

    async def record_feedback(
        self,
        user_profile_id: str,
        start_at: datetime,
        end_at: datetime,
        comfort_score: int,
        observed_temp_c: float,
        period_id: str | None = None,
        whole_day: bool = False,
        worn_outfit_id: str | None = None,
        optimal_outfit_id: str | None = None,
        context_profile_id: str | None = None,
        transport_value: str | None = None,
        confidence: float = 1.0,
        note: str | None = None,
    ) -> ComfortFeedback:
        """Record user feedback and update boundary model."""
        start_utc = ensure_utc(start_at) or datetime.now(UTC)
        end_utc = ensure_utc(end_at) or datetime.now(UTC)
        now = datetime.now(UTC)

        raw_id = f"fb_{user_profile_id}_{start_utc.isoformat()}_{comfort_score}"
        fb_id = hashlib.sha256(raw_id.encode("utf-8")).hexdigest()[:16]

        feedback = ComfortFeedback(
            feedback_id=fb_id,
            user_profile_id=user_profile_id,
            start_at=start_utc,
            end_at=end_utc,
            period_id=period_id,
            whole_day=whole_day,
            recommended_outfit_id=None,
            worn_outfit_id=worn_outfit_id,
            optimal_outfit_id=optimal_outfit_id,
            comfort_score=comfort_score,
            context_profile_id=context_profile_id,
            transport_value=transport_value,
            forecast_snapshot_id=None,
            confidence=confidence,
            note=note,
            created_at=now,
        )

        outfit_id = worn_outfit_id or optimal_outfit_id or "default"
        context_id = context_profile_id or "default"
        transport = transport_value or "default"

        key = self._make_boundary_key(user_profile_id, context_id, transport, outfit_id)
        existing = self.boundaries.get(key)

        updated_boundary = update_comfort_boundary(
            existing=existing,
            feedback=feedback,
            observed_temp_c=observed_temp_c,
        )

        self.boundaries[key] = updated_boundary
        _LOGGER.info(
            "Updated comfort boundary for key %s: lower=%.1f, upper=%.1f",
            key,
            updated_boundary.lower_temp_c,
            updated_boundary.upper_temp_c,
        )
        return feedback
