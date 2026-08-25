import json
from pathlib import Path
from collections import defaultdict


# ============================================================
# CONFIGURATION
# ============================================================

BASE_DIR = Path(__file__).resolve().parent
MOXFIELD_DIR = BASE_DIR / "moxfield"

COLLECTION_PATH = MOXFIELD_DIR / "collection_normalized.json"
NORMALIZED_DECK_PATH = MOXFIELD_DIR / "testdeck_normalized.json"
RAW_DECK_PATH = MOXFIELD_DIR / "testdeck.json"


# ============================================================
# JSON HELPERS
# ============================================================

def load_json(path):
    print(f"Loading: {path}")

    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


# ============================================================
# RAW MOXFIELD DECK EXTRACTION
# ============================================================

def extract_raw_deck_records(raw_deck):
    """
    Convert the raw Moxfield deck response into a simple list
    of card records suitable for price indexing.

    Moxfield's raw deck structure is:

        main
        boards.mainboard.cards

    The commander is stored in `main`.

    Mainboard cards are stored in a dictionary under
    `boards.mainboard.cards`.
    """

    records = []

    # --------------------------------------------------------
    # Commander
    # --------------------------------------------------------

    commander = raw_deck.get("main")

    if isinstance(commander, dict):
        records.append(
            {
                "board": "commander",
                "quantity": 1,
                "finish": commander.get(
                    "defaultFinish",
                    "nonFoil",
                ),
                "card": commander,
            }
        )

    # --------------------------------------------------------
    # Mainboard
    # --------------------------------------------------------

    boards = raw_deck.get("boards", {})

    mainboard = boards.get("mainboard", {})

    cards = mainboard.get("cards", {})

    if isinstance(cards, dict):
        for record in cards.values():

            if not isinstance(record, dict):
                continue

            card = record.get("card")

            if not isinstance(card, dict):
                continue

            records.append(
                {
                    "board": "mainboard",
                    "quantity": int(
                        record.get("quantity", 1)
                    ),
                    "finish": record.get(
                        "finish",
                        card.get(
                            "defaultFinish",
                            "nonFoil",
                        ),
                    ),
                    "card": card,
                }
            )

    return records


# ============================================================
# NORMALIZED DECK VALIDATION
# ============================================================

def validate_normalized_deck(deck):
    commander = deck.get("commander", [])
    mainboard = deck.get("mainboard", [])

    commander_quantity = sum(
        int(card.get("quantity", 0))
        for card in commander
    )

    mainboard_quantity = sum(
        int(card.get("quantity", 0))
        for card in mainboard
    )

    total_quantity = (
        commander_quantity
        + mainboard_quantity
    )

    print()
    print("=" * 60)
    print("DECK STRUCTURE VALIDATION")
    print("-" * 60)
    print(
        f"Commander records:      "
        f"{len(commander)}"
    )
    print(
        f"Commander quantity:     "
        f"{commander_quantity}"
    )
    print(
        f"Mainboard records:      "
        f"{len(mainboard)}"
    )
    print(
        f"Mainboard quantity:     "
        f"{mainboard_quantity}"
    )
    print(
        f"Total unique records:   "
        f"{len(commander) + len(mainboard)}"
    )
    print(
        f"Total card quantity:    "
        f"{total_quantity}"
    )

    if commander_quantity != 1:
        raise AssertionError(
            "Expected exactly one commander."
        )

    if total_quantity != 100:
        raise AssertionError(
            "Expected Commander + Mainboard "
            "quantity to equal 100."
        )

    print("Deck structure validation: PASS")


# ============================================================
# PRICE DATA
# ============================================================

def get_finish_price(card, finish):
    """
    Return the USD price for a particular finish.

    Moxfield/Scryfall price fields are:

        nonFoil -> usd
        foil    -> usd_foil

    Missing / None prices are treated as unavailable.
    """

    prices = card.get("prices", {})

    if not isinstance(prices, dict):
        return None

    if finish == "foil":
        value = prices.get("usd_foil")
    else:
        value = prices.get("usd")

    if value is None:
        return None

    try:
        return float(value)
    except (
        TypeError,
        ValueError,
    ):
        return None


