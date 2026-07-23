"""Unit tests for comfort prediction."""

from datetime import UTC, datetime

from custom_components.forecast_fusion.core.clothing import calculate_outfit_properties
from custom_components.forecast_fusion.core.comfort import predict_discomfort
from custom_components.forecast_fusion.core.enums import ClothingCategory
from custom_components.forecast_fusion.core.models import (
    ClothingItem,
    ContextProfile,
    FusedForecastPoint,
    FusedValue,
)


def test_predict_discomfort_cold_and_rain():
    """Test discomfort prediction for cold and rain."""
    tshirt = ClothingItem("tshirt", "T-Shirt", ClothingCategory.UPPER_BASE, 2.0, 0.0, 0.0, 0.9)
    outfit = calculate_outfit_properties("light", "Light", [tshirt])
    context = ContextProfile("walk", "Walking", cold_penalty=1.5, rain_sensitivity=1.0)

    now = datetime.now(UTC)
    point = FusedForecastPoint(
        valid_at=now,
        temperature=FusedValue(5.0, 0.9, None, None, (), "median", ()),
        apparent_temperature=FusedValue(4.0, 0.9, None, None, (), "median", ()),
        humidity=FusedValue(80.0, 0.9, None, None, (), "median", ()),
        precipitation_probability=FusedValue(90.0, 0.9, None, None, (), "median", ()),
        precipitation_amount=FusedValue(5.0, 0.9, None, None, (), "median", ()),
        wind_speed=FusedValue(2.0, 0.9, None, None, (), "median", ()),
        wind_gust=FusedValue(3.0, 0.9, None, None, (), "median", ()),
        cloud_cover=FusedValue(100.0, 0.9, None, None, (), "median", ()),
        condition=FusedValue("rainy", 0.9, None, None, (), "median", ()),
        overall_confidence=0.9,
    )

    score, reasons = predict_discomfort(point, outfit, context)
    assert score > 0.0
    assert "COLD_RISK" in reasons
    assert "RAIN_UNPROTECTED" in reasons
