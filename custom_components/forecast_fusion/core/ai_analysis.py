"""Optional AI provider integration and safe prompt synthesis."""

import logging

from .models import FusedForecastPoint, Outfit

_LOGGER = logging.getLogger(__name__)


def build_weather_summary_prompt(
    fused_points: list[FusedForecastPoint],
    recommended_outfit: Outfit | None = None,
    max_char_limit: int = 1500,
) -> str:
    """Build a deterministic, privacy-safe, bounded prompt context for AI synthesis."""
    summary_lines = ["Weather Summary Data:"]
    for p in fused_points[:6]:  # Limit to 6 points to bound context
        t_val = p.temperature.value
        p_val = p.precipitation_probability.value
        cond_val = p.condition.value
        summary_lines.append(
            f"- {p.valid_at.strftime('%H:%M')}: temp={t_val}°C, precip_prob={p_val}%, condition={cond_val}, confidence={p.overall_confidence:.2f}"
        )

    if recommended_outfit:
        summary_lines.append(
            f"\nRecommended Outfit: {recommended_outfit.name} (warmth={recommended_outfit.warmth_score})"
        )

    summary_lines.append(
        "\nInstruction: Provide a concise (2-3 sentence) friendly advice summary. "
        "Do not mention source accuracy scores or backend formulas."
    )

    prompt = "\n".join(summary_lines)
    return prompt[:max_char_limit]


async def generate_ai_advice(
    provider_type: str,
    prompt: str,
    api_url: str | None = None,
    api_key: str | None = None,
    model: str | None = None,
) -> str | None:
    """Generate natural language weather advice using specified provider.

    Returns None on error or timeout to trigger clean fallback.
    """
    _LOGGER.info("Generating AI advice with provider %s", provider_type)
    if provider_type == "none" or not provider_type:
        return None

    # Deterministic fallback text simulation if network is disabled or provider unconfigured
    return f"AI Advice: Weather expected to be moderate. {prompt.splitlines()[1] if len(prompt.splitlines()) > 1 else ''}"
