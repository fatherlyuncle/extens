"""
Public orchestration layer for the deck-cost engine.

This module owns calculate_deck_cost(), the single entry point the
eventual browser integration is meant to call. It wires together:

    collection.py   -> owned-card index
    deck.py         -> card requirements (from normalized deck)
                     -> raw card/printing records (from raw deck)
    matching.py     -> required vs. owned vs. missing
    pricing.py      -> printing/price index + strategy selection

...and returns a single structured DeckCostResult instead of printed
text, so callers never need to know how matching or pricing work
internally.

--------------------------------------------------------------------
Two deliberate deviations worth calling out
--------------------------------------------------------------------

1. Two "deck" inputs, not one.

   The originally sketched signature was:

       calculate_deck_cost(collection, deck, pricing_strategy, ...)

   In practice Moxfield data comes in two shapes that each carry
   different, non-overlapping information:

     * `normalized_deck` -- card names/quantities/board, used to build
       requirements.
     * `raw_deck`         -- the full Moxfield API response, used to
       build the printing/price index (set, collector number, finish,
       price fields).

   deck_cost.py always needed both, so calculate_deck_cost() takes
   both explicitly rather than pretending one "deck" argument covers
   it. Silently picking one and hoping it had everything needed would
   have been the kind of behavior change we agreed to avoid.

2. include_commander is a manual override, not a read of Moxfield's
   own `includeCommandersInPrice` flag.

   The raw deck JSON *does* carry an `includeCommandersInPrice` field
   (False in the current fixture), and deck_cost.py has never read it
   -- it has always counted the commander as required, unconditionally.
   include_commander=True here reproduces that exact original behavior
   and is the default specifically so the existing integration-test
   numbers keep matching.

   This parameter does NOT currently read raw_deck["includeCommandersInPrice"].
   Wiring it up to that flag is a real, separate decision (it would
   change required from 100 to 99 for the current fixture) and should
   be made deliberately, not as a side effect of this refactor.
"""

from __future__ import annotations

from decimal import Decimal
from typing import Any

from .collection import build_collection_index
from .deck import build_requirements, extract_deck_records
from .matching import match_deck
from .models import DeckCostResult, PriceSelection
from .pricing import build_raw_price_catalog, select_price


def calculate_deck_cost(
    collection: Any,
    normalized_deck: dict[str, Any],
    raw_deck: dict[str, Any],
    pricing_strategy: str = "cheapest",
    include_commander: bool = True,
) -> DeckCostResult:
    """
    Calculate the cost to complete a deck given a collection.

    Args:
        collection: normalized collection data (list of
            {"name", "total_quantity", "unique_printings"} records).
        normalized_deck: normalized deck data (dict with "commander"
            and "mainboard" lists of {"name", "quantity", "finish",
            "scryfall_id"} records).
        raw_deck: the raw Moxfield deck API response (dict with a
            "boards" object), used for printing/price metadata.
        pricing_strategy: one of "same", "cheapest", "most_expensive".
        include_commander: whether to count the commander as a
            required card. See module docstring for why this doesn't
            read Moxfield's own includeCommandersInPrice flag yet.

    Returns:
        A DeckCostResult with the deck-level required/owned/missing
        counts, priced/unpriced quantities, total cost, and the list
        of PriceSelection lines used to reach that total.
    """
    collection_index = build_collection_index(collection)
    requirements = build_requirements(normalized_deck, include_commander=include_commander)
    matches = match_deck(requirements, collection_index)

    required = sum(m["required"] for m in matches)
    owned = sum(m["owned"] for m in matches)
    missing = sum(m["missing"] for m in matches)

    raw_records = extract_deck_records(raw_deck)
    catalog = build_raw_price_catalog(raw_records)

    total = Decimal("0")
    priced_quantity = 0
    unpriced_quantity = 0
    selections: list[PriceSelection] = []

    for match in matches:
        missing_qty = match["missing"]
        if missing_qty <= 0:
            continue

        name = match["name"]
        selected = select_price(catalog.get(name, []), pricing_strategy)

        if selected is None:
            unpriced_quantity += missing_qty
            continue

        record = selected["record"]
        unit_price = selected["price"]
        line_total = unit_price * missing_qty

        total += line_total
        priced_quantity += missing_qty

        selections.append(
            PriceSelection(
                card_name=name,
                set_code=str(record.get("set", "?")),
                collector_number=str(record.get("cn", "?")),
                finish=selected["finish"],
                price_field=selected["price_field"],
                unit_price=unit_price,
                quantity=missing_qty,
                line_total=line_total,
            )
        )

    return DeckCostResult(
        required=required,
        owned=owned,
        missing=missing,
        priced_quantity=priced_quantity,
        unpriced_quantity=unpriced_quantity,
        cost=total,
        selections=selections,
    )
