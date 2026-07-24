"""Unit tests for apparent and perceived temperature calculations."""

from custom_components.forecast_fusion.core.apparent_temp import (
    calculate_australian_apparent_temp,
    calculate_humidex,
    calculate_perceived_temperature,
    calculate_vapor_pressure,
    calculate_wind_chill,
)


def test_vapor_pressure():
    """Test water vapor pressure calculation."""
    vp = calculate_vapor_pressure(20.0, 50.0)
    assert 11.0 < vp < 12.0


def test_australian_apparent_temp():
    """Test Steadman Australian Apparent Temperature formula."""
    at = calculate_australian_apparent_temp(20.0, 50.0, 2.0)
    assert 15.0 < at < 25.0


def test_humidex():
    """Test Canadian Humidex calculation."""
    hx = calculate_humidex(30.0, 80.0)
    assert hx > 30.0


def test_wind_chill():
    """Test Environment Canada Wind Chill calculation."""
    wc = calculate_wind_chill(0.0, 20.0)
    assert wc < 0.0

    # No wind chill for warm temp
    wc_warm = calculate_wind_chill(20.0, 20.0)
    assert wc_warm == 20.0


def test_perceived_temperature_unified():
    """Test unified perceived temperature calculation across different regimes."""
    # Cold regime -> wind chill
    p_cold = calculate_perceived_temperature(2.0, 70.0, 5.0)  # ~18 km/h wind
    assert p_cold < 2.0

    # Hot regime -> humidex
    p_hot = calculate_perceived_temperature(32.0, 75.0, 1.0)
    assert p_hot > 32.0

    # Mild regime -> Australian apparent temp
    p_mild = calculate_perceived_temperature(18.0, 60.0, 2.0)
    assert 10.0 < p_mild < 25.0
