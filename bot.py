import requests
import os
from bs4 import BeautifulSoup

WEBHOOK_URL = os.environ.get("DISCORD_WEBHOOK")

HEADERS = {
    "User-Agent": "Mozilla/5.0"
}

SEARCHES = [
    ("Needoh Tracker", "https://www.needohtracker.com/search"),
    ("Walmart", "https://www.walmart.com/search?q=needoh"),
    ("Target", "https://www.target.com/s?searchTerm=needoh"),
    ("Five Below", "https://www.fivebelow.com/search?q=needoh"),
    ("Walgreens", "https://www.walgreens.com/search/results.jsp?Ntt=needoh")
]

KEYWORDS = [
    "needoh",
    "nee doh",
    "squishy"
]


def matches_keywords(text):
    text = text.lower()
    return any(k in text for k in KEYWORDS)


def make_absolute(base_url, href):
    if not href:
        return base_url

    if href.startswith("http"):
        return href

    if href.startswith("/"):
        domain = base_url.split("//")[0] + "//" + base_url.split("//")[1].split("/")[0]
        return domain + href

    return base_url


def fetch_store(name, url):
    try:
        r = requests.get(url, headers=HEADERS, timeout=15)

        print(f"{name} status:", r.status_code)

        soup = BeautifulSoup(r.text, "html.parser")

        found = []

        # Only inspect links (product pages are usually links)
        for a in soup.find_all("a", href=True):
            text = a.get_text(" ", strip=True)

            if not text:
                continue

            if matches_keywords(text):
                href = make_absolute(url, a["href"])

                found.append({
                    "store": name,
                    "title": text,
                    "url": href
                })

        # Remove duplicates
        unique = []
        seen = set()

        for item in found:
            key = item["title"] + item["url"]

            if key not in seen:
                seen.add(key)
                unique.append(item)

        return unique[:5]

    except Exception as e:
        print(f"{name} error:", e)
        return []


def send_discord(results):
    if not results:
        message = "🔍 Squishy Check: No new results found."
    else:
        message = "🚨 **SQUISHY ALERTS FOUND** 🚨\n\n"

        for r in results:
            message += (
                f"🏪 {r['store']}\n"
                f"🧸 {r['title']}\n"
                f"🔗 {r['url']}\n\n"
            )

    requests.post(
        WEBHOOK_URL,
        json={"content": message[:2000]}
    )


if __name__ == "__main__":
    all_results = []

    for name, url in SEARCHES:
        results = fetch_store(name, url)

        print(name, "found:", len(results))

        all_results.extend(results)

    print("TOTAL RESULTS:", len(all_results))

    send_discord(all_results)