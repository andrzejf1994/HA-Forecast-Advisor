"""Unit tests for clothing catalog and outfit rating calculations."""

from custom_components.forecast_fusion.core.clothing import calculate_outfit_properties
from custom_components.forecast_fusion.core.enums import ClothingCategory
from custom_components.forecast_fusion.core.models import ClothingItem


def test_calculate_outfit_properties():
    """Test outfit thermal property calculations."""
    tshirt = ClothingItem("tshirt", "T-Shirt", ClothingCategory.UPPER_BASE, 2.0, 0.0, 0.0, 0.9)
    hoodie = ClothingItem("hoodie", "Hoodie", ClothingCategory.UPPER_MID, 4.0, 0.2, 0.1, 0.7)

    outfit = calculate_outfit_properties("casual", "Casual Outfit", [tshirt, hoodie])

    assert outfit.outfit_id == "casual"
    assert outfit.warmth_score == 6.0
    assert outfit.layer_count == 2
    assert outfit.wind_protection == 0.2
    assert outfit.rain_protection == 0.1
