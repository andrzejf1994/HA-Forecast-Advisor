"""Unit tests for SQLite repository storage and migrations."""

import os
import tempfile
from datetime import UTC, datetime, timedelta

import pytest

from custom_components.forecast_fusion.core.enums import (
    ForecastType,
    ObservationQuality,
    ObservationSourceMode,
    WeatherParameter,
)
from custom_components.forecast_fusion.core.models import (
    ForecastPoint,
    ForecastSnapshot,
    Observation,
)
from custom_components.forecast_fusion.repositories.sqlite import SQLiteRepository


@pytest.fixture
def db_repo():
    """Create a temporary SQLite repository for testing."""
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = os.path.join(tmpdir, "test_fusion.db")
        repo = SQLiteRepository(db_path)
        yield repo


async def test_sqlite_snapshot_crud(db_repo):
    """Test saving and querying snapshots in SQLite."""
    await db_repo.async_init()
    now = datetime.now(UTC)

    p1 = ForecastPoint(
        source_id="src1",
        forecast_type=ForecastType.HOURLY,
        fetched_at=now,
        issued_at=now - timedelta(hours=1),
        valid_at=now + timedelta(hours=2),
        lead_time=timedelta(hours=3),
        temperature_c=21.5,
        humidity_pct=60.0,
        raw_hash="hash_p1",
    )

    snapshot = ForecastSnapshot(
        snapshot_id="snap1",
        source_id="src1",
        fetched_at=now,
        forecast_type=ForecastType.HOURLY,
        points=(p1,),
        raw_hash="hash_snap1",
    )

    await db_repo.save_snapshot(snapshot)

    results = await db_repo.query_snapshots(source_id="src1")
    assert len(results) == 1
    assert results[0].snapshot_id == "snap1"
    assert len(results[0].points) == 1
    assert results[0].points[0].temperature_c == 21.5


async def test_sqlite_observation_crud(db_repo):
    """Test saving and querying observations."""
    await db_repo.async_init()
    now = datetime.now(UTC)

    obs = Observation(
        observation_id="obs1",
        parameter=WeatherParameter.TEMPERATURE,
        start_at=now - timedelta(hours=1),
        end_at=now,
        value=22.0,
        unit="°C",
        source_mode=ObservationSourceMode.ENTITY,
        source_entity_id="sensor.temp",
        quality=ObservationQuality.MEASURED_PRECISE,
        entered_at=now,
        metadata={"location": "garden"},
    )

    await db_repo.save_observation(obs)

    results = await db_repo.query_observations(parameter="temperature")
    assert len(results) == 1
    assert results[0].observation_id == "obs1"
    assert results[0].value == 22.0
    assert results[0].metadata.get("location") == "garden"
