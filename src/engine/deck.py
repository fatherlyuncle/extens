"""
Deck extraction and requirement-building.

Extracted from deck_cost.py. The raw-board extraction logic
(extract_raw_board_cards / extract_deck_records) is behaviorally
unchanged from the original implementation.

build_requirements() gained one addition beyond the original: an
`include_commander` flag and a `board` field on each CardRequirement.
Neither changes the numbers produced when include_commander=True (the
default, and the only behavior deck_cost.py ever had) -- see the
include_commander note in engine.py for why this isn't wired to
Moxfield's own `includeCommandersInPrice` flag yet.
"""

from __future__ import annotations

from typing import Any

from .models import CardRequirement


def qty(record: dict[str, Any]) -> int:
    try:
        return max(int(record.get("quantity", 1)), 0)
    except (TypeError, ValueError):
        return 1


# ---------------------------------------------------------------------
# NORMALIZED DECK
# ---------------------------------------------------------------------

def normalized_deck_records(deck: dict[str, Any]) -> list[dict[str, Any]]:
    """Return commander + mainboard records; deliberately excludes sideboard."""
    records = []
    for section in ("commander", "mainboard"):
        value = deck.get(section, [])
        if isinstance(value, list):
            records.extend(x for x in value if isinstance(x, dict))
    return records


def build_requirements(
    normalized_deck: dict[str, Any],
    include_commander: bool = True,
) -> list[CardRequirement]:
    """
    Build the list of CardRequirement objects the matcher needs.

    include_commander=True (the default) reproduces deck_cost.py's
    original, unconditional behavior of counting the commander as
    required. Setting it False excludes commander records entirely.
    """
    sections = ("commander", "mainboard") if include_commander else ("mainboard",)

    requirements: list[CardRequirement] = []
    for section in sections:
        value = normalized_deck.get(section, [])
        if not isinstance(value, list):
            continue
        for record in value:
            if not isinstance(record, dict) or not record.get("name"):
                continue
            requirements.append(
                CardRequirement(
                    name=str(record["name"]),
                    quantity=qty(record),
                    board=section,
                    finish=record.get("finish", "nonFoil"),
                    scryfall_id=record.get("scryfall_id"),
                )
            )
    return requirements


# ---------------------------------------------------------------------
# RAW MOXFIELD DECK
# ---------------------------------------------------------------------

def extract_raw_board_cards(board: Any) -> list[dict[str, Any]]:
    """
    Raw Moxfield board shape:

        {
          "count": 99,
          "cards": {
             "internal-id": {
                "quantity": 1,
                "boardType": "mainboard",
                "finish": "nonFoil",
                "card": {...}
             }
          }
        }

    Flatten each nested card into a convenient record while preserving
    the board-specific quantity/finish fields.
    """
    if not isinstance(board, dict):
        return []

    cards = board.get("cards", {})
    if isinstance(cards, dict):
        entries = cards.values()
    elif isinstance(cards, list):
        entries = cards
    else:
        return []

    result = []

    for entry in entries:
        if not isinstance(entry, dict):
            continue

        card = entry.get("card")
        if not isinstance(card, dict):
            continue

        record = dict(card)
        record["quantity"] = qty(entry)
        record["finish"] = entry.get(
            "finish",
            card.get("defaultFinish", "nonFoil"),
        )
        record["boardType"] = entry.get("boardType")
        record["isFoil"] = bool(entry.get("isFoil", False))
        record["isAlter"] = bool(entry.get("isAlter", False))
        record["isProxy"] = bool(entry.get("isProxy", False))
        result.append(record)

    return result


def extract_deck_records(raw_deck: dict[str, Any]) -> list[dict[str, Any]]:
    """
    Extract the actual Commander deck from a raw Moxfield response.

    IMPORTANT:
      raw Moxfield does NOT use top-level "commander"/"mainboard".
      It uses:

          raw_deck["boards"]["commanders"]["cards"]
          raw_deck["boards"]["mainboard"]["cards"]

      The raw response also has a sideboard. It is intentionally excluded.
    """
    if not isinstance(raw_deck, dict):
        raise TypeError(
            f"Unable to interpret raw deck data: {type(raw_deck).__name__}"
        )

    boards = raw_deck.get("boards")
    if not isinstance(boards, dict):
        raise TypeError(
            "Raw Moxfield deck is missing the expected 'boards' object."
        )

    commander = extract_raw_board_cards(boards.get("commanders"))
    mainboard = extract_raw_board_cards(boards.get("mainboard"))

    records = commander + mainboard

    if not records:
        raise TypeError(
            "Raw Moxfield deck contained boards, but no commander/mainboard "
            "cards could be extracted."
        )

    return records