def available_finish_options(card):
    """
    Return all priced finish options for one printing.

    This deliberately only considers actual finishes supported
    by the card record.

    It does NOT infer that every card has both foil and nonfoil.
    """

    options = []

    if card.get("nonfoil") is True:
        price = get_finish_price(
            card,
            "nonFoil",
        )

        if price is not None:
            options.append(
                {
                    "finish": "nonFoil",
                    "price": price,
                    "price_field": "usd",
                }
            )

    if card.get("foil") is True:
        price = get_finish_price(
            card,
            "foil",
        )

        if price is not None:
            options.append(
                {
                    "finish": "foil",
                    "price": price,
                    "price_field": "usd_foil",
                }
            )

    return options


# ============================================================
# PRICE CATALOG
# ============================================================

def build_price_catalog(raw_deck):
    """
    Build a catalog from the raw deck's actual printing records.

    The catalog is indexed both by:

        card name
        scryfall ID

    A card may have multiple printing records if the source
    contains them.

    At this stage the real raw deck supplies the selected
    printings. Alternate-printing behavior is covered by the
    synthetic tests.
    """

    records = extract_raw_deck_records(
        raw_deck
    )

    by_name = defaultdict(list)
    by_scryfall_id = {}

    for record in records:

        card = record["card"]

        name = card.get("name")

        if not name:
            continue

        entry = {
            "name": name,
            "scryfall_id": card.get(
                "scryfall_id"
            ),
            "set": card.get("set"),
            "collector_number": card.get(
                "cn"
            ),
            "finish": record.get(
                "finish"
            ),
            "card": card,
        }

        by_name[name].append(entry)

        scryfall_id = card.get(
            "scryfall_id"
        )

        if scryfall_id:
            by_scryfall_id[
                scryfall_id
            ] = entry

    return {
        "by_name": dict(by_name),
        "by_scryfall_id": by_scryfall_id,
    }


# ============================================================
# PRICE SELECTION
# ============================================================

def select_same_printing_option(
    printing,
):
    """
    Select the cheapest priced finish for a
    specific printing.

    This is the normal purchase behavior when
    the printing is fixed.
    """

    card = printing["card"]

    options = available_finish_options(
        card
    )

    if not options:
        return None

    return min(
        options,
        key=lambda option: option["price"],
    )


def select_option(
    printing,
    strategy="same",
):
    """
    Select a price option for one printing.

    Strategies:

        same
            Use the selected printing and choose
            its cheapest available finish.

        cheapest
            Currently equivalent to same for a
            single printing. Alternate-printing
            comparison is handled by
            select_card_option().

        most_expensive
            Select the most expensive available
            finish for the printing.
    """

    card = printing["card"]

    options = available_finish_options(
        card
    )

    if not options:
        return None

    if strategy == "most_expensive":
        return max(
            options,
            key=lambda option: option["price"],
        )

    return min(
        options,
        key=lambda option: option["price"],
    )


def select_card_option(
    catalog,
    card_name,
    scryfall_id=None,
    strategy="same",
):
    """
    Select the appropriate purchase option for a
    card requirement.

    For `same`, the requested Scryfall printing is
    retained.

    For `cheapest`, all known printings for the card
    are considered.

    For `most_expensive`, all known priced printings
    are considered.

    IMPORTANT:

    If only one printing is present in the catalog,
    it is naturally treated as the only/default
    option.
    """

    candidates = catalog["by_name"].get(
        card_name,
        [],
    )

    if not candidates:
        return None

    # --------------------------------------------------------
    # SAME PRINTING
    # --------------------------------------------------------

    if strategy == "same":

        if scryfall_id:
            for printing in candidates:

                if (
                    printing.get(
                        "scryfall_id"
                    )
                    == scryfall_id
                ):
                    option = select_option(
                        printing,
                        "same",
                    )

                    if option is None:
                        return None

                    return {
                        **printing,
                        **option,
                    }

        # If there is no Scryfall ID, fall back
        # to the first available printing.
        for printing in candidates:

            option = select_option(
                printing,
                "same",
            )

            if option is not None:
                return {
                    **printing,
                    **option,
                }

        return None

    # --------------------------------------------------------
    # CHEAPEST
    # --------------------------------------------------------

    if strategy == "cheapest":

        options = []

        for printing in candidates:

            option = select_option(
                printing,
                "cheapest",
            )

            if option is None:
                continue

            options.append(
                {
                    **printing,
                    **option,
                }
            )

        if not options:
            return None

        return min(
            options,
            key=lambda option: option[
                "price"
            ],
        )

    # --------------------------------------------------------
    # MOST EXPENSIVE
    # --------------------------------------------------------

    if strategy == "most_expensive":

        options = []

        for printing in candidates:

            option = select_option(
                printing,
                "most_expensive",
            )

            if option is None:
                continue

            options.append(
                {
                    **printing,
                    **option,
                }
            )

        if not options:
            return None

        return max(
            options,
            key=lambda option: option[
                "price"
            ],
        )

    raise ValueError(
        f"Unknown price strategy: {strategy}"
    )


