"""Unit tests for SourceManager."""

from homeassistant.core import SupportsResponse

from custom_components.forecast_fusion.core.enums import ForecastType
from custom_components.forecast_fusion.managers.source_manager import SourceManager


async def test_async_fetch_source_forecast_success(hass):
    """Test successful forecast fetching and health tracking."""
    manager = SourceManager(hass)
    hass.states.async_set("weather.mock", "sunny")

    async def mock_get_forecasts(call):
        return {
            "weather.mock": {
                "forecast": [
                    {
                        "datetime": "2026-07-22T14:00:00+00:00",
                        "temperature": 20.0,
                    }
                ]
            }
        }

    hass.services.async_register(
        "weather",
        "get_forecasts",
        mock_get_forecasts,
        supports_response=SupportsResponse.OPTIONAL,
    )

    snapshot = await manager.async_fetch_source_forecast(
        source_id="src1",
        entity_id="weather.mock",
        forecast_type=ForecastType.HOURLY,
    )

    assert snapshot is not None
    assert snapshot.source_id == "src1"
    assert len(snapshot.points) == 1
    assert snapshot.points[0].temperature_c == 20.0

    health = manager.get_health("src1")
    assert health.available is True
    assert health.consecutive_failures == 0
    assert health.last_success_at is not None


async def test_async_fetch_source_forecast_unavailable_entity(hass):
    """Test skipping service call when entity is unavailable or missing."""
    manager = SourceManager(hass)
    snapshot = await manager.async_fetch_source_forecast(
        source_id="src1",
        entity_id="weather.missing",
    )
    assert snapshot is None
    health = manager.get_health("src1")
    assert health.consecutive_failures == 1
    assert "unavailable" in (health.last_error or "")


async def test_async_fetch_source_forecast_failure(hass):
    """Test error handling and health tracking on failure."""
    manager = SourceManager(hass)
    hass.states.async_set("weather.mock", "sunny")

    async def mock_failing_service(call):
        raise RuntimeError("API error")

    hass.services.async_register(
        "weather",
        "get_forecasts",
        mock_failing_service,
        supports_response=SupportsResponse.OPTIONAL,
    )

    snapshot = await manager.async_fetch_source_forecast(
        source_id="src1",
        entity_id="weather.mock",
    )

    assert snapshot is None
    health = manager.get_health("src1")
    assert health.consecutive_failures == 1
    assert health.last_error == "API error"


async def test_async_fetch_all_sources(hass):
    """Test fetching from multiple sources."""
    manager = SourceManager(hass)
    hass.states.async_set("weather.src1", "sunny")

    async def mock_get_forecasts(call):
        return {
            "weather.src1": {
                "forecast": [{"datetime": "2026-07-22T14:00:00+00:00", "temperature": 20.0}]
            }
        }

    hass.services.async_register(
        "weather",
        "get_forecasts",
        mock_get_forecasts,
        supports_response=SupportsResponse.OPTIONAL,
    )

    sources = [
        {"id": "src1", "entity_id": "weather.src1"},
    ]
    snapshots = await manager.async_fetch_all_sources(sources)

    assert "src1" in snapshots
    assert snapshots["src1"].points[0].temperature_c == 20.0
