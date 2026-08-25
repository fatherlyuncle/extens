#!/usr/bin/env python3
from __future__ import annotations

import json
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Any

BASE_DIR = Path(__file__).resolve().parent
MOXFIELD_DIR = BASE_DIR / "moxfield"

COLLECTION_PATH = MOXFIELD_DIR / "collection_normalized.json"
NORMALIZED_DECK_PATH = MOXFIELD_DIR / "testdeck_normalized.json"
RAW_DECK_PATH = MOXFIELD_DIR / "testdeck.json"


def load_json(path: Path) -> Any:
    print(f"Loading: {path}")
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def dec(value: Any) -> Decimal | None:
    if value is None or value == "":
        return None
    try:
        x = Decimal(str(value))
    except (InvalidOperation, ValueError, TypeError):
        return None
    return x if x >= 0 else None


def qty(record: dict[str, Any]) -> int:
    try:
        return max(int(record.get("quantity", 1)), 0)
    except (TypeError, ValueError):
        return 1


# ---------------------------------------------------------------------
# NORMALIZED DECK
# ---------------------------------------------------------------------

def normalized_deck_records(deck: dict[str, Any]) -> list[dict[str, Any]]:
    """Return commander + mainboard records; deliberately exclude sideboard."""
    records = []
    for section in ("commander", "mainboard"):
        value = deck.get(section, [])
        if isinstance(value, list):
            records.extend(x for x in value if isinstance(x, dict))
    return records


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


# ---------------------------------------------------------------------
# DECK VALIDATION
# ---------------------------------------------------------------------

def validate_deck_structure(
    normalized_deck: dict[str, Any],
    raw_records: list[dict[str, Any]],
) -> None:
    commander = [
        x for x in normalized_deck.get("commander", [])
        if isinstance(x, dict)
    ]
    mainboard = [
        x for x in normalized_deck.get("mainboard", [])
        if isinstance(x, dict)
    ]

    commander_qty = sum(qty(x) for x in commander)
    mainboard_qty = sum(qty(x) for x in mainboard)
    total_qty = sum(qty(x) for x in raw_records)

    print()
    print("=" * 60)
    print("DECK STRUCTURE VALIDATION")
    print("-" * 60)
    print(f"Commander records:      {len(commander)}")
    print(f"Commander quantity:     {commander_qty}")
    print(f"Mainboard records:      {len(mainboard)}")
    print(f"Mainboard quantity:     {mainboard_qty}")
    print(f"Total unique records:   {len(raw_records)}")
    print(f"Total card quantity:    {total_qty}")

    assert len(commander) == 1
    assert commander_qty == 1
    assert len(mainboard) == 80
    assert mainboard_qty == 99
    assert len(raw_records) == 81
    assert total_qty == 100

    print("Deck structure validation: PASS")


# ---------------------------------------------------------------------
# COLLECTION MATCHING
# ---------------------------------------------------------------------

def build_collection_index(
    collection: Any,
) -> dict[str, dict[str, Any]]:
    if not isinstance(collection, list):
        raise TypeError("Normalized collection must be a list.")

    index = {}
    for record in collection:
        if not isinstance(record, dict):
            continue
        name = record.get("name")
        if name:
            index[str(name)] = record
    return index


def build_requirements(
    normalized_deck: dict[str, Any],
) -> list[dict[str, Any]]:
    return [
        {
            "name": str(x["name"]),
            "quantity": qty(x),
            "finish": x.get("finish", "nonFoil"),
            "scryfall_id": x.get("scryfall_id"),
        }
        for x in normalized_deck_records(normalized_deck)
        if x.get("name")
    ]


def match_deck(
    requirements: list[dict[str, Any]],
    collection_index: dict[str, dict[str, Any]],
) -> list[dict[str, Any]]:
    results = []

    for req in requirements:
        required = req["quantity"]
        collection = collection_index.get(req["name"])

        owned_total = 0
        if collection:
            try:
                owned_total = int(collection.get("total_quantity", 0))
            except (TypeError, ValueError):
                owned_total = 0

        owned = min(max(owned_total, 0), required)
        missing = required - owned

        results.append({
            **req,
            "required": required,
            "owned": owned,
            "missing": missing,
            "collection_record": collection,
        })

    return results


# ---------------------------------------------------------------------
# PRICE CATALOG
# ---------------------------------------------------------------------

def build_raw_price_catalog(
    raw_records: list[dict[str, Any]],
) -> dict[str, list[dict[str, Any]]]:
    catalog: dict[str, list[dict[str, Any]]] = {}

    for record in raw_records:
        name = record.get("name")
        if name:
            catalog.setdefault(str(name), []).append(record)

    return catalog


def price_options(record: dict[str, Any]) -> list[dict[str, Any]]:
    prices = record.get("prices", {})
    if not isinstance(prices, dict):
        return []

    result = []

    for finish, field in (
        ("nonFoil", "usd"),
        ("foil", "usd_foil"),
        ("etched", "usd_etched"),
    ):
        value = dec(prices.get(field))
        if value is not None:
            result.append({
                "finish": finish,
                "price_field": field,
                "price": value,
            })

    return result


def select_price(
    records: list[dict[str, Any]],
    strategy: str,
) -> dict[str, Any] | None:
    candidates = []

    for record in records:
        options = price_options(record)
        requested_finish = record.get("finish", "nonFoil")

        if strategy == "same":
            options = [
                x for x in options
                if x["finish"] == requested_finish
            ]

        for option in options:
            candidates.append({**option, "record": record})

    if not candidates:
        return None

    if strategy == "same":
        return candidates[0]
    if strategy == "cheapest":
        return min(candidates, key=lambda x: x["price"])
    if strategy == "most_expensive":
        return max(candidates, key=lambda x: x["price"])

    raise ValueError(f"Unknown price strategy: {strategy}")


