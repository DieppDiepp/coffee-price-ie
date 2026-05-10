import argparse
import asyncio
from pathlib import Path
from extractors import (
    Crawl4AIBrowserClient,
    HybridScraper,
    ScraplingHttpClient,
    load_json_file,
    load_source_rules,
    lookup_source_rule,
    process_occurrences,
    resolve_repo_path,
    Occurrence
)
from snowflake_utils import get_snowflake_connection

PROJECT_ROOT = Path(__file__).resolve().parents[2]

def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Hybrid scraper pulling from Snowflake discovery_links.",
    )
    parser.add_argument(
        "--config",
        default="config/scraper.json",
        help="Path to scraper config JSON. Defaults to config/scraper.json.",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help="Only process the first N occurrences.",
    )
    return parser

def fetch_pending_occurrences(conn) -> list[Occurrence]:
    cursor = conn.cursor()
    cursor.execute("SELECT url_hash, url, domain, date_ref FROM discovery_links WHERE scrape_status = 'pending'")
    rows = cursor.fetchall()
    occurrences = []
    for row in rows:
        occurrences.append(Occurrence(
            url_hash=row[0],
            url=row[1],
            domain=row[2],
            date_ref=str(row[3]) if row[3] else ""
        ))
    return occurrences

def get_save_callback(conn):
    def save_callback(record):
        cursor = conn.cursor()
        url_hash = record["url_hash"]
        status = record["status"]
        
        try:
            # If success, insert into scraped_html
            if status == "success" and record.get("raw_html"):
                # We use MERGE or ignore if exists, but assuming it's pending, we just insert.
                cursor.execute("""
                    MERGE INTO scraped_html target
                    USING (SELECT %s AS url_hash, %s AS html_content, %s AS scraped_at) source
                    ON target.url_hash = source.url_hash
                    WHEN MATCHED THEN UPDATE SET html_content = source.html_content, scraped_at = source.scraped_at
                    WHEN NOT MATCHED THEN INSERT (url_hash, html_content, scraped_at) VALUES (source.url_hash, source.html_content, source.scraped_at)
                """, (url_hash, record["raw_html"], record["collected_at"]))
                final_status = 'success'
            else:
                final_status = 'failed'
                
            # Update discovery_links
            cursor.execute(
                "UPDATE discovery_links SET scrape_status = %s WHERE url_hash = %s",
                (final_status, url_hash)
            )
            conn.commit()
        except Exception as e:
            print(f"Error saving record {url_hash} to Snowflake: {e}")
            conn.rollback()

    return save_callback

async def run_async(args: argparse.Namespace) -> int:
    config_path = resolve_repo_path(PROJECT_ROOT, "pipeline/02_scraper/" + args.config)
    if not config_path.exists():
        # Fallback to repo root if not found in 02_scraper/config
        config_path = resolve_repo_path(PROJECT_ROOT, args.config)
        
    config = load_json_file(config_path)

    sources_path = resolve_repo_path(PROJECT_ROOT, "pipeline/02_scraper/" + config["sources_config"])
    if not sources_path.exists():
        sources_path = resolve_repo_path(PROJECT_ROOT, config["sources_config"])
        
    default_rule, source_rules = load_source_rules(sources_path)

    print("Connecting to Snowflake...")
    conn = get_snowflake_connection()
    occurrences = fetch_pending_occurrences(conn)
    
    if args.limit is not None:
        occurrences = occurrences[: args.limit]

    print(f"Found {len(occurrences)} pending links to scrape.")

    http_config = config["http"]
    browser_config = config["browser"]
    timezone = config.get("timezone", "Asia/Ho_Chi_Minh")

    http_client = ScraplingHttpClient(
        timeout_sec=http_config["timeout_sec"],
        retries=http_config["retries"],
        concurrency=http_config["concurrency"],
        delay_between_requests_sec=http_config["delay_between_requests_sec"],
        timezone=timezone,
    )

    browser_client = None
    if browser_config.get("enabled", True):
        browser_client = Crawl4AIBrowserClient(
            timeout_sec=browser_config["timeout_sec"],
            concurrency=browser_config["concurrency"],
            wait_until=browser_config["wait_until"],
            delay_before_return_html_sec=browser_config["delay_before_return_html_sec"],
            wait_for_timeout_ms=browser_config["wait_for_timeout_ms"],
            headless=browser_config.get("headless", True),
            enable_stealth=browser_config.get("enable_stealth", True),
            timezone=timezone,
        )

    scraper = HybridScraper(
        http_client=http_client,
        browser_client=browser_client,
        browser_enabled=browser_config.get("enabled", True),
    )

    save_callback = get_save_callback(conn)

    try:
        stats = await process_occurrences(
            occurrences=occurrences,
            scraper=scraper,
            source_lookup=lambda domain: lookup_source_rule(domain, default_rule, source_rules),
            save_callback=save_callback,
            worker_count=max(http_config["concurrency"], browser_config["concurrency"]),
        )
    finally:
        await scraper.close()
        conn.close()

    print_summary(len(occurrences), stats)
    return 0

def print_summary(
    occurrence_count: int,
    stats: dict[str, int],
) -> None:
    print("Scraper summary")
    print(f"- Total pending links: {occurrence_count}")
    print(f"- Processed: {stats.get('written', 0)}")

    for prefix, label in (
        ("status:", "Status"),
        ("method:", "Method"),
        ("domain:", "Domain"),
    ):
        entries = sorted(
            ((key[len(prefix) :], value) for key, value in stats.items() if key.startswith(prefix)),
            key=lambda item: (-item[1], item[0]),
        )
        if not entries:
            continue
        print(f"- {label}:")
        for name, value in entries[:15]:
            print(f"  - {name}: {value}")

def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    return asyncio.run(run_async(args))

if __name__ == "__main__":
    raise SystemExit(main())