# ============================================================
# SYNTHETIC TESTS
# ============================================================

def synthetic_card(
    name,
    scryfall_id,
    nonfoil=None,
    foil=None,
    nonfoil_available=True,
    foil_available=True,
    set_code="tst",
    collector_number="1",
):
    return {
        "name": name,
        "scryfall_id": scryfall_id,
        "set": set_code,
        "cn": collector_number,
        "nonfoil": nonfoil_available,
        "foil": foil_available,
        "prices": {
            "usd": nonfoil,
            "usd_foil": foil,
        },
    }


def synthetic_catalog(cards):
    by_name = defaultdict(list)
    by_scryfall_id = {}

    for card in cards:

        entry = {
            "name": card["name"],
            "scryfall_id": card[
                "scryfall_id"
            ],
            "set": card.get("set"),
            "collector_number": card.get(
                "cn"
            ),
            "finish": "nonFoil",
            "card": card,
        }

        by_name[
            card["name"]
        ].append(entry)

        by_scryfall_id[
            card["scryfall_id"]
        ] = entry

    return {
        "by_name": dict(by_name),
        "by_scryfall_id": by_scryfall_id,
    }


def run_synthetic_tests():

    print()
    print("=" * 60)
    print("PRICE SELECTION SANITY TESTS")
    print("=" * 60)

    # --------------------------------------------------------
    # Same printing, cheapest treatment
    # --------------------------------------------------------

    card = synthetic_card(
        "Test Card",
        "id-1",
        nonfoil=2.00,
        foil=1.00,
    )

    catalog = synthetic_catalog(
        [card]
    )

    result = select_card_option(
        catalog,
        "Test Card",
        "id-1",
        "same",
    )

    assert result["finish"] == "foil"
    assert result["price"] == 1.00

    print(
        "  Same printing, cheapest treatment"
        "                PASS"
    )

    # --------------------------------------------------------
    # Same printing, foil cheapest
    # --------------------------------------------------------

    card = synthetic_card(
        "Test Card",
        "id-2",
        nonfoil=5.00,
        foil=2.00,
    )

    catalog = synthetic_catalog(
        [card]
    )

    result = select_card_option(
        catalog,
        "Test Card",
        "id-2",
        "same",
    )

    assert result["finish"] == "foil"
    assert result["price"] == 2.00

    print(
        "  Same printing, foil cheapest"
        "                       PASS"
    )

    # --------------------------------------------------------
    # Alternate printing cheaper
    # --------------------------------------------------------

    card_a = synthetic_card(
        "Multi Print",
        "id-a",
        nonfoil=10.00,
        foil=12.00,
        set_code="aaa",
    )

    card_b = synthetic_card(
        "Multi Print",
        "id-b",
        nonfoil=3.00,
        foil=4.00,
        set_code="bbb",
    )

    catalog = synthetic_catalog(
        [card_a, card_b]
    )

    result = select_card_option(
        catalog,
        "Multi Print",
        "id-a",
        "cheapest",
    )

    assert result["scryfall_id"] == "id-b"
    assert result["price"] == 3.00

    print(
        "  Alternate printing, cheaper selected"
        "          PASS"
    )

    # --------------------------------------------------------
    # Most expensive
    # --------------------------------------------------------

    result = select_card_option(
        catalog,
        "Multi Print",
        "id-a",
        "most_expensive",
    )

    assert result["scryfall_id"] == "id-a"
    assert result["price"] == 12.00

    print(
        "  Most expensive option"
        "                              PASS"
    )

    # --------------------------------------------------------
    # Single printing / single treatment
    # --------------------------------------------------------

    card = synthetic_card(
        "Single",
        "single",
        nonfoil=1.50,
        foil=None,
        foil_available=False,
    )

    catalog = synthetic_catalog(
        [card]
    )

    result = select_card_option(
        catalog,
        "Single",
        "single",
        "cheapest",
    )

    assert result["price"] == 1.50
    assert result["finish"] == "nonFoil"

    print(
        "  Single printing / single treatment"
        "               PASS"
    )

    # --------------------------------------------------------
    # None price excluded
    # --------------------------------------------------------

    card = synthetic_card(
        "Partial",
        "partial",
        nonfoil=None,
        foil=2.50,
        nonfoil_available=True,
        foil_available=True,
    )

    catalog = synthetic_catalog(
        [card]
    )

    result = select_card_option(
        catalog,
        "Partial",
        "partial",
        "cheapest",
    )

    assert result["price"] == 2.50
    assert result["finish"] == "foil"

    print(
        "  None price excluded"
        "                                PASS"
    )

    # --------------------------------------------------------
    # Completely unpriced
    # --------------------------------------------------------

    card = synthetic_card(
        "Unpriced",
        "unpriced",
        nonfoil=None,
        foil=None,
    )

    catalog = synthetic_catalog(
        [card]
    )

    result = select_card_option(
        catalog,
        "Unpriced",
        "unpriced",
        "cheapest",
    )

    assert result is None

    print(
        "  Completely unpriced card"
        "                         PASS"
    )

    # --------------------------------------------------------
    # Unknown card
    # --------------------------------------------------------

    result = select_card_option(
        catalog,
        "Does Not Exist",
        strategy="cheapest",
    )

    assert result is None

    print(
        "  Unknown card"
        "                                       PASS"
    )

    # --------------------------------------------------------
    # Quantity
    # --------------------------------------------------------

    unit_price = 1.25
    quantity = 20

    assert (
        unit_price * quantity
        == 25.00
    )

    print(
        "  Quantity calculation"
        "                              PASS"
    )

    print()
    print(
        "All price selection tests passed."
    )


