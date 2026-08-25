import json
import time
from pathlib import Path

import requests


# ============================================================
# CONFIGURATION
# ============================================================

MOXFIELD_VERSION = "2026.08.13.2"

# Your Moxfield session user.
SESSION_USER = "wBJR2"

# ------------------------------------------------------------
# CURRENTLY USED FOR TESTING
# ------------------------------------------------------------
#
# This is the collection search ID from the authenticated
# collection endpoint:
#
# /v1/collections/search/Sanl3ABKVUabHXNqVKBnXQ
#
# This will eventually be replaced with logic that discovers
# the user's current collection from their live Moxfield
# session.
#
COLLECTION_SEARCH_ID = "Sanl3ABKVUabHXNqVKBnXQ"

# ------------------------------------------------------------
# UPDATE THESE WHEN YOUR MOXFIELD SESSION CHANGES
# ------------------------------------------------------------

REFRESH_TOKEN = "16773856-c382-451c-89ca-227624e40292"

CF_CLEARANCE = "PM7JOixQ3cvvM3J90rxQSklPmWnfyvu1NYWvIR0qJXE-1786649404-1.2.1.1-KaQJMvTBkVdDrapfBfouk4OCEodwuooCmJJbrEwSUV_lmuXjjRnnh0MRqVLsxOuoBowUqWu7Wey3YJIPc9GJRGTTWlZcBWAccVlB_pDGNZUS9EjpWBGqwvvvFuWvyGq2H44CJizdWfGqBxMJgEz7zuy2f6g2H9X9fhsa.xFqk_PAshPd4LEnUyCYBCaXH5Jc6CPnDJOByoVz_JbUlzo6R_NG9JYH2wX.wn2EBs1.vvrGySqM1ce0gYokbPjfwvyKuHhZyP.G7V8AIiyYh9qLCJV80jCFFyYO.ARP5NTBsQ9lznjbP1Zsu8JEEhH0OziQa_RGDRb0Cs7A5XuT5q1KZ4oxFjgd3NyCgbw3Rr7RLBAT9N5viH7JeRraNRYQVHXgjc46MBPEoBrrTHQvfervvl._sSB2frxlt.QrrOESRDMBPThwrOHk3H0tsvcqsdS18a1z._sz0qgcEfFO5HWd.w"


# ============================================================
# FILE OUTPUT
# ============================================================

BASE_DIR = Path(__file__).resolve().parent

OUTPUT_DIR = BASE_DIR / "moxfield"

OUTPUT_FILE = OUTPUT_DIR / "collection.json"


# ============================================================
# MOXFIELD API
# ============================================================

BASE_URL = "https://api2.moxfield.com"

STARTUP_URL = f"{BASE_URL}/v1/startup/authenticated"

COLLECTION_URL = (
    f"{BASE_URL}/v1/collections/search/"
    f"{COLLECTION_SEARCH_ID}"
)


# ============================================================
# REQUEST SETTINGS
# ============================================================

USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:153.0) "
    "Gecko/20100101 Firefox/153.0"
)

COMMON_HEADERS = {
    "User-Agent": USER_AGENT,
    "Accept": "application/json, text/plain, */*",
    "Accept-Language": "en-US,en;q=0.9",
    "x-moxfield-version": MOXFIELD_VERSION,
    "Origin": "https://moxfield.com",
    "Referer": "https://moxfield.com/",
}


# ============================================================
# AUTHENTICATION
# ============================================================

