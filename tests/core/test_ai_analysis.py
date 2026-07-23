"""Unit tests for AI analysis prompt synthesis and fallback."""

from datetime import UTC, datetime

from custom_components.forecast_fusion.core.ai_analysis import (
    build_weather_summary_prompt,
    generate_ai_advice,
)
from custom_components.forecast_fusion.core.models import FusedForecastPoint, FusedValue


def test_build_weather_summary_prompt():
    """Test prompt building with character bounding."""
    now = datetime.now(UTC)
    p1 = FusedForecastPoint(
        valid_at=now,
        temperature=FusedValue(20.0, 0.9, None, None, (), "median", ()),
        apparent_temperature=FusedValue(20.0, 0.9, None, None, (), "median", ()),
        humidity=FusedValue(50.0, 0.9, None, None, (), "median", ()),
        precipitation_probability=FusedValue(10.0, 0.9, None, None, (), "median", ()),
        precipitation_amount=FusedValue(0.0, 0.9, None, None, (), "median", ()),
        wind_speed=FusedValue(3.0, 0.9, None, None, (), "median", ()),
        wind_gust=FusedValue(4.0, 0.9, None, None, (), "median", ()),
        cloud_cover=FusedValue(10.0, 0.9, None, None, (), "median", ()),
        condition=FusedValue("sunny", 0.9, None, None, (), "median", ()),
        overall_confidence=0.9,
    )

    prompt = build_weather_summary_prompt([p1], max_char_limit=100)
    assert len(prompt) <= 100
    assert "Weather" in prompt


async def test_generate_ai_advice_none_fallback():
    """Test clean fallback when provider is none."""
    advice = await generate_ai_advice("none", "Test prompt")
    assert advice is None