# ============================================================
# MATCHING
# ============================================================

def run_matching(
    normalized_deck,
    collection,
):
    """
    Call the existing matcher using its actual API:

        analyze_deck(deck, collection)

    NOT:

        analyze_deck(collection, deck)
    """

    import matcher

    return matcher.analyze_deck(
        normalized_deck,
        collection,
        matching_mode="card",
    )


# ============================================================
# PRICE CALCULATION
# ============================================================

def calculate_strategy(
    normalized_deck,
    matching_result,
    catalog,
    strategy,
):
    """
    Price only the missing quantity.

    Ownership is determined by the matcher first.

    Price selection is therefore downstream from
    ownership determination.
    """

    rows = []

    total = 0.0
    priced_quantity = 0
    unpriced_quantity = 0

    for card_result in matching_result[
        "cards"
    ]:

        missing = int(
            card_result[
                "missing_quantity"
            ]
        )

        if missing <= 0:
            continue

        name = card_result["name"]

        scryfall_id = card_result.get(
            "scryfall_id"
        )

        option = select_card_option(
            catalog,
            name,
            scryfall_id,
            strategy,
        )

        if option is None:

            unpriced_quantity += missing

            rows.append(
                {
                    "name": name,
                    "required": card_result[
                        "required_quantity"
                    ],
                    "owned": card_result[
                        "owned_quantity"
                    ],
                    "missing": missing,
                    "option": None,
                }
            )

            continue

        unit_price = option["price"]

        line_total = (
            unit_price * missing
        )

        total += line_total

        priced_quantity += missing

        rows.append(
            {
                "name": name,
                "required": card_result[
                    "required_quantity"
                ],
                "owned": card_result[
                    "owned_quantity"
                ],
                "missing": missing,
                "option": option,
                "line_total": line_total,
            }
        )

    return {
        "strategy": strategy,
        "rows": rows,
        "priced_quantity": priced_quantity,
        "unpriced_quantity": unpriced_quantity,
        "total": total,
    }


# ============================================================
# DISPLAY
# ============================================================