# ---------------------------------------------------------------------
# SANITY TESTS
# ---------------------------------------------------------------------

def test_record(
    name: str,
    finish: str,
    usd=None,
    usd_foil=None,
    usd_etched=None,
) -> dict[str, Any]:
    return {
        "name": name,
        "set": "tst",
        "cn": "1",
        "finish": finish,
        "prices": {
            "usd": usd,
            "usd_foil": usd_foil,
            "usd_etched": usd_etched,
        },
    }


def run_price_tests() -> None:
    print()
    print("=" * 60)
    print("PRICE SELECTION SANITY TESTS")
    print("=" * 60)

    r = test_record("Test", "nonFoil", 0.50, 1.25)

    assert select_price([r], "same")["price"] == Decimal("0.50")
    print("  Same printing, cheapest treatment                PASS")

    r["finish"] = "foil"
    assert select_price([r], "same")["price"] == Decimal("1.25")
    print("  Same printing, foil cheapest                    PASS")

    assert select_price([r], "cheapest")["price"] == Decimal("0.50")
    print("  Alternate treatment, cheaper selected           PASS")

    assert select_price([r], "most_expensive")["price"] == Decimal("1.25")
    print("  Most expensive option                            PASS")

    one = test_record("One", "nonFoil", 0.33)
    assert select_price([one], "cheapest")["price"] == Decimal("0.33")
    print("  Single printing / single treatment               PASS")

    none = test_record("None", "nonFoil")
    assert select_price([none], "cheapest") is None
    print("  None price excluded                              PASS")

    assert select_price([], "cheapest") is None
    print("  Completely unpriced card                         PASS")

    assert select_price([], "cheapest") is None
    print("  Unknown card                                      PASS")

    assert select_price([one], "cheapest")["price"] * 19 == Decimal("6.27")
    print("  Quantity calculation                              PASS")

    print()
    print("All price selection tests passed.")


# ---------------------------------------------------------------------
# PRICE CALCULATION
# ---------------------------------------------------------------------

def calculate(
    matches: list[dict[str, Any]],
    catalog: dict[str, list[dict[str, Any]]],
    strategy: str,
):
    total = Decimal("0")
    priced = 0
    unpriced = 0

    print()
    print("=" * 60)
    print(f"PRICE STRATEGY: {strategy}")
    print("=" * 60)

    for match in matches:
        missing = match["missing"]
        if missing <= 0:
            continue

        name = match["name"]
        selected = select_price(catalog.get(name, []), strategy)

        print()
        print(name)
        print(f"  Required:        {match['required']}")
        print(f"  Owned:           {match['owned']}")
        print(f"  Missing:         {missing}")

        if selected is None:
            print("  Price:           UNAVAILABLE")
            print("  Line total:      UNAVAILABLE")
            unpriced += missing
            continue

        record = selected["record"]
        unit = selected["price"]
        line = unit * missing

        total += line
        priced += missing

        print(f"  Selected set:    {record.get('set', '?')}")
        print(f"  Collector #:     {record.get('cn', '?')}")
        print(f"  Finish:          {selected['finish']}")
        print(f"  Price field:     {selected['price_field']}")
        print(f"  Unit price:      ${unit:.2f}")
        print(f"  Line total:      ${line:.2f}")

    print()
    print("-" * 60)
    print(f"Priced quantity:     {priced}")
    print(f"Unpriced quantity:   {unpriced}")
    print(f"Total:               ${total:.2f}")

    return total, priced, unpriced


def main() -> None:
    print("=" * 60)
    print("MOXFIELD DECK MISSING-CARD / MINIMUM COST ENGINE")
    print("=" * 60)

    collection = load_json(COLLECTION_PATH)
    normalized_deck = load_json(NORMALIZED_DECK_PATH)
    raw_deck = load_json(RAW_DECK_PATH)

    # Critical fix: raw Moxfield data is nested under boards.
    raw_records = extract_deck_records(raw_deck)

    validate_deck_structure(normalized_deck, raw_records)

    catalog = build_raw_price_catalog(raw_records)

    print()
    print("=" * 60)
    print("RAW DECK PRICE INDEX")
    print("-" * 60)
    print(f"Raw deck records extracted: {len(raw_records)}")
    print(f"Unique card names indexed: {len(catalog)}")
    print(f"Unique printings indexed:  {sum(len(v) for v in catalog.values())}")

    run_price_tests()

    collection_index = build_collection_index(collection)
    requirements = build_requirements(normalized_deck)
    matches = match_deck(requirements, collection_index)

    required = sum(x["required"] for x in matches)
    owned = sum(x["owned"] for x in matches)
    missing = sum(x["missing"] for x in matches)

    print()
    print("=" * 60)
    print("MATCHING")
    print("=" * 60)
    print(f"Required: {required}")
    print(f"Owned:    {owned}")
    print(f"Missing:  {missing}")

    summaries = {}
    for strategy in ("same", "cheapest", "most_expensive"):
        summaries[strategy] = calculate(matches, catalog, strategy)

    print()
    print("=" * 60)
    print("PRICE STRATEGY SUMMARY")
    print("=" * 60)

    for strategy, (total, priced, unpriced) in summaries.items():
        print(
            f"{strategy:<17}"
            f"${total:>9.2f}"
            f"  priced={priced:>3}"
            f"  unpriced={unpriced:>3}"
        )

    print()
    print("DECK COST CALCULATION TEST COMPLETE")


if __name__ == "__main__":
    main()
