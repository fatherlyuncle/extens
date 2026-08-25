from pathlib import Path

from matcher import (
    MATCH_EXACT,
    MATCH_PRINTING,
    MATCH_CARD,
    analyze_deck,
    analyze_deck_files,
    print_analysis,
)


# ============================================================
# REAL FIXTURE FILES
# ============================================================

BASE_DIR = Path(__file__).resolve().parent

DECK_FILE = (
    BASE_DIR
    / "moxfield"
    / "testdeck_normalized.json"
)

COLLECTION_FILE = (
    BASE_DIR
    / "moxfield"
    / "collection_normalized.json"
)


# ============================================================
# BASIC VALIDATION
# ============================================================

def validate_result(result):
    required = result[
        "required_quantity"
    ]

    owned = result[
        "owned_quantity"
    ]

    missing = result[
        "missing_quantity"
    ]

    assert (
        owned + missing == required
    )

    assert owned >= 0
    assert missing >= 0
    assert owned <= required

    for card in result["cards"]:

        assert (
            card["owned_quantity"]
            + card["missing_quantity"]
            == card["required_quantity"]
        )

        assert (
            card["owned_quantity"]
            >= 0
        )

        assert (
            card["missing_quantity"]
            >= 0
        )

        assert (
            card["owned_quantity"]
            <= card["required_quantity"]
        )


# ============================================================
# SYNTHETIC COLLECTION
# ============================================================

def make_test_collection():
    """
    Small artificial collection used to test inventory
    allocation.

    This intentionally contains multiple printings and
    multiple finishes.
    """

    return [
        {
            "name": "Swamp",
            "total_quantity": 26,
            "unique_printings": [
                {
                    "set": "AAA",
                    "collector_number": "1",
                    "finish": "nonFoil",
                    "quantity": 8,
                    "scryfall_id": "swamp-a",
                },
                {
                    "set": "BBB",
                    "collector_number": "2",
                    "finish": "nonFoil",
                    "quantity": 15,
                    "scryfall_id": "swamp-b",
                },
                {
                    "set": "CCC",
                    "collector_number": "3",
                    "finish": "foil",
                    "quantity": 3,
                    "scryfall_id": "swamp-c",
                },
            ],
        },
        {
            "name": "Card X",
            "total_quantity": 1,
            "unique_printings": [
                {
                    "set": "AAA",
                    "collector_number": "10",
                    "finish": "nonFoil",
                    "quantity": 1,
                    "scryfall_id": "card-x-a",
                }
            ],
        },
        {
            "name": "Card Y",
            "total_quantity": 4,
            "unique_printings": [
                {
                    "set": "AAA",
                    "collector_number": "20",
                    "finish": "nonFoil",
                    "quantity": 2,
                    "scryfall_id": "card-y-a",
                },
                {
                    "set": "BBB",
                    "collector_number": "21",
                    "finish": "foil",
                    "quantity": 2,
                    "scryfall_id": "card-y-b",
                },
            ],
        },
    ]


# ============================================================
# SYNTHETIC DECK
# ============================================================

def make_test_deck(cards):
    return {
        "name": "Synthetic Test Deck",
        "format": "commander",
        "commander": [],
        "mainboard": cards,
    }


def deck_card(
    name,
    quantity,
    scryfall_id,
    finish="nonFoil",
):
    return {
        "name": name,
        "quantity": quantity,
        "scryfall_id": scryfall_id,
        "finish": finish,
    }


# ============================================================
# TEST: BASIC LAND QUANTITY
# ============================================================

def test_basic_land_quantity():
    collection = make_test_collection()

    deck = make_test_deck(
        [
            deck_card(
                "Swamp",
                20,
                "swamp-a",
            )
        ]
    )

    result = analyze_deck(
        deck,
        collection,
        MATCH_CARD,
    )

    assert result[
        "required_quantity"
    ] == 20

    assert result[
        "owned_quantity"
    ] == 20

    assert result[
        "missing_quantity"
    ] == 0


# ============================================================
# TEST: REQUIREMENT EXCEEDS INVENTORY
# ============================================================

def test_quantity_exceeds_inventory():
    collection = make_test_collection()

    deck = make_test_deck(
        [
            deck_card(
                "Swamp",
                30,
                "swamp-a",
            )
        ]
    )

    result = analyze_deck(
        deck,
        collection,
        MATCH_CARD,
    )

    assert result[
        "required_quantity"
    ] == 30

    assert result[
        "owned_quantity"
    ] == 26

    assert result[
        "missing_quantity"
    ] == 4


# ============================================================
# TEST: ARBITRARY COPY COUNT
# ============================================================

def test_arbitrary_copy_count():
    """
    The matcher must not impose Commander singleton rules.

    If the deck says 17 copies, 17 are required.
    """

    collection = make_test_collection()

    deck = make_test_deck(
        [
            deck_card(
                "Swamp",
                17,
                "swamp-a",
            )
        ]
    )

    result = analyze_deck(
        deck,
        collection,
        MATCH_CARD,
    )

    assert result[
        "required_quantity"
    ] == 17

    assert result[
        "owned_quantity"
    ] == 17

    assert result[
        "missing_quantity"
    ] == 0


# ============================================================
# TEST: NO DOUBLE COUNTING
# ============================================================