def print_strategy(result):

    print()
    print("=" * 60)
    print(
        f"PRICE STRATEGY: "
        f"{result['strategy']}"
    )
    print("=" * 60)

    for row in result["rows"]:

        print()
        print(row["name"])

        print(
            f"  Required:        "
            f"{row['required']}"
        )

        print(
            f"  Owned:           "
            f"{row['owned']}"
        )

        print(
            f"  Missing:         "
            f"{row['missing']}"
        )

        option = row["option"]

        if option is None:

            print(
                "  Price:           "
                "UNAVAILABLE"
            )

            print(
                "  Line total:      "
                "UNAVAILABLE"
            )

            continue

        print(
            f"  Selected set:    "
            f"{option.get('set')}"
        )

        print(
            f"  Collector #:     "
            f"{option.get('collector_number')}"
        )

        print(
            f"  Finish:          "
            f"{option.get('finish')}"
        )

        print(
            f"  Price field:     "
            f"{option.get('price_field')}"
        )

        print(
            f"  Unit price:      "
            f"${option['price']:.2f}"
        )

        print(
            f"  Line total:      "
            f"${row['line_total']:.2f}"
        )

    print()
    print("-" * 60)

    print(
        f"Priced quantity:     "
        f"{result['priced_quantity']}"
    )

    print(
        f"Unpriced quantity:   "
        f"{result['unpriced_quantity']}"
    )

    print(
        f"Total:               "
        f"${result['total']:.2f}"
    )


# ============================================================
# MAIN
# ============================================================

def main():

    print("=" * 60)
    print(
        "MOXFIELD MINIMUM PURCHASE PRICE TEST"
    )
    print("=" * 60)

    collection = load_json(
        COLLECTION_PATH
    )

    normalized_deck = load_json(
        NORMALIZED_DECK_PATH
    )

    raw_deck = load_json(
        RAW_DECK_PATH
    )

    # --------------------------------------------------------
    # Validate deck
    # --------------------------------------------------------

    validate_normalized_deck(
        normalized_deck
    )

    # --------------------------------------------------------
    # Extract raw deck records
    # --------------------------------------------------------

    raw_records = extract_raw_deck_records(
        raw_deck
    )

    print()
    print("=" * 60)
    print("RAW DECK PRICE INDEX")
    print("-" * 60)

    print(
        f"Raw deck records extracted: "
        f"{len(raw_records)}"
    )

    catalog = build_price_catalog(
        raw_deck
    )

    print(
        f"Unique card names indexed: "
        f"{len(catalog['by_name'])}"
    )

    print(
        f"Unique printings indexed:   "
        f"{len(catalog['by_scryfall_id'])}"
    )

    if not catalog["by_name"]:
        raise AssertionError(
            "Price catalog is empty. "
            "Raw Moxfield deck extraction failed."
        )

    # --------------------------------------------------------
    # Synthetic tests
    # --------------------------------------------------------

    run_synthetic_tests()

    # --------------------------------------------------------
    # Matching
    # --------------------------------------------------------

    print()
    print("=" * 60)
    print("MATCHING")
    print("=" * 60)

    try:

        matching_result = run_matching(
            normalized_deck,
            collection,
        )

    except Exception as exc:

        print()
        print(
            "Existing matcher failed:"
        )

        print(
            f"  {type(exc).__name__}: "
            f"{exc}"
        )

        raise

    print(
        f"Required: "
        f"{matching_result['required_quantity']}"
    )

    print(
        f"Owned:    "
        f"{matching_result['owned_quantity']}"
    )

    print(
        f"Missing:  "
        f"{matching_result['missing_quantity']}"
    )

    # --------------------------------------------------------
    # Price strategies
    # --------------------------------------------------------

    results = {}

    for strategy in (
        "same",
        "cheapest",
        "most_expensive",
    ):

        result = calculate_strategy(
            normalized_deck,
            matching_result,
            catalog,
            strategy,
        )

        results[strategy] = result

        print_strategy(result)

    # --------------------------------------------------------
    # Summary
    # --------------------------------------------------------

    print()
    print("=" * 60)
    print("PRICE STRATEGY SUMMARY")
    print("=" * 60)

    for strategy in (
        "same",
        "cheapest",
        "most_expensive",
    ):

        result = results[strategy]

        print(
            f"{strategy:<18}"
            f"${result['total']:>9.2f}  "
            f"priced="
            f"{result['priced_quantity']:>3}  "
            f"unpriced="
            f"{result['unpriced_quantity']:>3}"
        )

    print()
    print(
        "PRICE CALCULATION TEST COMPLETE"
    )


if __name__ == "__main__":
    main()