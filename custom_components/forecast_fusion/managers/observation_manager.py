"""Observation manager for recording and querying ground truth weather observations."""

import contextlib
import hashlib
import logging
from datetime import UTC, datetime
from typing import Any

from homeassistant.core import HomeAssistant

from ..core.enums import ObservationQuality, ObservationSourceMode, WeatherParameter
from ..core.models import Observation
from ..core.normalizer import ensure_utc
from ..repositories.sqlite import SQLiteRepository

_LOGGER = logging.getLogger(__name__)


class ObservationManager:
    """Manager for recording manual and entity observations."""

    def __init__(self, hass: HomeAssistant, repo: SQLiteRepository) -> None:
        """Initialize observation manager."""
        self.hass = hass
        self.repo = repo

    async def record_manual_observation(
        self,
        parameter: WeatherParameter,
        start_at: datetime,
        end_at: datetime,
        value: float | str | bool,
        quality: ObservationQuality = ObservationQuality.MANUAL_OBSERVATION,
        unit: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> Observation:
        """Record a manual observation (e.g., manual rain report or qualitative assessment)."""
        start_utc = ensure_utc(start_at) or datetime.now(UTC)
        end_utc = ensure_utc(end_at) or datetime.now(UTC)
        now = datetime.now(UTC)

        raw_id_str = (
            f"manual_{parameter.value}_{start_utc.isoformat()}_{end_utc.isoformat()}_{value}"
        )
        obs_id = hashlib.sha256(raw_id_str.encode("utf-8")).hexdigest()[:16]

        obs = Observation(
            observation_id=obs_id,
            parameter=parameter,
            start_at=start_utc,
            end_at=end_utc,
            value=value,
            unit=unit,
            source_mode=ObservationSourceMode.MANUAL,
            source_entity_id=None,
            quality=quality,
            entered_at=now,
            metadata=metadata or {},
        )

        await self.repo.save_observation(obs)
        _LOGGER.info(
            "Recorded manual observation %s for %s (%s..%s): %s",
            obs_id,
            parameter.value,
            start_utc,
            end_utc,
            value,
        )
        return obs

    async def record_entity_observation(
        self,
        parameter: WeatherParameter,
        entity_id: str,
        start_at: datetime,
        end_at: datetime,
        quality: ObservationQuality = ObservationQuality.MEASURED_PRECISE,
    ) -> Observation | None:
        """Record an observation fetched from a Home Assistant entity state."""
        state = self.hass.states.get(entity_id)
        if state is None or state.state in ("unknown", "unavailable"):
            _LOGGER.warning(
                "Entity %s state unavailable for observation parameter %s",
                entity_id,
                parameter.value,
            )
            return None

        raw_str = str(state.state)
        val: float | str | bool = raw_str
        if raw_str.lower() in ("true", "on"):
            val = True
        elif raw_str.lower() in ("false", "off"):
            val = False
        else:
            with contextlib.suppress(ValueError):
                val = float(raw_str)

        unit = state.attributes.get("unit_of_measurement")
        start_utc = ensure_utc(start_at) or datetime.now(UTC)
        end_utc = ensure_utc(end_at) or datetime.now(UTC)
        now = datetime.now(UTC)

        raw_id_str = f"entity_{entity_id}_{parameter.value}_{start_utc.isoformat()}_{val}"
        obs_id = hashlib.sha256(raw_id_str.encode("utf-8")).hexdigest()[:16]

        obs = Observation(
            observation_id=obs_id,
            parameter=parameter,
            start_at=start_utc,
            end_at=end_utc,
            value=val,
            unit=unit,
            source_mode=ObservationSourceMode.ENTITY,
            source_entity_id=entity_id,
            quality=quality,
            entered_at=now,
            metadata={"entity_id": entity_id, "attributes": dict(state.attributes)},
        )

        await self.repo.save_observation(obs)
        return obs
