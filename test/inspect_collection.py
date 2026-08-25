import json
from pathlib import Path
from collections import defaultdict


# ============================================================
# CONFIGURATION
# ============================================================

SCRIPT_DIR = Path(__file__).resolve().parent

COLLECTION_FILE = SCRIPT_DIR / "moxfield" / "collection.json"
OUTPUT_FILE = SCRIPT_DIR / "moxfield" / "collection-normalized.json"


# ============================================================
# HELPERS
# ============================================================

def load_json(path):
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def get_collection_entries(data):
    """
    Locate the collection entries in the Moxfield response.

    The current Moxfield response format uses a top-level
    'data' collection in some contexts, while test fixtures
    may contain the entries directly.
    """

    if isinstance(data, list):
        return data

    if not isinstance(data, dict):
        raise ValueError("Collection JSON must contain an object or array.")

    # Common possibilities
    for key in ("data", "entries", "cards", "results"):
        value = data.get(key)

        if isinstance(value, list):
            return value

    raise ValueError(
        "Could not locate collection entries in the JSON. "
        "Expected a list or one of: data, entries, cards, results."
    )


def get_card_name(entry):
    """
    Get the card name from the collection entry.
    """

    card = entry.get("card")

    if isinstance(card, dict):
        name = card.get("name")

        if name:
            return name

    name = entry.get("name")

    if name:
        return name

    return None


def get_card_field(entry, field):
    """
    Retrieve a field from the nested card object.
    """

    card = entry.get("card")

    if isinstance(card, dict):
        return card.get(field)

    return None


def get_quantity(entry):
    quantity = entry.get("quantity", 1)

    try:
        quantity = int(quantity)
    except (TypeError, ValueError):
        return None

    return quantity


# ============================================================
# NORMALIZATION
# ============================================================

def normalize_collection(entries):
    """
    Convert the raw collection into:

    {
        "cards": [
            {
                "name": "...",
                "printings": [
                    {
                        "set": "...",
                        "collectorNumber": "...",
                        "finish": "...",
                        "quantity": 1,
                        "scryfallId": "..."
                    }
                ]
            }
        ]
    }

    A unique printing is defined by:

        set + collectorNumber + finish

    Quantities are aggregated when multiple source entries
    represent the same unique printing.
    """

    cards = {}

    source_entries_processed = 0

    skipped_entries = []

    for entry in entries:
        source_entries_processed += 1

        name = get_card_name(entry)

        if not name:
            skipped_entries.append({
                "reason": "missing card name",
                "entry": entry,
            })
            continue

        set_code = get_card_field(entry, "set")
        collector_number = get_card_field(entry, "cn")
        scryfall_id = get_card_field(entry, "scryfall_id")

        finish = entry.get("finish")

        quantity = get_quantity(entry)

        if not set_code:
            skipped_entries.append({
                "reason": "missing set",
                "card": name,
            })
            continue

        if collector_number is None:
            skipped_entries.append({
                "reason": "missing collector number",
                "card": name,
            })
            continue

        if not finish:
            skipped_entries.append({
                "reason": "missing finish",
                "card": name,
            })
            continue

        if quantity is None or quantity <= 0:
            skipped_entries.append({
                "reason": "invalid quantity",
                "card": name,
                "quantity": entry.get("quantity"),
            })
            continue

        # Normalize collector number to a string.
        collector_number = str(collector_number)

        # Normalize finish casing.
        finish = str(finish)

        # Create the card record if necessary.
        if name not in cards:
            cards[name] = {
                "name": name,
                "printings": {}
            }

        # This is the important uniqueness rule.
        printing_key = (
            str(set_code),
            collector_number,
            finish
        )

        if printing_key not in cards[name]["printings"]:
            cards[name]["printings"][printing_key] = {
                "set": str(set_code),
                "collectorNumber": collector_number,
                "finish": finish,
                "quantity": 0,
                "scryfallId": scryfall_id,
            }

        printing = cards[name]["printings"][printing_key]

        # Aggregate quantity.
        printing["quantity"] += quantity

        # Preserve a Scryfall ID if the first occurrence did not
        # contain one but a later occurrence does.
        if not printing["scryfallId"] and scryfall_id:
            printing["scryfallId"] = scryfall_id

    # Convert printing dictionaries into arrays.
    normalized_cards = []

    for name in sorted(cards.keys(), key=str.casefold):
        card = cards[name]

        printings = list(card["printings"].values())

        # Stable ordering makes the generated JSON easier to inspect
        # and produces cleaner diffs if the file is version controlled.
        printings.sort(
            key=lambda p: (
                p["set"].casefold(),
                p["collectorNumber"].casefold(),
                p["finish"].casefold(),
            )
        )

        normalized_cards.append({
            "name": name,
            "printings": printings,
        })

    normalized = {
        "cards": normalized_cards
    }

    return normalized, source_entries_processed, skipped_entries


# ============================================================
# VALIDATION
# ============================================================

