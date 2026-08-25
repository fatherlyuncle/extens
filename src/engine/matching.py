"""
Matching requirements against the owned collection.

Extracted from deck_cost.py's match_deck() with no behavior change.
The per-card match record stays a plain dict on purpose (see models.py
docstring) -- only the deck-level MatchResult is a public dataclass,
and engine.py builds that by summing over these dicts.
"""

from __future__ import annotations

from typing import Any

from .models import CardRequirement


def match_deck(
    requirements: list[CardRequirement],
    collection_index: dict[str, dict[str, Any]],
) -> list[dict[str, Any]]:
    results = []

    for req in requirements:
        required = req.quantity
        collection = collection_index.get(req.name)

        owned_total = 0
        if collection:
            try:
                owned_total = int(collection.get("total_quantity", 0))
            except (TypeError, ValueError):
                owned_total = 0

        owned = min(max(owned_total, 0), required)
        missing = required - owned

        results.append({
            "name": req.name,
            "quantity": req.quantity,
            "finish": req.finish,
            "scryfall_id": req.scryfall_id,
            "board": req.board,
            "required": required,
            "owned": owned,
            "missing": missing,
            "collection_record": collection,
        })

    return results
