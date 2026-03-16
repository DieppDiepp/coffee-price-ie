import json
import hashlib
from pathlib import Path
from datetime import datetime
from time import sleep
from urllib.parse import urlparse

from extractors import fetch_requests, fetch_browser, is_html_empty

INPUT_FILE = "data/01_discovered/2026-03.jsonl"
OUTPUT_ROOT = "data/02_rawhtml"

BAD_DOMAINS = [
    "instagram.com",
    "facebook.com",
    "youtube.com"
]


def save_metadata(filepath, metadata):
    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(metadata, f, ensure_ascii=False, indent=2)


def main():

    seen_urls = {}

    with open(INPUT_FILE, "r", encoding="utf-8") as f:

        for line in f:

            record = json.loads(line)

            date = record["date"]
            query_id = record["query_id"]
            results = record["results"]

            day_dir = Path(OUTPUT_ROOT) / date
            day_dir.mkdir(parents=True, exist_ok=True)

            for r in results:

                url = r["url"]
                rank = r["rank"]

                # check duplicate
                if url in seen_urls:
                    print("duplicate link:", url)
                    continue

                seen_urls[url] = True

                domain = urlparse(url).netloc

                if any(d in domain for d in BAD_DOMAINS):
                    print("skip social:", url)
                    continue

                # hash filename để tránh trùng
                url_hash = hashlib.md5(url.encode()).hexdigest()

                html_path = day_dir / f"{url_hash}.html"
                meta_path = day_dir / f"{url_hash}.json"

                if html_path.exists():
                    print("skip existing:", html_path)
                    continue

                print("crawl:", url)

                crawl_method = "requests"
                html, status = fetch_requests(url)

                if is_html_empty(html):
                    print("retry with browser...")
                    html = fetch_browser(url)
                    crawl_method = "browser"

                if html:

                    with open(html_path, "w", encoding="utf-8") as f:
                        f.write(html)

                    metadata = {
                        "url": url,
                        "domain": domain,
                        "date": date,
                        "query_id": query_id,
                        "rank": rank,
                        "url_hash": url_hash,
                        "crawl_time": datetime.utcnow().isoformat(),
                        "crawl_method": crawl_method,
                        "status_code": status,
                        "html_size": len(html)
                    }

                    save_metadata(meta_path, metadata)

                sleep(1)


if __name__ == "__main__":
    main()