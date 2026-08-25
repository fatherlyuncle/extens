import json
from pathlib import Path


# ============================================================
# FILE CONFIGURATION
# ============================================================

BASE_DIR = Path(__file__).resolve().parent

INPUT_FILE = BASE_DIR / "moxfield" / "testdeck.json"

OUTPUT_FILE = (
    BASE_DIR
    / "moxfield"
    / "testdeck_normalized.json"
)


# ============================================================
# BOARD EXTRACTION
# ============================================================

def get_board_cards(deck, board_name):
    """
    Return the card map for a specific Moxfield board.

    Moxfield's current v3 deck response stores cards under:

        boards
            └── <board_name>
                    └── cards

    An empty dictionary is returned if the board does not exist.
    """

    boards = deck.get("boards", {})

    if not isinstance(boards, dict):
        raise ValueError(
            "Deck response does not contain a valid 'boards' object."
        )

    board = boards.get(board_name, {})

    if not isinstance(board, dict):
        return {}

    cards = board.get("cards", {})

    if cards is None:
        return {}

    if not isinstance(cards, dict):
        raise ValueError(
            f"Board '{board_name}' does not contain "
            "a valid 'cards' object."
        )

    return cards


# ============================================================
# CARD NORMALIZATION
# ============================================================

def normalize_card(card_id, entry):
    """
    Convert one raw Moxfield deck card entry into the
    simplified representation used by the test fixture.

    The raw Moxfield entry contains considerably more data.
    Only the fields needed for deck/collection comparison
    are retained here.
    """

    if not isinstance(entry, dict):
        raise ValueError(
            f"Invalid card entry for '{card_id}'."
        )

    card = entry.get("card")

    if not isinstance(card, dict):
        raise ValueError(
            f"Card entry '{card_id}' does not contain "
            "a valid card object."
        )

    name = card.get("name")

    if not name:
        raise ValueError(
            f"Card entry '{card_id}' does not contain "
            "a card name."
        )

    quantity = entry.get("quantity", 1)

    if quantity is None:
        quantity = 1

    if not isinstance(quantity, int):
        raise ValueError(
            f"Invalid quantity for '{name}': {quantity!r}"
        )

    if quantity < 1:
        raise ValueError(
            f"Invalid quantity for '{name}': {quantity}"
        )

    finish = entry.get("finish")

    scryfall_id = card.get("scryfall_id")

    return {
        "name": name,
        "quantity": quantity,
        "finish": finish,
        "scryfall_id": scryfall_id,
    }


def normalize_board(cards):
    """
    Normalize all cards in a Moxfield board.

    The output remains a list because the deck fixture represents
    individual deck entries rather than an ownership aggregate.
    """

    normalized = []

    for card_id, entry in cards.items():

        normalized.append(
            normalize_card(
                card_id,
                entry,
            )
        )

    # --------------------------------------------------------
    # Deterministic ordering.
    # --------------------------------------------------------

    normalized.sort(
        key=lambda card: (
            card["name"].lower(),
            str(card["scryfall_id"] or "").lower(),
            str(card["finish"] or "").lower(),
        )
    )

    return normalized


# ============================================================
# DECK NORMALIZATION
# ============================================================

def normalize_deck(deck):
    """
    Normalize the Commander and Mainboard portions of a
    Moxfield deck.

    Sideboard, considering/maybeboard, companions, and all
    other boards are intentionally excluded.
    """

    commander_cards = get_board_cards(
        deck,
        "commanders",
    )

    mainboard_cards = get_board_cards(
        deck,
        "mainboard",
    )

    normalized = {
        "name": deck.get("name"),
        "format": deck.get("format"),
        "commander": normalize_board(
            commander_cards
        ),
        "mainboard": normalize_board(
            mainboard_cards
        ),
    }

    return normalized


# ============================================================
# VALIDATION
# ============================================================

