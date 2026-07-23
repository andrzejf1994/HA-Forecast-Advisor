"""Repository base protocol interfaces for forecast_fusion data storage."""

from datetime import datetime
from typing import Protocol

from ..core.models import ForecastSnapshot, Observation, VerificationResult


class ForecastRepository(Protocol):
    """Protocol for persisting and querying forecast snapshots."""

    async def save_snapshot(self, snapshot: ForecastSnapshot) -> None:
        """Save a forecast snapshot to storage."""
        ...

    async def query_snapshots(
        self,
        source_id: str | None = None,
        start_at: datetime | None = None,
        end_at: datetime | None = None,
    ) -> list[ForecastSnapshot]:
        """Query forecast snapshots from storage."""
        ...

    async def delete_before(self, before: datetime) -> int:
        """Delete raw forecasts fetched before a given timestamp."""
        ...


class ObservationRepository(Protocol):
    """Protocol for persisting and querying ground truth observations."""

    async def save_observation(self, observation: Observation) -> None:
        """Save an observation to storage."""
        ...

    async def query_observations(
        self,
        parameter: str | None = None,
        start_at: datetime | None = None,
        end_at: datetime | None = None,
    ) -> list[Observation]:
        """Query observations from storage."""
        ...

    async def delete_before(self, before: datetime) -> int:
        """Delete observations recorded before a given timestamp."""
        ...


class VerificationRepository(Protocol):
    """Protocol for persisting verification results."""

    async def save_verification_results(self, results: list[VerificationResult]) -> None:
        """Save verification results to storage."""
        ...

    async def delete_before(self, before: datetime) -> int:
        """Delete verification results older than given timestamp."""
        ...
