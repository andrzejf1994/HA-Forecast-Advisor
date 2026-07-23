"""Unit tests for ObservationManager."""

import os
import tempfile
from datetime import UTC, datetime, timedelta

from custom_components.forecast_fusion.core.enums import (
    ObservationQuality,
    WeatherParameter,
)
from custom_components.forecast_fusion.managers.observation_manager import ObservationManager
from custom_components.forecast_fusion.repositories.sqlite import SQLiteRepository


async def test_record_manual_observation(hass):
    """Test recording a manual observation including categorical rain."""
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = os.path.join(tmpdir, "obs_test.db")
        repo = SQLiteRepository(db_path)
        await repo.async_init()

        manager = ObservationManager(hass, repo)
        now = datetime.now(UTC)

        obs = await manager.record_manual_observation(
            parameter=WeatherParameter.PRECIPITATION,
            start_at=now - timedelta(hours=1),
            end_at=now,
            value="heavy",
            quality=ObservationQuality.MANUAL_OBSERVATION,
        )

        assert obs is not None
        assert obs.value == "heavy"
        assert obs.quality == ObservationQuality.MANUAL_OBSERVATION

        db_obs = await repo.query_observations(parameter="precipitation")
        assert len(db_obs) == 1
        assert db_obs[0].value == "heavy"


async def test_record_entity_observation(hass):
    """Test recording observation from HA entity state."""
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = os.path.join(tmpdir, "obs_test.db")
        repo = SQLiteRepository(db_path)
        await repo.async_init()

        manager = ObservationManager(hass, repo)

        hass.states.async_set("sensor.outdoor_temp", "21.5", {"unit_of_measurement": "°C"})

        now = datetime.now(UTC)
        obs = await manager.record_entity_observation(
            parameter=WeatherParameter.TEMPERATURE,
            entity_id="sensor.outdoor_temp",
            start_at=now - timedelta(minutes=30),
            end_at=now,
        )

        assert obs is not None
        assert obs.value == 21.5
        assert obs.unit == "°C"
