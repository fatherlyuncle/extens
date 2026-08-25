import json
from pathlib import Path

import requests


# ============================================================
# CONFIGURATION
# ============================================================

MOXFIELD_VERSION = "2026.08.13.2"

# Public Moxfield deck:
# https://moxfield.com/decks/v35AP7qQd0-Lj7XVg7UmBA
DECK_ID = "v35AP7qQd0-Lj7XVg7UmBA"


# ============================================================
# FILE OUTPUT
# ============================================================

BASE_DIR = Path(__file__).resolve().parent

OUTPUT_DIR = BASE_DIR / "moxfield"

OUTPUT_FILE = OUTPUT_DIR / "testdeck.json"


# ============================================================
# MOXFIELD API
# ============================================================

BASE_URL = "https://api2.moxfield.com"

DECK_URL = f"{BASE_URL}/v3/decks/all/{DECK_ID}"


# ============================================================
# REQUEST SETTINGS
# ============================================================

USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:153.0) "
    "Gecko/20100101 Firefox/153.0"
)

HEADERS = {
    "User-Agent": USER_AGENT,
    "Accept": "application/json, text/plain, */*",
    "Accept-Language": "en-US,en;q=0.9",
    "x-moxfield-version": MOXFIELD_VERSION,
    "Origin": "https://moxfield.com",
    "Referer": "https://moxfield.com/",
}


# ============================================================
# DECK RETRIEVAL
# ============================================================

def get_deck():
    """
    Retrieve the complete raw JSON response for the public
    Moxfield deck.
    """

    print()
    print("Requesting public Moxfield deck...")
    print(f"Deck ID: {DECK_ID}")
    print()

    response = requests.get(
        DECK_URL,
        headers=HEADERS,
        timeout=30,
    )

    print(f"HTTP status: {response.status_code}")

    if response.status_code != 200:
        print()
        print("Deck request failed.")
        print()
        print(response.text[:2000])

        raise RuntimeError(
            f"Moxfield deck request failed with HTTP "
            f"{response.status_code}"
        )

    try:
        data = response.json()
    except ValueError:
        print()
        print("Moxfield returned invalid JSON.")
        print()
        print(response.text[:2000])

        raise RuntimeError(
            "Moxfield returned a response that was not valid JSON."
        )

    if not isinstance(data, dict):
        raise RuntimeError(
            "Expected Moxfield deck response to be a JSON object."
        )

    return data


# ============================================================
# BASIC VALIDATION / INFORMATION
# ============================================================

def inspect_deck(data):
    """
    Print basic information from the raw deck response.

    This does NOT modify the response.
    """

    print()
    print("=" * 60)
    print("DECK INFORMATION")
    print("=" * 60)

    print()

    print(f"Name:   {data.get('name')}")
    print(f"Format: {data.get('format')}")
    print(f"ID:     {data.get('id')}")

    # --------------------------------------------------------
    # Moxfield currently exposes deck cards through board
    # dictionaries. Support both the legacy top-level structure
    # and the newer boards structure when reporting counts.
    # --------------------------------------------------------

    if "mainboard" in data:
        mainboard = data.get("mainboard") or {}
        commanders = data.get("commanders") or {}
        sideboard = data.get("sideboard") or {}

    else:
        boards = data.get("boards") or {}

        mainboard = (
            boards.get("mainboard", {}).get("cards", {})
        )

        commanders = (
            boards.get("commanders", {}).get("cards", {})
        )

        sideboard = (
            boards.get("sideboard", {}).get("cards", {})
        )

    print()
    print(f"Commander records: {len(commanders)}")
    print(f"Mainboard records: {len(mainboard)}")
    print(f"Sideboard records: {len(sideboard)}")

    commander_quantity = sum(
        entry.get("quantity", 1)
        for entry in commanders.values()
    )

    mainboard_quantity = sum(
        entry.get("quantity", 1)
        for entry in mainboard.values()
    )

    sideboard_quantity = sum(
        entry.get("quantity", 1)
        for entry in sideboard.values()
    )

    print()
    print(f"Commander quantity: {commander_quantity}")
    print(f"Mainboard quantity: {mainboard_quantity}")
    print(f"Sideboard quantity: {sideboard_quantity}")

    print()
    print(
        f"Total deck quantity: "
        f"{commander_quantity + mainboard_quantity + sideboard_quantity}"
    )


# ============================================================
# WRITE RAW OUTPUT
# ============================================================

def write_deck(data):
    """
    Write the complete raw Moxfield response to testdeck.json.

    No normalization or transformation is performed.
    """

    OUTPUT_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    with open(
        OUTPUT_FILE,
        "w",
        encoding="utf-8",
    ) as f:
        json.dump(
            data,
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
    print("MOXFIELD DECK COMPILER")
    print("=" * 60)

    print()
    print(f"Deck URL:")
    print(
        f"https://moxfield.com/decks/{DECK_ID}"
    )

    # --------------------------------------------------------
    # Retrieve raw deck
    # --------------------------------------------------------

    data = get_deck()

    # --------------------------------------------------------
    # Basic inspection
    # --------------------------------------------------------

    inspect_deck(data)

    # --------------------------------------------------------
    # Write raw fixture
    # --------------------------------------------------------

    write_deck(data)

    print()
    print("=" * 60)
    print("COMPILATION COMPLETE")
    print("=" * 60)

    print()
    print("Raw deck written to:")
    print(OUTPUT_FILE)

    print()


if __name__ == "__main__":
    main()