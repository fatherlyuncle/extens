import json
from pathlib import Path


# ============================================================
# MATCHING MODES
# ============================================================

MATCH_EXACT = "exact"
MATCH_PRINTING = "printing"
MATCH_CARD = "card"

VALID_MATCHING_MODES = {
    MATCH_EXACT,
    MATCH_PRINTING,
    MATCH_CARD,
}


# ============================================================
# DATA LOADING
# ============================================================

def load_json(path):
    """
    Load a JSON file and return its contents.
    """

    path = Path(path)

    with open(
        path,
        "r",
        encoding="utf-8",
    ) as f:
        return json.load(f)


# ============================================================
# COLLECTION INVENTORY
# ============================================================

def build_collection_inventory(collection):
    """
    Build a mutable inventory from the normalized collection.

    Each inventory entry represents owned physical copies.

    The inventory is keyed by:

        card name
        Scryfall ID
        finish

    Quantities are mutable and are consumed as deck
    requirements are satisfied.
    """

    inventory = {
        "by_name": {},
        "by_scryfall_id": {},
        "by_scryfall_id_and_finish": {},
    }

    for card in collection:

        name = card["name"]

        # ----------------------------------------------------
        # Card-level inventory
        # ----------------------------------------------------

        inventory["by_name"][name] = {
            "total_quantity": card["total_quantity"],
        }

        # ----------------------------------------------------
        # Printing-level inventory
        # ----------------------------------------------------

        for printing in card.get(
            "unique_printings",
            [],
        ):

            scryfall_id = printing.get(
                "scryfall_id"
            )

            finish = printing.get(
                "finish"
            )

            quantity = printing.get(
                "quantity",
                0,
            )

            if not scryfall_id:
                continue

            # ------------------------------------------------
            # Scryfall ID
            # ------------------------------------------------

            inventory[
                "by_scryfall_id"
            ].setdefault(
                scryfall_id,
                0,
            )

            inventory[
                "by_scryfall_id"
            ][scryfall_id] += quantity

            # ------------------------------------------------
            # Scryfall ID + finish
            # ------------------------------------------------

            key = (
                scryfall_id,
                finish,
            )

            inventory[
                "by_scryfall_id_and_finish"
            ].setdefault(
                key,
                0,
            )

            inventory[
                "by_scryfall_id_and_finish"
            ][key] += quantity

    return inventory


# ============================================================
# INVENTORY CONSUMPTION
# ============================================================

def consume_inventory(
    inventory,
    deck_card,
    quantity_needed,
    matching_mode,
):
    """
    Consume owned inventory to satisfy a deck-card requirement.

    Returns the number of copies successfully allocated.

    Every allocated copy is removed from the available
    inventory, preventing the same physical cards from being
    used to satisfy another deck requirement.
    """

    if quantity_needed <= 0:
        return 0

    if matching_mode not in VALID_MATCHING_MODES:
        raise ValueError(
            f"Unknown matching mode: {matching_mode!r}"
        )

    # --------------------------------------------------------
    # EXACT
    # --------------------------------------------------------

    if matching_mode == MATCH_EXACT:

        scryfall_id = deck_card.get(
            "scryfall_id"
        )

        finish = deck_card.get(
            "finish"
        )

        if not scryfall_id:
            return 0

        key = (
            scryfall_id,
            finish,
        )

        available = inventory[
            "by_scryfall_id_and_finish"
        ].get(
            key,
            0,
        )

        allocated = min(
            quantity_needed,
            available,
        )

        if allocated:
            inventory[
                "by_scryfall_id_and_finish"
            ][key] -= allocated

            # Keep the broader printing inventory synchronized.
            inventory[
                "by_scryfall_id"
            ][scryfall_id] -= allocated

            # Keep card-level inventory synchronized.
            name = deck_card["name"]

            if name in inventory["by_name"]:
                inventory["by_name"][name][
                    "total_quantity"
                ] -= allocated

        return allocated

    # --------------------------------------------------------
    # PRINTING
    # --------------------------------------------------------

    if matching_mode == MATCH_PRINTING:

        scryfall_id = deck_card.get(
            "scryfall_id"
        )

        if not scryfall_id:
            return 0

        available = inventory[
            "by_scryfall_id"
        ].get(
            scryfall_id,
            0,
        )

        allocated = min(
            quantity_needed,
            available,
        )

        if allocated:
            inventory[
                "by_scryfall_id"
            ][scryfall_id] -= allocated

            name = deck_card["name"]

            if name in inventory["by_name"]:
                inventory["by_name"][name][
                    "total_quantity"
                ] -= allocated

            # Consume the copies from the finish-level
            # inventory as well.
            remaining = allocated

            for key in list(
                inventory[
                    "by_scryfall_id_and_finish"
                ]
            ):

                if remaining <= 0:
                    break

                key_scryfall_id, finish = key

                if key_scryfall_id != scryfall_id:
                    continue

                available_finish = inventory[
                    "by_scryfall_id_and_finish"
                ][key]

                consume = min(
                    remaining,
                    available_finish,
                )

                inventory[
                    "by_scryfall_id_and_finish"
                ][key] -= consume

                remaining -= consume

        return allocated

    # --------------------------------------------------------
    # CARD
    # --------------------------------------------------------

    if matching_mode == MATCH_CARD:

        name = deck_card["name"]

        card_inventory = inventory[
            "by_name"
        ].get(name)

        if card_inventory is None:
            return 0

        available = card_inventory[
            "total_quantity"
        ]

        allocated = min(
            quantity_needed,
            available,
        )

        if allocated:
            card_inventory[
                "total_quantity"
            ] -= allocated

            # Consume the allocated quantity from the underlying
            # printing inventories too.
            remaining = allocated

            for scryfall_id in list(
                inventory[
                    "by_scryfall_id"
                ]
            ):

                if remaining <= 0:
                    break

                # Find whether this printing belongs to the card.
                printing_quantity = 0

                for (
                    key,
                    quantity,
                ) in inventory[
                    "by_scryfall_id_and_finish"
                ].items():

                    key_scryfall_id, finish = key

                    if key_scryfall_id != scryfall_id:
                        continue

                    printing_quantity += quantity

                if printing_quantity <= 0:
                    continue

                consume_from_printing = min(
                    remaining,
                    printing_quantity,
                )

                inventory[
                    "by_scryfall_id"
                ][scryfall_id] -= (
                    consume_from_printing
                )

                finish_remaining = (
                    consume_from_printing
                )

                for key in list(
                    inventory[
                        "by_scryfall_id_and_finish"
                    ]
                ):

                    if finish_remaining <= 0:
                        break

                    key_scryfall_id, finish = key

                    if key_scryfall_id != scryfall_id:
                        continue

                    available_finish = inventory[
                        "by_scryfall_id_and_finish"
                    ][key]

                    consume = min(
                        finish_remaining,
                        available_finish,
                    )

                    inventory[
                        "by_scryfall_id_and_finish"
                    ][key] -= consume

                    finish_remaining -= consume

                remaining -= (
                    consume_from_printing
                )

        return allocated

    raise RuntimeError(
        "Unexpected matching mode."
    )


