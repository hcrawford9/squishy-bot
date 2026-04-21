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

        items = []

        for a in soup.select("a"):
            text = a.get_text(strip=True)

            if text and "needoh" in text.lower():
                link = a.get("href")

                if link and link.startswith("/"):
                    link = url.split("/")[0] + "//" + url.split("/")[2] + link

                items.append(f"{name}: {text}\n{link}")

        return items[:2]

    except Exception as e:
        return [f"{name} error"]

def send_to_discord(results):
    message = "🚨 Squishy Check:\n\n" + "\n\n".join(results)
    requests.post(WEBHOOK_URL, json={"content": message[:2000]})


if __name__ == "__main__":
    all_results = []

    for name, url in SEARCHES:
        results = scrape_store(name, url)
        all_results.extend(results)

    send_to_discord(all_results)
