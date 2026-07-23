"""Source manager for fetching weather forecasts via weather.get_forecasts action."""

import logging
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any

from homeassistant.core import HomeAssistant

from ..core.enums import ForecastType
from ..core.models import ForecastSnapshot
from ..core.normalizer import normalize_forecast_snapshot

_LOGGER = logging.getLogger(__name__)


@dataclass
class SourceHealth:
    """Tracks health metrics for a weather forecast source."""

    source_id: str
    entity_id: str
    available: bool = True
    consecutive_failures: int = 0
    last_success_at: datetime | None = None
    last_error: str | None = None


class SourceManager:
    """Manager responsible for fetching, normalizing, and deduplicating weather forecasts."""

    def __init__(self, hass: HomeAssistant) -> None:
        """Initialize the SourceManager."""
        self.hass = hass
        self.health_records: dict[str, SourceHealth] = {}
        self.last_snapshots: dict[str, ForecastSnapshot] = {}

    def get_health(self, source_id: str) -> SourceHealth:
        """Get or initialize health record for source."""
        if source_id not in self.health_records:
            self.health_records[source_id] = SourceHealth(
                source_id=source_id,
                entity_id=source_id,
            )
        return self.health_records[source_id]

    async def async_fetch_source_forecast(
        self,
        source_id: str,
        entity_id: str,
        forecast_type: ForecastType = ForecastType.HOURLY,
    ) -> ForecastSnapshot | None:
        """Fetch forecast from a single weather entity via weather.get_forecasts."""
        health = self.get_health(source_id)
        health.entity_id = entity_id
        now = datetime.now(UTC)

        try:
            response = await self.hass.services.async_call(
                "weather",
                "get_forecasts",
                service_data={"type": forecast_type.value},
                target={"entity_id": entity_id},
                blocking=True,
                return_response=True,
            )

            if not isinstance(response, dict) or entity_id not in response:
                raise ValueError(f"No valid forecast response for entity {entity_id}")

            entity_data = response[entity_id]
            if not isinstance(entity_data, dict):
                raise ValueError(f"Invalid payload returned for entity {entity_id}")

            raw_list = entity_data.get("forecast", [])
            if not isinstance(raw_list, list) or not raw_list:
                raise ValueError(f"Empty forecast returned for entity {entity_id}")

            raw_forecast: list[dict[str, Any]] = [x for x in raw_list if isinstance(x, dict)]
            if not raw_forecast:
                raise ValueError(f"No valid forecast items for entity {entity_id}")

            snapshot = normalize_forecast_snapshot(
                source_id=source_id,
                forecast_type=forecast_type,
                fetched_at=now,
                raw_points=raw_forecast,
            )

            if snapshot is None:
                raise ValueError(f"Failed to normalize forecast for {entity_id}")

            # Deduplication check
            prev_snapshot = self.last_snapshots.get(source_id)
            if prev_snapshot is not None and prev_snapshot.raw_hash == snapshot.raw_hash:
                _LOGGER.debug("Deduplicated identical snapshot for source %s", source_id)
                health.last_success_at = now
                health.consecutive_failures = 0
                health.available = True
                health.last_error = None
                return prev_snapshot

            self.last_snapshots[source_id] = snapshot
            health.last_success_at = now
            health.consecutive_failures = 0
            health.available = True
            health.last_error = None
            return snapshot

        except Exception as err:
            health.consecutive_failures += 1
            health.last_error = str(err)
            if health.consecutive_failures >= 3:
                health.available = False
            _LOGGER.warning(
                "Failed to fetch forecast from %s (%s): %s",
                source_id,
                entity_id,
                err,
            )
            return None

    async def async_fetch_all_sources(
        self,
        sources: list[dict[str, Any]],
    ) -> dict[str, ForecastSnapshot]:
        """Fetch forecasts from all configured sources."""
        snapshots: dict[str, ForecastSnapshot] = {}

        for src in sources:
            source_id = str(src.get("id") or src.get("entity_id", ""))
            entity_id = str(src.get("entity_id", ""))
            if not entity_id:
                continue

            snapshot = await self.async_fetch_source_forecast(
                source_id=source_id,
                entity_id=entity_id,
            )
            if snapshot is not None:
                snapshots[source_id] = snapshot

        return snapshots
