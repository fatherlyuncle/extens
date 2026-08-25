import json
from pathlib import Path

import requests


ACCESS_TOKEN = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJhdWQiOiJ1c3IiLCJpc3MiOiJodHRwczovL21veGZpZWxkLWFwaS5henVyZXdlYnNpdGVzLm5ldC8iLCJleHAiOjE3ODY0NzkyNzEsImlhdCI6MTc4NjQ3ODM3MSwibmJmIjoxNzg2NDc4MzcxLCJzdWIiOiJzaHJvb21jbG91ZHMiLCJqdGkiOiI0MjMyMWFjNi0xMDYxLTRiYzktOGM2Yy1iYzM5YTRmNGFlMjkiLCJodHRwOi8vd3d3Lm1veGZpZWxkLmNvbS93cy8yMDE2LzA4L2lkZW50aXR5L2NsYWltcy9Vc2VySWQiOiI5MTc5OTAiLCJhZHVsdCI6ImFhYzEwNzBjLTc0ZWYtNGRhYi05NWU5LTU3NzJmMTg3MjUzMyJ9.VFi9I4RUQfXc8C8-aU_u4KNFjwJ7kPyECsjDKtlQMyk"

API_URL = "https://api2.moxfield.com/v1/collections/search"

OUTPUT_FILE = Path(__file__).parent / "moxfield" / "collection-page1-debug.json"


PARAMS = {
    "q": "+",
    "setId": "",
    "deckId": "",
    "rarity": "",
    "condition": "",
    "game": "",
    "cardLanguageId": "",
    "finish": "",
    "isAlter": "",
    "isProxy": "",
    "tradeBinderId": "",
    "pricingProvider": "cardkingdom",
    "priceMinimum": "",
    "priceMaximum": "",
    "pageNumber": 1,
    "pageSize": 50,
    "sortType": "cardName",
    "sortDirection": "ascending",
}


def main():
    headers = {
        "Authorization": f"Bearer {ACCESS_TOKEN}",
        "Accept": "application/json",
        "User-Agent": "extens-moxfield-poc/1.0",
    }

    print()
    print("=" * 60)
    print("MOXFIELD PAGE 1 DIAGNOSTIC")
    print("=" * 60)
    print()

    print("Requesting:")
    print(API_URL)
    print()

    response = requests.get(
        API_URL,
        params=PARAMS,
        headers=headers,
        timeout=30,
    )

    print(f"HTTP status: {response.status_code}")
    print(f"Final URL: {response.url}")
    print()

    if not response.ok:
        print(response.text)
        raise RuntimeError(
            f"Moxfield request failed with HTTP {response.status_code}"
        )

    try:
        data = response.json()
    except ValueError:
        print(response.text)
        raise RuntimeError("Moxfield did not return JSON.")

    OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)

    with OUTPUT_FILE.open("w", encoding="utf-8") as f:
        json.dump(
            data,
            f,
            indent=2,
            ensure_ascii=False,
        )
        f.write("\n")

    print("Top-level response fields:")
    print()

    if isinstance(data, dict):
        for key, value in data.items():
            if isinstance(value, list):
                print(f"  {key}: list ({len(value)} items)")
            elif isinstance(value, dict):
                print(f"  {key}: object")
            else:
                print(f"  {key}: {value!r}")

    print()
    print("Full response written to:")
    print(OUTPUT_FILE)
    print()


if __name__ == "__main__":
    main()