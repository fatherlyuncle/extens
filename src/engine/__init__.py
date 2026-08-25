"""
Deck-cost engine: UI-independent core for the Moxfield deck-cost tool.

Public API:

    from engine import calculate_deck_cost
    result = calculate_deck_cost(collection, normalized_deck, raw_deck,
                                  pricing_strategy="cheapest")

See engine.py for the full calculate_deck_cost() docstring, including
two deliberate deviations from the originally sketched signature.
"""

from .engine import calculate_deck_cost
from .models import CardRequirement, DeckCostResult, MatchResult, PriceSelection

__all__ = [
    "calculate_deck_cost",
    "CardRequirement",
    "MatchResult",
    "PriceSelection",
    "DeckCostResult",
]
