"""Personal comfort prediction and discomfort optimization module."""

from .models import ComfortBoundary, ContextProfile, FusedForecastPoint, Outfit


def predict_discomfort(
    point: FusedForecastPoint,
    outfit: Outfit,
    context: ContextProfile,
    boundary: ComfortBoundary | None = None,
) -> tuple[float, list[str]]:
    """Predict expected discomfort score and reason codes for an outfit in given weather.

    Returns:
    (discomfort_score, list_of_reason_codes)
    discomfort_score = 0 is ideal, >0 indicates discomfort.
    """
    reasons: list[str] = []
    discomfort = 0.0

    temp_val = (
        float(point.temperature.value)
        if isinstance(point.temperature.value, (int, float))
        else 20.0
    )
    wind_val = (
        float(point.wind_speed.value) if isinstance(point.wind_speed.value, (int, float)) else 0.0
    )
    precip_val = (
        float(point.precipitation_amount.value)
        if isinstance(point.precipitation_amount.value, (int, float))
        else 0.0
    )

    # Effective temperature felt considering activity heat generation and wind exposure
    effective_temp = (
        temp_val + (context.heat_generation * 3.0) - (wind_val * 0.5 * context.wind_exposure)
    )

    # Defaults if no learned boundary yet
    lower_limit = boundary.lower_temp_c if boundary else 15.0 - outfit.warmth_score
    upper_limit = boundary.upper_temp_c if boundary else 22.0 - (outfit.warmth_score * 0.5)

    if effective_temp < lower_limit:
        cold_diff = lower_limit - effective_temp
        discomfort += cold_diff * context.cold_penalty
        reasons.append("COLD_RISK")

    if effective_temp > upper_limit:
        heat_diff = effective_temp - upper_limit
        discomfort += heat_diff * context.heat_penalty
        reasons.append("HEAT_RISK")

    if precip_val > 0.0 and outfit.rain_protection < 0.5:
        rain_diff = precip_val * context.rain_sensitivity * (1.0 - outfit.rain_protection)
        discomfort += rain_diff * 2.0
        reasons.append("RAIN_UNPROTECTED")

    if wind_val > 8.0 and outfit.wind_protection < 0.5:
        discomfort += (wind_val - 8.0) * 0.8
        reasons.append("WIND_UNPROTECTED")

    return (round(discomfort, 2), reasons)