def test_no_double_counting():
    """
    One physical copy cannot satisfy two separate deck
    requirements.
    """

    collection = make_test_collection()

    deck = make_test_deck(
        [
            deck_card(
                "Card X",
                1,
                "card-x-a",
            ),
            deck_card(
                "Card X",
                1,
                "card-x-a",
            ),
        ]
    )

    result = analyze_deck(
        deck,
        collection,
        MATCH_CARD,
    )

    assert result[
        "required_quantity"
    ] == 2

    assert result[
        "owned_quantity"
    ] == 1

    assert result[
        "missing_quantity"
    ] == 1


# ============================================================
# TEST: MULTIPLE PRINTINGS
# ============================================================

def test_multiple_printings():
    collection = make_test_collection()

    deck = make_test_deck(
        [
            deck_card(
                "Swamp",
                20,
                "swamp-a",
            )
        ]
    )

    result = analyze_deck(
        deck,
        collection,
        MATCH_CARD,
    )

    assert result[
        "owned_quantity"
    ] == 20


# ============================================================
# TEST: EXACT PRINTING
# ============================================================

def test_exact_printing():
    collection = make_test_collection()

    deck = make_test_deck(
        [
            deck_card(
                "Swamp",
                10,
                "swamp-a",
                "nonFoil",
            )
        ]
    )

    result = analyze_deck(
        deck,
        collection,
        MATCH_EXACT,
    )

    assert result[
        "owned_quantity"
    ] == 8

    assert result[
        "missing_quantity"
    ] == 2


# ============================================================
# TEST: EXACT FINISH MATTERS
# ============================================================

def test_exact_finish():
    collection = make_test_collection()

    deck = make_test_deck(
        [
            deck_card(
                "Swamp",
                3,
                "swamp-c",
                "nonFoil",
            )
        ]
    )

    result = analyze_deck(
        deck,
        collection,
        MATCH_EXACT,
    )

    assert result[
        "owned_quantity"
    ] == 0

    assert result[
        "missing_quantity"
    ] == 3


# ============================================================
# TEST: PRINTING IGNORING FINISH
# ============================================================

def test_printing_ignores_finish():
    collection = make_test_collection()

    deck = make_test_deck(
        [
            deck_card(
                "Swamp",
                3,
                "swamp-c",
                "nonFoil",
            )
        ]
    )

    result = analyze_deck(
        deck,
        collection,
        MATCH_PRINTING,
    )

    assert result[
        "owned_quantity"
    ] == 3

    assert result[
        "missing_quantity"
    ] == 0


# ============================================================
# TEST: CARD MODE USES ALL PRINTINGS
# ============================================================

def test_card_uses_all_printings():
    collection = make_test_collection()

    deck = make_test_deck(
        [
            deck_card(
                "Card Y",
                4,
                "card-y-a",
            )
        ]
    )

    result = analyze_deck(
        deck,
        collection,
        MATCH_CARD,
    )

    assert result[
        "owned_quantity"
    ] == 4

    assert result[
        "missing_quantity"
    ] == 0


# ============================================================
# REAL DECK TEST
# ============================================================

def test_real_deck():

    print()
    print("=" * 60)
    print("REAL MOXFIELD DECK TEST")
    print("=" * 60)

    results = {}

    for mode in (
        MATCH_EXACT,
        MATCH_PRINTING,
        MATCH_CARD,
    ):

        result = analyze_deck_files(
            DECK_FILE,
            COLLECTION_FILE,
            mode,
        )

        validate_result(
            result
        )

        results[mode] = result

        print_analysis(
            result
        )

        print()
        print(
            f"{mode.capitalize()} validation: PASS"
        )

    # --------------------------------------------------------
    # Less restrictive modes cannot produce fewer owned cards.
    # --------------------------------------------------------

    assert (
        results[MATCH_EXACT][
            "owned_quantity"
        ]
        <=
        results[MATCH_PRINTING][
            "owned_quantity"
        ]
    )

    assert (
        results[MATCH_PRINTING][
            "owned_quantity"
        ]
        <=
        results[MATCH_CARD][
            "owned_quantity"
        ]
    )

    print()
    print(
        "Matching-mode monotonicity: PASS"
    )


# ============================================================
# MAIN
# ============================================================

def main():

    print()
    print("=" * 60)
    print("MOXFIELD MATCHING ENGINE TEST")
    print("=" * 60)

    print()
    print("Running synthetic tests...")

    test_basic_land_quantity()
    print("  Basic land quantity: PASS")

    test_quantity_exceeds_inventory()
    print("  Inventory shortage: PASS")

    test_arbitrary_copy_count()
    print("  Arbitrary copy count: PASS")

    test_no_double_counting()
    print("  No double counting: PASS")

    test_multiple_printings()
    print("  Multiple printings: PASS")

    test_exact_printing()
    print("  Exact printing: PASS")

    test_exact_finish()
    print("  Exact finish: PASS")

    test_printing_ignores_finish()
    print("  Printing finish flexibility: PASS")

    test_card_uses_all_printings()
    print("  Card-level printing aggregation: PASS")

    print()
    print(
        "All synthetic tests passed."
    )

    test_real_deck()

    print()
    print("=" * 60)
    print("ALL MATCHING TESTS PASSED")
    print("=" * 60)
    print()


if __name__ == "__main__":
    main()