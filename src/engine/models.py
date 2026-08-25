"""
Public/domain dataclasses for the deck-cost engine.

These are the types that cross the engine boundary. Everything internal
to a single module (e.g. per-card match dicts inside matching.py) stays
a plain dict on purpose -- we only promote something to a dataclass here
if it's part of the contract that callers (tests, the eventual browser
integration) actually depend on.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from decimal import Decimal


@dataclass
class CardRequirement:
    """A single card the deck needs, at a given quantity."""

    name: str
    quantity: int
    board: str  # "commander" or "mainboard"
    finish: str = "nonFoil"
    scryfall_id: str | None = None


@dataclass
class MatchResult:
    """Deck-level summary of how many required cards are owned vs. missing."""

    required: int
    owned: int
    missing: int


@dataclass
class PriceSelection:
    """The printing/treatment chosen to price a single missing card line."""

    card_name: str
    set_code: str
    collector_number: str
    finish: str
    price_field: str
    unit_price: Decimal
    quantity: int
    line_total: Decimal


@dataclass
class DeckCostResult:
    """The complete, structured result of calculate_deck_cost()."""

    required: int
    owned: int
    missing: int
    priced_quantity: int
    unpriced_quantity: int
    cost: Decimal
    selections: list[PriceSelection] = field(default_factory=list)
