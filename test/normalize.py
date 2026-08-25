import json
from pathlib import Path


# ============================================================
# FILE CONFIGURATION
# ============================================================

BASE_DIR = Path(__file__).resolve().parent

INPUT_FILE = BASE_DIR / "moxfield" / "collection.json"
OUTPUT_FILE = BASE_DIR / "moxfield" / "collection_normalized.json"


# ============================================================
# NORMALIZATION
# ============================================================

def normalize_collection(records):
    """
    Normalize raw Moxfield collection records into:

    CARD
    ├── name
    ├── total quantity
    └── unique printings
          ├── set
          ├── collector number
          ├── finish
          ├── quantity
          └── Scryfall ID

    Records representing the same printing are combined and
    their quantities are summed.
    """

    cards = {}

    for record in records:

        card = record.get("card")

        if not card:
            raise ValueError(
                f"Collection record {record.get('id')} "
                "does not contain a card object."
            )

        name = card.get("name")
        set_code = card.get("set")
        collector_number = card.get("cn")
        finish = record.get("finish")
        scryfall_id = card.get("scryfall_id")
        quantity = record.get("quantity", 0)

        if not name:
            raise ValueError(
                f"Collection record {record.get('id')} "
                "does not contain a card name."
            )

        if quantity is None:
            quantity = 0

        if not isinstance(quantity, (int, float)):
            raise ValueError(
                f"Invalid quantity for collection record "
                f"{record.get('id')}: {quantity!r}"
            )

        # ----------------------------------------------------
        # Create the top-level card entry if necessary.
        # ----------------------------------------------------

        if name not in cards:
            cards[name] = {
                "name": name,
                "total_quantity": 0,
                "unique_printings": {},
            }

        normalized_card = cards[name]

        # ----------------------------------------------------
        # Add to the card's total quantity.
        # ----------------------------------------------------

        normalized_card["total_quantity"] += quantity

        # ----------------------------------------------------
        # Identify the unique printing.
        #
        # Set + collector number + finish + Scryfall ID
        # together identify the normalized printing.
        # ----------------------------------------------------

        printing_key = (
            set_code,
            collector_number,
            finish,
            scryfall_id,
        )

        if printing_key not in normalized_card["unique_printings"]:
            normalized_card["unique_printings"][printing_key] = {
                "set": set_code,
                "collector_number": collector_number,
                "finish": finish,
                "quantity": 0,
                "scryfall_id": scryfall_id,
            }

        printing = normalized_card["unique_printings"][printing_key]

        printing["quantity"] += quantity

    # --------------------------------------------------------
    # Convert the internal printing dictionaries into lists.
    # --------------------------------------------------------

    normalized = []

    for card in cards.values():

        printings = list(
            card["unique_printings"].values()
        )

        normalized.append(
            {
                "name": card["name"],
                "total_quantity": card["total_quantity"],
                "unique_printings": printings,
            }
        )

    # --------------------------------------------------------
    # Sort cards alphabetically for deterministic output.
    # --------------------------------------------------------

    normalized.sort(
        key=lambda card: card["name"].lower()
    )

    # Sort printings deterministically as well.
    for card in normalized:
        card["unique_printings"].sort(
            key=lambda printing: (
                str(printing["set"]).lower(),
                str(printing["collector_number"]).lower(),
                str(printing["finish"]).lower(),
                str(printing["scryfall_id"]).lower(),
            )
        )

    return normalized


# ============================================================
# VALIDATION
# ============================================================

def validate_normalized_collection(
    raw_records,
    normalized_cards,
):
    """
    Validate that normalization preserved the complete
    quantity represented by the raw collection.

    Raw records may contain multiple records for the same
    printing, so validation is performed using quantity totals.
    """

    raw_quantity = sum(
        record.get("quantity", 0)
        for record in raw_records
    )

    normalized_quantity = sum(
        card["total_quantity"]
        for card in normalized_cards
    )

    print()
    print("=" * 60)
    print("VALIDATION")
    print("=" * 60)

    print()
    print(f"Raw collection quantity:        {raw_quantity}")
    print(f"Normalized collection quantity: {normalized_quantity}")

    if raw_quantity != normalized_quantity:
        print()
        print("FAIL: Quantity was lost during normalization.")

        raise RuntimeError(
            "Normalized quantity does not match raw quantity."
        )

    print()
    print("PASS: All card quantities preserved.")

    # --------------------------------------------------------
    # Also verify each card's total equals the sum of its
    # normalized printing quantities.
    # --------------------------------------------------------

    for card in normalized_cards:

        printing_quantity = sum(
            printing["quantity"]
            for printing in card["unique_printings"]
        )

        if printing_quantity != card["total_quantity"]:
            raise RuntimeError(
                f"Quantity mismatch for card "
                f"'{card['name']}': "
                f"card total is {card['total_quantity']}, "
                f"but printing total is {printing_quantity}."
            )

    print("PASS: All card totals match printing totals.")


# ============================================================
# FILE I/O
# ============================================================

def load_raw_collection():
    """
    Read the immutable raw collection fixture.
    """

    if not INPUT_FILE.exists():
        raise FileNotFoundError(
            f"Raw collection file not found:\n{INPUT_FILE}"
        )

    with open(
        INPUT_FILE,
        "r",
        encoding="utf-8",
    ) as f:
        records = json.load(f)

    if not isinstance(records, list):
        raise ValueError(
            "Expected collection.json to contain a list "
            "of collection records."
        )

    return records


def write_normalized_collection(normalized_cards):
    """
    Write normalized collection data to a separate file.
    """

    OUTPUT_FILE.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    with open(
        OUTPUT_FILE,
        "w",
        encoding="utf-8",
    ) as f:
        json.dump(
            normalized_cards,
            f,
            indent=2,
            ensure_ascii=False,
        )


# ============================================================
# MAIN
# ============================================================

def main():

    print()
    print("=" * 60)
    print("MOXFIELD COLLECTION NORMALIZER")
    print("=" * 60)

    # --------------------------------------------------------
    # Load raw master fixture
    # --------------------------------------------------------

    print()
    print("Loading raw collection:")
    print(INPUT_FILE)

    raw_records = load_raw_collection()

    print(f"Raw records loaded: {len(raw_records)}")

    # --------------------------------------------------------
    # Normalize
    # --------------------------------------------------------

    print()
    print("Normalizing collection...")

    normalized_cards = normalize_collection(
        raw_records
    )

    # --------------------------------------------------------
    # Validation
    # --------------------------------------------------------

    validate_normalized_collection(
        raw_records,
        normalized_cards,
    )

    # --------------------------------------------------------
    # Output
    # --------------------------------------------------------

    write_normalized_collection(
        normalized_cards
    )

    print()
    print("=" * 60)
    print("NORMALIZATION COMPLETE")
    print("=" * 60)

    print()
    print(f"Raw records:       {len(raw_records)}")
    print(f"Unique cards:      {len(normalized_cards)}")

    unique_printings = sum(
        len(card["unique_printings"])
        for card in normalized_cards
    )

    print(f"Unique printings:  {unique_printings}")

    print()
    print("Normalized collection written to:")
    print(OUTPUT_FILE)

    print()


if __name__ == "__main__":
    main()