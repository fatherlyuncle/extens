import requests

URL = "https://api2.moxfield.com/v1/startup/authenticated"

COOKIES = {
    "refresh_token":  "82d527a9-b1db-41ac-a802-2592996e389d",
    "refresh_token_wBJR2":  "82d527a9-b1db-41ac-a802-2592996e389d",
    "logged_in": "true",
}

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:153.0) "
        "Gecko/20100101 Firefox/153.0"
    ),
    "Accept": "application/json, text/plain, */*",
    "Accept-Language": "en-US,en;q=0.9",
    "Content-Type": "application/json",
    "x-moxfield-version": "2026.08.11.1",
    "Origin": "https://moxfield.com",
    "Referer": "https://moxfield.com/",
}

response = requests.post(
    URL,
    headers=HEADERS,
    cookies=COOKIES,
    json={"isAppLogin": False},
    timeout=30,
)

print("HTTP status:", response.status_code)
print()
print(response.text)