# ============================================================
# DECK ANALYSIS
# ============================================================

def analyze_deck(
    deck,
    collection,
    matching_mode=MATCH_EXACT,
):
    """
    Compare a normalized deck against a normalized collection.

    Collection quantities are consumed as they are allocated.

    Commander and Mainboard are included.

    Sideboard and Considering are intentionally ignored.
    """

    inventory = build_collection_inventory(
        collection
    )

    results = []

    # --------------------------------------------------------
    # IMPORTANT:
    #
    # More restrictive requirements are processed first.
    # This prevents a broad requirement from consuming inventory
    # that a more specific requirement could use.
    # --------------------------------------------------------

    deck_cards = []

    for card in deck.get(
        "commander",
        [],
    ):
        deck_cards.append(
            ("commander", card)
        )

    for card in deck.get(
        "mainboard",
        [],
    ):
        deck_cards.append(
            ("mainboard", card)
        )

    # --------------------------------------------------------
    # Analyze every deck entry.
    # --------------------------------------------------------

    for board, card in deck_cards:

        result = analyze_card(
            card,
            board,
            inventory,
            matching_mode,
        )

        results.append(result)

    # --------------------------------------------------------
    # Summary
    # --------------------------------------------------------

    required_quantity = sum(
        result["required_quantity"]
        for result in results
    )

    owned_quantity = sum(
        result["owned_quantity"]
        for result in results
    )

    missing_quantity = sum(
        result["missing_quantity"]
        for result in results
    )

    return {
        "matching_mode": matching_mode,
        "required_quantity": required_quantity,
        "owned_quantity": owned_quantity,
        "missing_quantity": missing_quantity,
        "cards": results,
    }


def analyze_card(
    deck_card,
    board,
    inventory,
    matching_mode,
):
    """
    Analyze and allocate inventory for one deck card.
    """

    required_quantity = deck_card[
        "quantity"
    ]

    owned_quantity = consume_inventory(
        inventory,
        deck_card,
        required_quantity,
        matching_mode,
    )

    missing_quantity = (
        required_quantity
        - owned_quantity
    )

    return {
        "board": board,
        "name": deck_card["name"],
        "scryfall_id": deck_card.get(
            "scryfall_id"
        ),
        "finish": deck_card.get(
            "finish"
        ),
        "required_quantity": required_quantity,
        "owned_quantity": owned_quantity,
        "missing_quantity": missing_quantity,
    }


# ============================================================
# CONVENIENCE FUNCTION
# ============================================================

def analyze_deck_files(
    deck_path,
    collection_path,
    matching_mode=MATCH_EXACT,
):
    """
    Load normalized deck and collection files and analyze them.
    """

    deck = load_json(deck_path)
    collection = load_json(collection_path)

    return analyze_deck(
        deck,
        collection,
        matching_mode,
    )


# ============================================================
# DISPLAY
# ============================================================

def print_analysis(result):
    """
    Print a human-readable ownership analysis.
    """

    print()
    print("=" * 60)
    print("DECK OWNERSHIP ANALYSIS")
    print("=" * 60)

    print()
    print(
        f"Matching mode:      "
        f"{result['matching_mode']}"
    )

    print(
        f"Required:           "
        f"{result['required_quantity']}"
    )

    print(
        f"Owned:              "
        f"{result['owned_quantity']}"
    )

    print(
        f"Missing:            "
        f"{result['missing_quantity']}"
    )

    print()
    print("-" * 60)
    print("MISSING CARDS")
    print("-" * 60)

    missing_cards = [
        card
        for card in result["cards"]
        if card["missing_quantity"] > 0
    ]

    if not missing_cards:

        print()
        print("None.")

        return

    for card in missing_cards:

        print()
        print(
            f"{card['name']}"
        )

        print(
            f"  Required: "
            f"{card['required_quantity']}"
        )

        print(
            f"  Owned:    "
            f"{card['owned_quantity']}"
        )

        print(
            f"  Missing:  "
            f"{card['missing_quantity']}"
        )