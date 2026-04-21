import requests
import os
from bs4 import BeautifulSoup

WEBHOOK_URL = os.environ.get("DISCORD_WEBHOOK")

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"
}

SEARCHES = [
    ("Walmart", "https://www.walmart.com/search?q=needoh"),
    ("Target", "https://www.target.com/s?searchTerm=needoh"),
    ("Five Below", "https://www.fivebelow.com/search?q=needoh"),
    ("Walgreens", "https://www.walgreens.com/search/results.jsp?Ntt=needoh")
]


def fetch_store(name, url):
    try:
        r = requests.get(url, headers=HEADERS, timeout=12)
        soup = BeautifulSoup(r.text, "html.parser")

        found = []

        # Try to extract product-like entries
        for tag in soup.find_all(["a", "h2", "h3", "span"]):
            text = tag.get_text(" ", strip=True)

            if not text:
                continue

            if "needoh" in text.lower():
                link = tag.get("href")

                if link and link.startswith("/"):
                    if "walmart" in url:
                        base = "https://www.walmart.com"
                    elif "target" in url:
                        base = "https://www.target.com"
                    elif "fivebelow" in url:
                        base = "https://www.fivebelow.com"
                    elif "walgreens" in url:
                        base = "https://www.walgreens.com"
                    else:
                        base = url.split("//")[0] + "//" + url.split("//")[1].split("/")[0]

                    link = base + link

                found.append({
                    "store": name,
                    "title": text,
                    "url": link if link else url
                })

        # remove duplicates
        unique = []
        seen = set()

        for item in found:
            key = item["title"] + item["url"]
            if key not in seen:
                seen.add(key)
                unique.append(item)

        return unique[:3]

    except Exception as e:
        return [{
            "store": name,
            "title": f"Error checking store: {str(e)[:40]}",
            "url": url
        }]


def send_discord(results):
    if not results:
        payload = {
            "content": "🔍 Squishy Check: No results found right now."
        }
        requests.post(WEBHOOK_URL, json=payload)
        return

    embeds = []

    for r in results[:10]:
        embeds.append({
            "title": r["store"],
            "description": r["title"],
            "url": r["url"]
        })

    payload = {
        "content": "🚨 **SQUISHY ALERT (PRODUCTION SCAN)** 🚨",
        "embeds": embeds
    }

    requests.post(WEBHOOK_URL, json=payload)


if __name__ == "__main__":
    all_results = []

    for name, url in SEARCHES:
        results = fetch_store(name, url)
        print(name, results)

        for r in results:
            if "error" not in r["title"].lower():
                all_results.append(r)

    # remove duplicates across stores
    final = []
    seen = set()

    for r in all_results:
        key = r["title"] + r["url"]
        if key not in seen:
            seen.add(key)
            final.append(r)

    print("FINAL:", final)

    send_discord(final)


