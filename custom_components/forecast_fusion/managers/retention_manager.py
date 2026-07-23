"""Retention manager for purging historic forecast and observation data."""

import logging
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

from ..repositories.sqlite import SQLiteRepository

_LOGGER = logging.getLogger(__name__)


@dataclass
class RetentionSummary:
    """Summary of retention operation results."""

    raw_forecasts_deleted: int = 0
    observations_deleted: int = 0
    verification_results_deleted: int = 0
    dry_run: bool = False


class RetentionManager:
    """Manager for executing batch data retention policies."""

    def __init__(self, repo: SQLiteRepository) -> None:
        """Initialize retention manager with repository."""
        self.repo = repo

    async def async_purge(
        self,
        raw_forecasts_days: int = 90,
        observations_days: int = 365,
        verification_results_days: int = 365,
        dry_run: bool = False,
    ) -> RetentionSummary:
        """Execute data retention purge."""
        now = datetime.now(UTC)
        summary = RetentionSummary(dry_run=dry_run)

        # 0 means keep indefinitely
        if raw_forecasts_days > 0:
            cutoff = now - timedelta(days=raw_forecasts_days)
            if dry_run:
                snapshots = await self.repo.query_snapshots(end_at=cutoff)
                summary.raw_forecasts_deleted = len(snapshots)
            else:
                summary.raw_forecasts_deleted = await self.repo.delete_forecasts_before(cutoff)

        if observations_days > 0:
            cutoff = now - timedelta(days=observations_days)
            if dry_run:
                obs = await self.repo.query_observations(end_at=cutoff)
                summary.observations_deleted = len(obs)
            else:
                summary.observations_deleted = await self.repo.delete_observations_before(cutoff)

        _LOGGER.info(
            "Retention purge completed (dry_run=%s): %s raw forecasts, %s observations deleted",
            dry_run,
            summary.raw_forecasts_deleted,
            summary.observations_deleted,
        )
        return summary
