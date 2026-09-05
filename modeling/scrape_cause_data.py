"""
Better scraper for cause detection dataset.
Uses more specific queries for each category.
"""
import os
import re
import time
import requests
from pathlib import Path
from urllib.parse import quote_plus

DATA_DIR = Path(__file__).parent / "data" / "training"
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
}

SEARCH_QUERIES = {
    "flood_river": [
        "air sungai meluap banjir",
        "sungai penuh air banjir kota",
        "river flooding brown water streets",
        "banjir kiriman sungai deras",
        "sungai meluap terendam jalan",
        "river overflow residential area",
        "air bah sungai rumah terendam",
        "flash flood river Indonesia",
        "banjir bandang sungai kota",
        "river water level high flood",
        "sungai naik banjir perkotaan",
        "flooding from river overflow",
    ],
    "flood_trash": [
        "sampah menumpuk di sungai",
        "sampah plastik menyumbat saluran air",
        "garbage blocking drain flood",
        "trash clogged canal water",
        "sampah di saluran pembuangan banjir",
        "plastic waste river pollution flood",
        "tumpukan sampah sungai kotor",
        "debris blocking waterway flood",
        "sampah mengotori sungai banjir",
        "waste accumulation drain clog",
        "trash filled river flood",
        "garbage pile water blockage",
    ],
    "flood_rain": [
        "genangan air hujan di jalan raya",
        "banjir genangan air hujan jalanan",
        "street flooding after heavy rain",
        "jalan raya terendam air hujan",
        "water pooling on road rain",
        "genangan air di perkotaan hujan",
        "road submerged rain water",
        "urban street waterlogging rain",
        "jalan banjir genangan air",
        "rain accumulation on street flood",
        "waterlogged road after rainfall",
        "genangan air hujan kota banjir",
    ],
}


def get_bing_image_urls(query, count=20):
    """Get image URLs from Bing Image Search."""
    urls = []
    search_url = f"https://www.bing.com/images/search?q={quote_plus(query)}&first=1&count={count}"

    try:
        resp = requests.get(search_url, headers=HEADERS, timeout=15)
        resp.raise_for_status()
        html = resp.text

        m = re.findall(r'murl&quot;:&quot;(https?://[^&]+?)&quot;', html)
        urls.extend(m)

    except Exception as e:
        print(f"  Search failed: {e}")

    seen = set()
    unique = []
    for u in urls:
        u = u.replace("&amp;", "&")
        if u not in seen and not u.endswith(".svg") and "bing.com" not in u:
            seen.add(u)
            unique.append(u)

    return unique[:count]


def download_image(url, filepath, timeout=10):
    """Download a single image."""
    try:
        resp = requests.get(url, headers=HEADERS, timeout=timeout, stream=True)
        resp.raise_for_status()

        content_type = resp.headers.get("Content-Type", "")
        if "image" not in content_type and not url.endswith((".jpg", ".jpeg", ".png", ".webp")):
            return False

        with open(filepath, "wb") as f:
            for chunk in resp.iter_content(8192):
                f.write(chunk)

        size = os.path.getsize(filepath)
        if size < 5000:
            os.remove(filepath)
            return False

        return True
    except Exception:
        return False


def scrape_category(category, queries, target_count=100):
    """Scrape images for a category."""
    out_dir = DATA_DIR / category
    out_dir.mkdir(parents=True, exist_ok=True)

    existing = len(list(out_dir.glob("*.*")))
    print(f"\n{'='*50}")
    print(f"Category: {category} (existing: {existing})")
    print(f"Target: {target_count} images")

    downloaded = existing
    all_urls = []

    for query in queries:
        print(f"  Searching: {query}")
        urls = get_bing_image_urls(query, count=20)
        all_urls.extend(urls)
        print(f"    Found {len(urls)} URLs")
        time.sleep(1)

    print(f"  Total unique URLs: {len(all_urls)}")

    for i, url in enumerate(all_urls):
        if downloaded >= target_count:
            break

        ext = ".jpg"
        if ".png" in url.lower():
            ext = ".png"
        elif ".webp" in url.lower():
            ext = ".jpg"

        filepath = out_dir / f"{category}_{downloaded:04d}{ext}"

        if download_image(url, filepath):
            downloaded += 1
            if downloaded % 10 == 0:
                print(f"  Progress: {downloaded}/{target_count}")

        time.sleep(0.3)

    print(f"  Final count: {downloaded} images")
    return downloaded


def main():
    total = 0
    for category, queries in SEARCH_QUERIES.items():
        count = scrape_category(category, queries, target_count=100)
        total += count

    print(f"\n{'='*50}")
    print(f"TOTAL: {total} images scraped")

    for cat in SEARCH_QUERIES:
        d = DATA_DIR / cat
        n = len(list(d.glob("*.*")))
        print(f"  {cat}: {n} images")


if __name__ == "__main__":
    main()
