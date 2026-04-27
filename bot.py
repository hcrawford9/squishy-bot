import requests
import os
from bs4 import BeautifulSoup

WEBHOOK_URL = os.environ.get("DISCORD_WEBHOOK")

HEADERS = {
    "User-Agent": "Mozilla/5.0"
}

ZIP_CODE = "23320"

SEARCHES = [
    ("Needoh Tracker", f"https://www.needohtracker.com/search?zip={ZIP_CODE}"),
    ("Walmart", f"https://www.walmart.com/search?q=needoh&zip={ZIP_CODE}"),
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
    return any(keyword in text for keyword in KEYWORDS)


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

        print(f"{name} status: {r.status_code}")

        if r.status_code != 200:
            return []

        soup = BeautifulSoup(r.text, "html.parser")

        found = []

        # Product pages are usually links
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
        print(f"{name} error: {e}")
        return []


def send_discord(results):
    if not results:
        message = "🔍 Squishy Check: No NeeDoh results found right now."
    else:
        message = "🚨 **NEEDOH ALERTS FOUND** 🚨\n\n"

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

        print(f"{name} found: {len(results)}")

        all_results.extend(results)

    print("TOTAL RESULTS:", len(all_results))

    send_discord(all_results)