def validate_normalized_collection(
    normalized,
    source_entries_processed,
    skipped_entries,
):
    errors = []
    warnings = []

    cards = normalized.get("cards")

    if not isinstance(cards, list):
        errors.append("'cards' must be a list.")
        return errors, warnings

    normalized_card_names = set()

    total_normalized_quantity = 0

    for card in cards:

        # ----------------------------------------------------
        # Card-level validation
        # ----------------------------------------------------

        name = card.get("name")

        if not name:
            errors.append("Card is missing a name.")
            continue

        if name in normalized_card_names:
            errors.append(
                f"Duplicate normalized card name: {name}"
            )

        normalized_card_names.add(name)

        printings = card.get("printings")

        if not isinstance(printings, list):
            errors.append(
                f"{name}: 'printings' must be a list."
            )
            continue

        if not printings:
            errors.append(
                f"{name}: card has no printings."
            )
            continue

        card_total_quantity = 0
        printing_keys = set()

        # ----------------------------------------------------
        # Printing-level validation
        # ----------------------------------------------------

        for printing in printings:

            required_fields = (
                "set",
                "collectorNumber",
                "finish",
                "quantity",
                "scryfallId",
            )

            for field in required_fields:
                if field not in printing:
                    errors.append(
                        f"{name}: printing missing '{field}'."
                    )

            set_code = printing.get("set")
            collector_number = printing.get("collectorNumber")
            finish = printing.get("finish")
            quantity = printing.get("quantity")

            # Unique-printing identity
            printing_key = (
                set_code,
                collector_number,
                finish,
            )

            if printing_key in printing_keys:
                errors.append(
                    f"{name}: duplicate normalized printing "
                    f"{set_code}|{collector_number}|{finish}"
                )

            printing_keys.add(printing_key)

            # Quantity validation
            if (
                not isinstance(quantity, int)
                or isinstance(quantity, bool)
                or quantity <= 0
            ):
                errors.append(
                    f"{name}: invalid quantity for "
                    f"{set_code}|{collector_number}|{finish}: "
                    f"{quantity!r}"
                )
            else:
                card_total_quantity += quantity
                total_normalized_quantity += quantity

            # Scryfall ID validation
            if not printing.get("scryfallId"):
                warnings.append(
                    f"{name}: no Scryfall ID for "
                    f"{set_code}|{collector_number}|{finish}"
                )

        # ----------------------------------------------------
        # Derived total check
        # ----------------------------------------------------

        derived_total = sum(
            p.get("quantity", 0)
            for p in printings
            if isinstance(p.get("quantity"), int)
            and not isinstance(p.get("quantity"), bool)
        )

        if derived_total != card_total_quantity:
            errors.append(
                f"{name}: derived quantity mismatch."
            )

    # --------------------------------------------------------
    # Source vs normalized quantity sanity check
    # --------------------------------------------------------

    # This is intentionally not a strict equality check between
    # source entry count and normalized printing count.
    #
    # Multiple source entries are EXPECTED to collapse into one
    # normalized printing.
    #
    # We therefore only report the two counts for visibility.

    normalized_printing_count = sum(
        len(card.get("printings", []))
        for card in cards
    )

    # --------------------------------------------------------
    # Skipped entries
    # --------------------------------------------------------

    if skipped_entries:
        warnings.append(
            f"{len(skipped_entries)} source entries were skipped."
        )

    return errors, warnings


# ============================================================
# MAIN
# ============================================================

def main():

    if not COLLECTION_FILE.exists():
        raise FileNotFoundError(
            f"Collection file not found:\n{COLLECTION_FILE}"
        )

    raw_data = load_json(COLLECTION_FILE)

    entries = get_collection_entries(raw_data)

    normalized, source_count, skipped_entries = normalize_collection(
        entries
    )

    errors, warnings = validate_normalized_collection(
        normalized,
        source_count,
        skipped_entries,
    )

    # --------------------------------------------------------
    # Write normalized JSON
    # --------------------------------------------------------

    OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)

    with OUTPUT_FILE.open("w", encoding="utf-8") as f:
        json.dump(
            normalized,
            f,
            indent=2,
            ensure_ascii=False,
        )

    # --------------------------------------------------------
    # Summary
    # --------------------------------------------------------

    unique_card_names = len(normalized["cards"])

    unique_printings = sum(
        len(card["printings"])
        for card in normalized["cards"]
    )

    total_quantity = sum(
        printing["quantity"]
        for card in normalized["cards"]
        for printing in card["printings"]
    )

    print()
    print("# NORMALIZATION COMPLETE")
    print()
    print(f"Normalized collection written to:")
    print(OUTPUT_FILE)
    print()
    print(f"Unique card names: {unique_card_names}")
    print(f"Unique printings: {unique_printings}")
    print(f"Source collection entries processed: {source_count}")
    print(f"Total normalized quantity: {total_quantity}")

    # --------------------------------------------------------
    # Validation report
    # --------------------------------------------------------

    print()
    print("# VALIDATION")

    if not errors:
        print("PASS: No validation errors found.")
    else:
        print(f"FAIL: {len(errors)} validation error(s).")

        for error in errors:
            print(f"  ERROR: {error}")

    if warnings:
        print()
        print(f"Warnings: {len(warnings)}")

        for warning in warnings:
            print(f"  WARNING: {warning}")
    else:
        print("Warnings: 0")

    # --------------------------------------------------------
    # Final status
    # --------------------------------------------------------

    if errors:
        print()
        print("Normalization completed, but validation FAILED.")
        raise SystemExit(1)

    print()
    print("Normalization and validation completed successfully.")


if __name__ == "__main__":
    main()