def authenticate(session):
    """
    Authenticate with Moxfield using the browser refresh token.

    The startup endpoint returns a fresh access token and may
    rotate the refresh token.
    """

    print("=" * 60)
    print("MOXFIELD AUTHENTICATION")
    print("=" * 60)

    if REFRESH_TOKEN == "PASTE_CURRENT_REFRESH_TOKEN_HERE":
        raise RuntimeError(
            "You must paste your current Moxfield refresh token "
            "into REFRESH_TOKEN before running the script."
        )

    if CF_CLEARANCE == "PASTE_CURRENT_CF_CLEARANCE_HERE":
        raise RuntimeError(
            "You must paste your current cf_clearance value "
            "into CF_CLEARANCE before running the script."
        )

    # --------------------------------------------------------
    # Browser session cookies
    # --------------------------------------------------------

    session.cookies.set(
        "refresh_token",
        REFRESH_TOKEN,
        domain=".moxfield.com",
        path="/",
    )

    session.cookies.set(
        f"refresh_token_{SESSION_USER}",
        REFRESH_TOKEN,
        domain=".moxfield.com",
        path="/",
    )

    session.cookies.set(
        "cf_clearance",
        CF_CLEARANCE,
        domain=".moxfield.com",
        path="/",
    )

    session.cookies.set(
        "logged_in",
        "true",
        domain=".moxfield.com",
        path="/",
    )

    headers = {
        **COMMON_HEADERS,
        "Content-Type": "application/json",
    }

    print()
    print("Requesting authenticated startup...")

    response = session.post(
        STARTUP_URL,
        headers=headers,
        json={"isAppLogin": False},
        timeout=30,
    )

    print(f"HTTP status: {response.status_code}")

    if response.status_code != 200:
        print()
        print("Authentication request failed.")
        print()
        print(response.text[:2000])

        raise RuntimeError(
            f"Moxfield authentication failed with HTTP "
            f"{response.status_code}"
        )

    try:
        data = response.json()
    except ValueError:
        print(response.text[:2000])

        raise RuntimeError(
            "Moxfield returned a response that was not valid JSON."
        )

    refresh_data = data.get("refresh")

    if not refresh_data:
        raise RuntimeError(
            "Authentication response did not contain a "
            "'refresh' object."
        )

    access_token = refresh_data.get("access_token")

    if not access_token:
        raise RuntimeError(
            "Authentication response did not contain an "
            "access token."
        )

    # --------------------------------------------------------
    # Moxfield may rotate the refresh token.
    # --------------------------------------------------------

    new_refresh_token = refresh_data.get("refresh_token")

    if new_refresh_token:
        session.cookies.set(
            "refresh_token",
            new_refresh_token,
            domain=".moxfield.com",
            path="/",
        )

        session.cookies.set(
            f"refresh_token_{SESSION_USER}",
            new_refresh_token,
            domain=".moxfield.com",
            path="/",
        )

    username = refresh_data.get("user_name")
    user_id = refresh_data.get("user_id")
    expiration = refresh_data.get("expiration")

    print()
    print("Authentication successful.")
    print(f"Username:       {username}")
    print(f"User ID:        {user_id}")
    print(f"Session user:   {SESSION_USER}")
    print(f"Token expires:  {expiration}")

    if new_refresh_token:
        print("Refresh token:  rotated by Moxfield")

    return access_token


# ============================================================
# COLLECTION REQUEST
# ============================================================

def get_collection_page(
    session,
    access_token,
    page_number,
    page_size=50,
):
    """
    Retrieve one page from the user's collection.

    This uses the collection-specific search endpoint rather
    than Moxfield's generic collection-search initialization
    endpoint.
    """

    params = {
        "sortType": "cardName",
        "sortDirection": "ascending",
        "pageNumber": page_number,
        "pageSize": page_size,
        "pricingProvider": "cardkingdom",
    }

    headers = {
        **COMMON_HEADERS,
        "Authorization": f"Bearer {access_token}",
        "X-Session-User": SESSION_USER,
    }

    response = session.get(
        COLLECTION_URL,
        params=params,
        headers=headers,
        timeout=30,
    )

    return response


# ============================================================
# COLLECTION COMPILER
# ============================================================

def compile_collection(session, access_token):
    """
    Retrieve every record from the collection.

    Moxfield provides totalResults and totalPages in the
    response, so pagination is deterministic.
    """

    print()
    print("=" * 60)
    print("COLLECTION RETRIEVAL")
    print("=" * 60)

    page_size = 50
    page_number = 1

    all_records = []

    expected_records = None
    expected_quantity = None
    total_pages = None

    while True:

        print()
        print(
            f"Requesting page {page_number}...",
            end=" ",
            flush=True,
        )

        response = get_collection_page(
            session,
            access_token,
            page_number,
            page_size,
        )

        print(f"HTTP status: {response.status_code}")

        if response.status_code != 200:
            print()
            print("Collection request failed.")
            print(response.text[:2000])

            raise RuntimeError(
                f"Collection request failed with HTTP "
                f"{response.status_code} on page {page_number}"
            )

        try:
            data = response.json()
        except ValueError:
            print(response.text[:2000])

            raise RuntimeError(
                f"Collection page {page_number} "
                "was not valid JSON."
            )

        # ----------------------------------------------------
        # Read collection metadata from the first response.
        # ----------------------------------------------------

        if expected_records is None:

            expected_records = data.get("totalResults")

            expected_quantity = data.get("totalOverall")

            total_pages = data.get("totalPages")

            page_size = data.get("pageSize", page_size)

            if expected_records is None:
                raise RuntimeError(
                    "Moxfield response did not contain "
                    "'totalResults'."
                )

            if expected_quantity is None:
                raise RuntimeError(
                    "Moxfield response did not contain "
                    "'totalOverall'."
                )

            if total_pages is None:
                raise RuntimeError(
                    "Moxfield response did not contain "
                    "'totalPages'."
                )

            print()
            print(f"Total collection records: {expected_records}")
            print(f"Total card quantity:       {expected_quantity}")
            print(f"Page size:                  {page_size}")
            print(f"Total pages:                {total_pages}")

            if data.get("isEmpty") is True:

                if expected_records != 0:
                    raise RuntimeError(
                        "Moxfield reported isEmpty=True but "
                        "totalResults is non-zero."
                    )

                print()
                print("Moxfield reports an empty collection.")

                return {
                    "records": [],
                    "expected_records": 0,
                    "expected_quantity": 0,
                    "total_pages": 0,
                }

        records = data.get("data")

        if not isinstance(records, list):
            raise RuntimeError(
                f"Moxfield response for page {page_number} "
                "did not contain a 'data' list."
            )

        print(
            f"Records returned on page {page_number}: "
            f"{len(records)}"
        )

        # ----------------------------------------------------
        # A page other than the final page should never be
        # empty.
        # ----------------------------------------------------

        if not records:

            if page_number < total_pages:

                raise RuntimeError(
                    f"Moxfield returned an empty page "
                    f"({page_number}) before the reported "
                    f"final page ({total_pages})."
                )

            break

        all_records.extend(records)

        # ----------------------------------------------------
        # Stop when the final page has been retrieved.
        # ----------------------------------------------------

        if page_number >= total_pages:
            break

        page_number += 1

        # Be polite to the API.
        time.sleep(0.15)

    return {
        "records": all_records,
        "expected_records": expected_records,
        "expected_quantity": expected_quantity,
        "total_pages": total_pages,
    }


