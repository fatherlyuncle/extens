import requests

URL = "https://api2.moxfield.com/v1/collections/search"

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

# Paste ONLY your current access token between the quotes.
ACCESS_TOKEN = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJhdWQiOiJ1c3IiLCJpc3MiOiJodHRwczovL21veGZpZWxkLWFwaS5henVyZXdlYnNpdGVzLm5ldC8iLCJleHAiOjE3ODY0NzkyNzEsImlhdCI6MTc4NjQ3ODM3MSwibmJmIjoxNzg2NDc4MzcxLCJzdWIiOiJzaHJvb21jbG91ZHMiLCJqdGkiOiI0MjMyMWFjNi0xMDYxLTRiYzktOGM2Yy1iYzM5YTRmNGFlMjkiLCJodHRwOi8vd3d3Lm1veGZpZWxkLmNvbS93cy8yMDE2LzA4L2lkZW50aXR5L2NsYWltcy9Vc2VySWQiOiI5MTc5OTAiLCJhZHVsdCI6ImFhYzEwNzBjLTc0ZWYtNGRhYi05NWU5LTU3NzJmMTg3MjUzMyJ9.VFi9I4RUQfXc8C8-aU_u4KNFjwJ7kPyECsjDKtlQMyk"

# Paste your current session-user value here.
SESSION_USER = "wBJR2"

# If the request still returns 0 records, we can add the
# browser cookies afterward.
COOKIES = {
    "cf_clearance": "YOUR_CURRENT_CF_CLEARANCE",
    "refresh_token": "YOUR_CURRENT_REFRESH_TOKEN",
    "refresh_token_wBJR2": "YOUR_CURRENT_REFRESH_TOKEN",
    "logged_in": "true",
}

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:153.0) "
        "Gecko/20100101 Firefox/153.0"
    ),
    "Accept": "application/json, text/plain, */*",
    "Accept-Language": "en-US,en;q=0.9",
    "x-moxfield-version": "2026.08.11.1",
    "Authorization": f"Bearer {ACCESS_TOKEN}",
    "X-Session-User": SESSION_USER,
    "Origin": "https://moxfield.com",
    "Referer": "https://moxfield.com/",
}


def main():
    print("Requesting Moxfield collection...")
    print()

    response = requests.get(
        URL,
        params=PARAMS,
        headers=HEADERS,
        cookies=COOKIES,
        timeout=30,
    )

    print("HTTP status:", response.status_code)
    print("Final URL:", response.url)
    print()

    print("Response:")
    print(response.text[:2000])
    print()

    if not response.ok:
        print("REQUEST FAILED")
        return

    data = response.json()

    print("totalOverall:", data.get("totalOverall"))
    print("totalResults:", data.get("totalResults"))
    print("totalPages:", data.get("totalPages"))
    print("pageNumber:", data.get("pageNumber"))
    print("pageSize:", data.get("pageSize"))
    print("hasMore:", data.get("hasMore"))

    records = data.get("data", [])

    print()
    print("Records returned:", len(records))

    if records:
        print()
        print("First record:")
        print(records[0])


if __name__ == "__main__":
    main()