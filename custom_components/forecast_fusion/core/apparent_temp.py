"""Apparent and Perceived Temperature thermodynamic calculations."""

import math


def calculate_vapor_pressure(temp_c: float, humidity_pct: float) -> float:
    """Calculate water vapor pressure (e) in hPa using Magnus formula."""
    safe_humidity = max(0.0, min(100.0, humidity_pct))
    return (safe_humidity / 100.0) * 6.105 * math.exp((17.27 * temp_c) / (237.7 + temp_c))


def calculate_australian_apparent_temp(
    temp_c: float, humidity_pct: float, wind_speed_ms: float = 0.0
) -> float:
    """Calculate Australian Apparent Temperature (Steadman formula).

    Formula: AT = T + 0.33 * e - 0.70 * v - 4.00
    where e is vapor pressure in hPa and v is wind speed in m/s.
    """
    e = calculate_vapor_pressure(temp_c, humidity_pct)
    at = temp_c + (0.33 * e) - (0.70 * wind_speed_ms) - 4.00
    return round(at, 1)


def calculate_humidex(temp_c: float, humidity_pct: float) -> float:
    """Calculate Canadian Humidex index for heat discomfort."""
    e = calculate_vapor_pressure(temp_c, humidity_pct)
    humidex = temp_c + (5.0 / 9.0) * (e - 10.0)
    return round(max(temp_c, humidex), 1)


def calculate_wind_chill(temp_c: float, wind_speed_kmh: float) -> float:
    """Calculate Environment Canada / NWS Wind Chill index (°C)."""
    if temp_c > 10.0 or wind_speed_kmh <= 4.8:
        return temp_c
    v_pow = math.pow(wind_speed_kmh, 0.16)
    wc = 13.12 + (0.6215 * temp_c) - (11.37 * v_pow) + (0.3965 * temp_c * v_pow)
    return round(wc, 1)


def calculate_perceived_temperature(
    temp_c: float,
    humidity_pct: float = 50.0,
    wind_speed_ms: float = 0.0,
) -> float:
    """Calculate unified perceived temperature based on ambient conditions.

    Uses Wind Chill for cold & windy conditions, Humidex for hot & humid conditions,
    and Australian Apparent Temperature (Steadman) for normal conditions.
    """
    wind_kmh = wind_speed_ms * 3.6
    if temp_c <= 10.0 and wind_kmh > 4.8:
        return calculate_wind_chill(temp_c, wind_kmh)
    if temp_c >= 27.0:
        return calculate_humidex(temp_c, humidity_pct)
    return calculate_australian_apparent_temp(temp_c, humidity_pct, wind_speed_ms)


def get_thermal_perception(perceived_temp_c: float) -> str:
    """Return human-readable thermal perception category based on perceived temperature (°C)."""
    if perceived_temp_c < -10.0:
        return "Ekstremalne zimno"
    if perceived_temp_c < 0.0:
        return "Bardzo zimno"
    if perceived_temp_c < 10.0:
        return "Chłodno"
    if perceived_temp_c < 16.0:
        return "Lekki chłód"
    if perceived_temp_c <= 24.0:
        return "Komfortowo"
    if perceived_temp_c <= 28.0:
        return "Ciepło"
    if perceived_temp_c <= 32.0:
        return "Gorąco / Parno"
    return "Ekstremalny upał"
