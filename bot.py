import requests
import os
from bs4 import BeautifulSoup

WEBHOOK_URL = os.environ.get("DISCORD_WEBHOOK")

HEADERS = {
    "User-Agent": "Mozilla/5.0"
}

SEARCHES = [
    ("Walmart", "https://www.walmart.com/search?q=needoh&zip=23320"),
    ("Target", "https://www.target.com/s?searchTerm=needoh"),
    ("Five Below", "https://www.fivebelow.com/search?q=needoh"),
    ("Walgreens", "https://www.walgreens.com/search/results.jsp?Ntt=needoh")
]


def scrape_store(name, url):
    try:
        res = requests.get(url, headers=HEADERS, timeout=10)
        soup = BeautifulSoup(res.text, "html.parser")

        text = soup.get_text(" ", strip=True).lower()

        if "needoh" in text:
            return [f"{name}: possible squishy found → {url}"]

        return []

    except Exception:
        return [f"{name}: error checking site"]


def send_to_discord(results):
    if results:
        message = "🚨 Squishy Check:\n\n" + "\n\n".join(results)
    else:
        message = "🚨 Squishy Check:\n\nNo squishies found right now."

    requests.post(
        WEBHOOK_URL,
        json={"content": message[:2000]}
    )


if __name__ == "__main__":
    all_results = []

    for name, url in SEARCHES:
        results = scrape_store(name, url)
        print(name, results)  # debug in GitHub Actions logs
        all_results.extend(results)

    print("FINAL RESULTS:", all_results)

    send_to_discord(all_results)
