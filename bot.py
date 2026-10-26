
import json
import os
import re
import subprocess
from pathlib import Path
from urllib.parse import quote_plus, urljoin, urlparse, parse_qs, urlencode, urlunparse

import requests
from bs4 import BeautifulSoup

WEBHOOK_URL = os.environ.get("DISCORD_WEBHOOK", "")
ZIP_CODE = "23320"
SEEN_FILE = Path("seen_products.json")

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/131.0.0.0 Safari/537.36"
    )
}

KEYWORDS = [
    "needoh",
    "nee doh",
    "squishy",
    "slow rise",
    "sugar squish",
]

# Search each retailer using each keyword.
STORES = {
    "Walmart": "https://www.walmart.com/search?q={query}&zip=" + ZIP_CODE,
    "Target": "https://www.target.com/s?searchTerm={query}",
    "Five Below": "https://www.fivebelow.com/search?q={query}",
    "Walgreens": "https://www.walgreens.com/search/results.jsp?Ntt={query}",
    "Kohl's": "https://www.kohls.com/search.jsp?search={query}",
    "American Eagle": "https://www.ae.com/us/en/search?q={query}",
}

# Avoid links that are clearly not individual product pages.
SKIP_PATH_PARTS = (
    "/search", "/account", "/login", "/cart", "/help",
    "/stores", "/store-locator", "/wishlist", "/checkout",
)

session = requests.Session()
session.headers.update(HEADERS)


def matches_keywords(text):
    text = re.sub(r"[-_]+", " ", text.lower())
    return any(keyword in text for keyword in KEYWORDS)


def load_seen():
    try:
        return set(json.loads(SEEN_FILE.read_text(encoding="utf-8")))
    except (OSError, json.JSONDecodeError, TypeError):
        return set()


def save_seen(seen):
    SEEN_FILE.write_text(
        json.dumps(sorted(seen), indent=2),
        encoding="utf-8",
    )


def clean_url(url):
    """Remove tracking parameters so the same product is not repeated."""
    parsed = urlparse(url)
    query = parse_qs(parsed.query, keep_blank_values=True)
    query = {
        key: value for key, value in query.items()
        if not key.lower().startswith(("utm_", "fbclid", "gclid"))
    }
    return urlunparse((
        parsed.scheme,
        parsed.netloc.lower(),
        parsed.path.rstrip("/") or "/",
        parsed.params,
        urlencode(query, doseq=True),
        "",
    ))


def fetch_store(store_name, template, keyword):
    url = template.format(query=quote_plus(keyword))

    try:
        response = session.get(url, timeout=20)
        print(f"{store_name} / {keyword}: HTTP {response.status_code}")

        if response.status_code != 200:
            return []

        soup = BeautifulSoup(response.text, "html.parser")
        found = {}

        for anchor in soup.find_all("a", href=True):
            title = anchor.get_text(" ", strip=True)
            if not title or not matches_keywords(title):
                continue

            full_url = urljoin(url, anchor["href"])
            parsed = urlparse(full_url)

            if parsed.scheme not in ("http", "https"):
                continue

            if any(part in parsed.path.lower() for part in SKIP_PATH_PARTS):
                continue

            # Don't alert on links that point outside the retailer's site.
            base_host = urlparse(template.split("{query}")[0]).netloc.lower()
            if base_host and not (
                parsed.netloc.lower() == base_host
                or parsed.netloc.lower().endswith("." + base_host)
            ):
                continue

            full_url = clean_url(full_url)
            key = f"{store_name}|{full_url}"

            # Keep the longer, more informative matching title.
            if key not in found or len(title) > len(found[key]["title"]):
                found[key] = {
                    "key": key,
                    "store": store_name,
                    "title": title[:180],
                    "url": full_url,
                }

        return list(found.values())

    except requests.RequestException as error:
        print(f"{store_name} / {keyword} error: {error}")
        return []


def send_discord(items):
    if not WEBHOOK_URL:
        print("ERROR: DISCORD_WEBHOOK secret is missing.")
        return

    # Discord has a 2,000-character message limit.
    chunks = []
    current = "🧸 **NEW SQUISHY LISTINGS FOUND**\n\n"

    for item in items:
        block = (
            f"🏪 **{item['store']}**\n"
            f"🧸 {item['title']}\n"
            f"🔗 {item['url']}\n\n"
        )

        if len(current) + len(block) > 1850:
            chunks.append(current)
            current = "🧸 **More new listings**\n\n"

        current += block

    if current.strip():
        chunks.append(current)

    for message in chunks:
        try:
            response = session.post(
                WEBHOOK_URL,
                json={"content": message},
                timeout=20,
            )
            response.raise_for_status()
        except requests.RequestException as error:
            print(f"Discord alert failed: {error}")


def main():
    if not WEBHOOK_URL:
        raise SystemExit(
            "Missing DISCORD_WEBHOOK secret. Add it in repository Actions secrets."
        )

    seen = load_seen()
    all_items = {}

    for store_name, template in STORES.items():
        for keyword in KEYWORDS:
            results = fetch_store(store_name, template, keyword)
            for item in results:
                all_items[item["key"]] = item

    new_items = [
        item for key, item in all_items.items()
        if key not in seen
    ]

    print(f"Matching listings found: {len(all_items)}")
    print(f"New listings to alert: {len(new_items)}")

    # Remember matching listings even when no new alert is needed.
    updated_seen = seen | set(all_items.keys())
    save_seen(updated_seen)

    if new_items:
        send_discord(new_items)
    else:
        print("No new matching listings. No Discord message sent.")

    # Persist the deduplication list for the next scheduled run.
    subprocess.run(
        ["git", "config", "user.name", "github-actions[bot]"],
        check=True,
    )
    subprocess.run(
        ["git", "config", "user.email",
         "41898282+github-actions[bot]@users.noreply.github.com"],
        check=True,
    )
    subprocess.run(["git", "add", "seen_products.json"], check=True)

    changed = subprocess.run(
        ["git", "diff", "--cached", "--quiet"]
    ).returncode != 0

    if changed:
        subprocess.run(
            ["git", "commit", "-m", "Update seen squishy listings"],
            check=True,
        )
        subprocess.run(["git", "push"], check=True)


if __name__ == "__main__":
    main()