# ============================================================
# VALIDATION
# ============================================================

def validate_collection(result):
    """
    Validate both collection record count and total quantity.
    """

    print()
    print("=" * 60)
    print("VALIDATION")
    print("=" * 60)

    records = result["records"]

    expected_records = result["expected_records"]
    expected_quantity = result["expected_quantity"]

    actual_records = len(records)

    actual_quantity = sum(
        record.get("quantity", 0)
        for record in records
    )

    # --------------------------------------------------------
    # Record-count validation
    # --------------------------------------------------------

    print()
    print(f"Records retrieved: {actual_records}")
    print(f"Records expected:  {expected_records}")

    records_passed = actual_records == expected_records

    if records_passed:
        print("Record count: PASS")
    else:
        difference = expected_records - actual_records

        print("Record count: FAIL")
        print(f"Record difference: {difference}")

    # --------------------------------------------------------
    # Quantity validation
    # --------------------------------------------------------

    print()
    print(f"Quantity retrieved: {actual_quantity}")
    print(f"Quantity expected:  {expected_quantity}")

    quantity_passed = actual_quantity == expected_quantity

    if quantity_passed:
        print("Quantity total: PASS")
    else:
        difference = expected_quantity - actual_quantity

        print("Quantity total: FAIL")
        print(f"Quantity difference: {difference}")

    # --------------------------------------------------------
    # Overall result
    # --------------------------------------------------------

    print()

    if records_passed and quantity_passed:
        print("PASS: Collection fully validated.")
        return True

    print("WARNING: Collection validation failed.")

    return False


# ============================================================
# WRITE OUTPUT
# ============================================================

def write_collection(records):
    """
    Write the complete raw collection records to collection.json.

    The Moxfield record structure is preserved so this file can
    later be used as a test fixture.
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
            records,
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
    print("MOXFIELD COLLECTION COMPILER")
    print("=" * 60)

    print()
    print(f"Collection search ID: {COLLECTION_SEARCH_ID}")

    session = requests.Session()

    # --------------------------------------------------------
    # Authentication
    # --------------------------------------------------------

    access_token = authenticate(session)

    # --------------------------------------------------------
    # Collection
    # --------------------------------------------------------

    result = compile_collection(
        session,
        access_token,
    )

    records = result["records"]

    expected_records = result["expected_records"]
    expected_quantity = result["expected_quantity"]

    # --------------------------------------------------------
    # Validation
    # --------------------------------------------------------

    validation_passed = validate_collection(result)

    # --------------------------------------------------------
    # Output
    # --------------------------------------------------------

    print()
    print("=" * 60)
    print("COMPILATION COMPLETE")
    print("=" * 60)

    print()
    print(f"Total records:    {len(records)}")
    print(f"Expected records: {expected_records}")

    actual_quantity = sum(
        record.get("quantity", 0)
        for record in records
    )

    print(f"Total quantity:   {actual_quantity}")
    print(f"Expected quantity: {expected_quantity}")

    if validation_passed:
        print()
        print("Validation: PASS")
    else:
        print()
        print("Validation: WARNING")

    # --------------------------------------------------------
    # Write collection fixture
    # --------------------------------------------------------

    write_collection(records)

    print()
    print("Raw collection written to:")
    print(OUTPUT_FILE)

    print()


if __name__ == "__main__":
    main()