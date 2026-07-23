"""Clothing catalog and outfit rating calculations module."""

from .models import ClothingItem, Outfit


def calculate_outfit_properties(
    outfit_id: str,
    name: str,
    items: list[ClothingItem],
    adjustable: bool = True,
    allowed_contexts: tuple[str, ...] = (),
) -> Outfit:
    """Calculate aggregated thermal and protective ratings for an outfit from its items."""
    active_items = [item for item in items if item.active]

    warmth = sum(item.warmth_score for item in active_items)
    wind_prot = min(1.0, sum(item.wind_protection for item in active_items))
    rain_prot = min(1.0, sum(item.rain_protection for item in active_items))
    breathability = (
        sum(item.breathability for item in active_items) / len(active_items)
        if active_items
        else 1.0
    )
    layer_count = len(active_items)

    item_ids = tuple(item.item_id for item in active_items)

    return Outfit(
        outfit_id=outfit_id,
        name=name,
        item_ids=item_ids,
        warmth_score=warmth,
        wind_protection=wind_prot,
        rain_protection=rain_prot,
        breathability=breathability,
        layer_count=layer_count,
        adjustable=adjustable,
        active=True,
        allowed_contexts=allowed_contexts,
    )
