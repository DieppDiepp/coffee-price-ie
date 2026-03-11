from __future__ import annotations

import argparse
import asyncio
from pathlib import Path

from extractors import (
    Crawl4AIBrowserClient,
    HybridScraper,
    ScraplingHttpClient,
    flatten_discovered_inputs,
    load_json_file,
    load_resume_index,
    load_source_rules,
    lookup_source_rule,
    process_occurrences,
    resolve_input_paths,
    resolve_repo_path,
)


PROJECT_ROOT = Path(__file__).resolve().parents[2]


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Hybrid scraper for discovered article URLs.",
    )
    parser.add_argument(
        "--input",
        nargs="+",
        help="One or more JSONL files or glob patterns. Defaults to config input_glob.",
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
        help="Only process the first N occurrences after flattening and resume filtering.",
    )
    parser.add_argument(
        "--resume",
        dest="resume",
        action="store_true",
        help="Skip existing (url, date_ref) records already present in output.",
    )
    parser.add_argument(
        "--no-resume",
        dest="resume",
        action="store_false",
        help="Ignore existing output and process everything again.",
    )
    parser.set_defaults(resume=None)
    return parser


async def run_async(args: argparse.Namespace) -> int:
    config_path = resolve_repo_path(PROJECT_ROOT, args.config)
    config = load_json_file(config_path)

    input_patterns = args.input or [config["input_glob"]]
    input_paths = resolve_input_paths(PROJECT_ROOT, input_patterns)
    if not input_paths:
        raise FileNotFoundError(f"No input files matched: {input_patterns}")

    output_dir = resolve_repo_path(PROJECT_ROOT, config["output_dir"])
    sources_path = resolve_repo_path(PROJECT_ROOT, config["sources_config"])
    default_rule, source_rules = load_source_rules(sources_path)

    occurrences = flatten_discovered_inputs(input_paths)
    if args.limit is not None:
        occurrences = occurrences[: args.limit]

    resume_enabled = config.get("resume", True) if args.resume is None else args.resume
    resume_index = load_resume_index(output_dir) if resume_enabled else set()

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

    try:
        stats = await process_occurrences(
            occurrences=occurrences,
            output_dir=output_dir,
            scraper=scraper,
            source_lookup=lambda domain: lookup_source_rule(domain, default_rule, source_rules),
            resume_index=resume_index,
            worker_count=max(http_config["concurrency"], browser_config["concurrency"]),
        )
    finally:
        await scraper.close()

    print_summary(input_paths, output_dir, len(occurrences), resume_enabled, stats)
    return 0


def print_summary(
    input_paths: list[Path],
    output_dir: Path,
    occurrence_count: int,
    resume_enabled: bool,
    stats: dict[str, int],
) -> None:
    print("Scraper summary")
    print(f"- Inputs: {', '.join(str(path) for path in input_paths)}")
    print(f"- Output dir: {output_dir}")
    print(f"- Flattened occurrences: {occurrence_count}")
    print(f"- Resume enabled: {resume_enabled}")
    print(f"- Skipped via resume: {stats.get('skipped_resume', 0)}")
    print(f"- Written: {stats.get('written', 0)}")

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
