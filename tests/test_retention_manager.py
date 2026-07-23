"""Unit tests for RetentionManager."""

import os
import tempfile
from datetime import UTC, datetime, timedelta

from custom_components.forecast_fusion.core.enums import ForecastType
from custom_components.forecast_fusion.core.models import ForecastPoint, ForecastSnapshot
from custom_components.forecast_fusion.managers.retention_manager import RetentionManager
from custom_components.forecast_fusion.repositories.sqlite import SQLiteRepository


async def test_retention_manager_purge():
    """Test purging old forecasts via retention manager."""
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = os.path.join(tmpdir, "retention_test.db")
        repo = SQLiteRepository(db_path)
        await repo.async_init()

        now = datetime.now(UTC)
        old_time = now - timedelta(days=100)

        p_old = ForecastPoint(
            source_id="src1",
            forecast_type=ForecastType.HOURLY,
            fetched_at=old_time,
            issued_at=old_time,
            valid_at=old_time + timedelta(hours=1),
            lead_time=timedelta(hours=1),
            temperature_c=15.0,
            raw_hash="hash_old",
        )

        snap_old = ForecastSnapshot(
            snapshot_id="snap_old",
            source_id="src1",
            fetched_at=old_time,
            forecast_type=ForecastType.HOURLY,
            points=(p_old,),
            raw_hash="hash_snap_old",
        )

        await repo.save_snapshot(snap_old)

        retention = RetentionManager(repo)

        # Dry run test
        summary_dry = await retention.async_purge(raw_forecasts_days=90, dry_run=True)
        assert summary_dry.raw_forecasts_deleted == 1

        # Real purge
        summary_real = await retention.async_purge(raw_forecasts_days=90, dry_run=False)
        assert summary_real.raw_forecasts_deleted == 1

        snapshots_left = await repo.query_snapshots()
        assert len(snapshots_left) == 0