def validate_deck(
    raw_deck,
    normalized_deck,
):
    """
    Verify that normalization preserved the Commander and
    Mainboard card quantities.

    Sideboard and other boards are intentionally ignored.
    """

    raw_commanders = get_board_cards(
        raw_deck,
        "commanders",
    )

    raw_mainboard = get_board_cards(
        raw_deck,
        "mainboard",
    )

    raw_commander_quantity = sum(
        entry.get("quantity", 1)
        for entry in raw_commanders.values()
    )

    raw_mainboard_quantity = sum(
        entry.get("quantity", 1)
        for entry in raw_mainboard.values()
    )

    normalized_commander_quantity = sum(
        card["quantity"]
        for card in normalized_deck["commander"]
    )

    normalized_mainboard_quantity = sum(
        card["quantity"]
        for card in normalized_deck["mainboard"]
    )

    print()
    print("=" * 60)
    print("VALIDATION")
    print("=" * 60)

    # --------------------------------------------------------
    # Commander
    # --------------------------------------------------------

    print()
    print(
        f"Commander records:           "
        f"{len(raw_commanders)}"
    )

    print(
        f"Commander quantity (raw):    "
        f"{raw_commander_quantity}"
    )

    print(
        f"Commander quantity "
        f"(normalized):               "
        f"{normalized_commander_quantity}"
    )

    if (
        raw_commander_quantity
        != normalized_commander_quantity
    ):
        raise RuntimeError(
            "Commander quantity was not preserved."
        )

    print("Commander quantity: PASS")

    # --------------------------------------------------------
    # Mainboard
    # --------------------------------------------------------

    print()
    print(
        f"Mainboard records:            "
        f"{len(raw_mainboard)}"
    )

    print(
        f"Mainboard quantity (raw):     "
        f"{raw_mainboard_quantity}"
    )

    print(
        f"Mainboard quantity "
        f"(normalized):                "
        f"{normalized_mainboard_quantity}"
    )

    if (
        raw_mainboard_quantity
        != normalized_mainboard_quantity
    ):
        raise RuntimeError(
            "Mainboard quantity was not preserved."
        )

    print("Mainboard quantity: PASS")

    # --------------------------------------------------------
    # Combined deck
    # --------------------------------------------------------

    raw_total = (
        raw_commander_quantity
        + raw_mainboard_quantity
    )

    normalized_total = (
        normalized_commander_quantity
        + normalized_mainboard_quantity
    )

    print()
    print(
        f"Deck quantity (raw):          "
        f"{raw_total}"
    )

    print(
        f"Deck quantity (normalized):   "
        f"{normalized_total}"
    )

    if raw_total != normalized_total:
        raise RuntimeError(
            "Total deck quantity was not preserved."
        )

    print("Total deck quantity: PASS")

    print()
    print(
        "PASS: Commander and Mainboard "
        "quantities fully preserved."
    )


# ============================================================
# FILE I/O
# ============================================================

def load_raw_deck():
    """
    Load the immutable raw Moxfield deck fixture.
    """

    if not INPUT_FILE.exists():
        raise FileNotFoundError(
            f"Raw deck file not found:\n{INPUT_FILE}"
        )

    with open(
        INPUT_FILE,
        "r",
        encoding="utf-8",
    ) as f:
        deck = json.load(f)

    if not isinstance(deck, dict):
        raise ValueError(
            "Expected testdeck.json to contain "
            "a JSON object."
        )

    return deck


def write_normalized_deck(deck):
    """
    Write the normalized deck to a separate file.
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
            deck,
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
    print("MOXFIELD DECK NORMALIZER")
    print("=" * 60)

    # --------------------------------------------------------
    # Load raw master fixture
    # --------------------------------------------------------

    print()
    print("Loading raw deck:")
    print(INPUT_FILE)

    raw_deck = load_raw_deck()

    print(
        f"Deck: {raw_deck.get('name')}"
    )

    print(
        f"Format: {raw_deck.get('format')}"
    )

    # --------------------------------------------------------
    # Normalize
    # --------------------------------------------------------

    print()
    print("Normalizing Commander and Mainboard...")

    normalized_deck = normalize_deck(
        raw_deck
    )

    # --------------------------------------------------------
    # Validation
    # --------------------------------------------------------

    validate_deck(
        raw_deck,
        normalized_deck,
    )

    # --------------------------------------------------------
    # Output
    # --------------------------------------------------------

    write_normalized_deck(
        normalized_deck
    )

    commander_count = sum(
        card["quantity"]
        for card in normalized_deck["commander"]
    )

    mainboard_count = sum(
        card["quantity"]
        for card in normalized_deck["mainboard"]
    )

    print()
    print("=" * 60)
    print("NORMALIZATION COMPLETE")
    print("=" * 60)

    print()
    print(f"Commander quantity: {commander_count}")
    print(f"Mainboard quantity: {mainboard_count}")
    print(
        f"Total quantity:     "
        f"{commander_count + mainboard_count}"
    )

    print()
    print("Normalized deck written to:")
    print(OUTPUT_FILE)

    print()


if __name__ == "__main__":
    main()