from __future__ import annotations

import asyncio
import copy
import json
import re
import time
from collections import Counter
from dataclasses import dataclass, field
from datetime import date, datetime
from pathlib import Path
from typing import Any, Callable, Iterable, Sequence
from urllib.parse import urlparse
from zoneinfo import ZoneInfo

from bs4 import BeautifulSoup
from dateutil import parser as date_parser


DEFAULT_TIMEZONE = "Asia/Ho_Chi_Minh"
DEFAULT_PUBLISHED_AT_PRIORITY = ["jsonld", "time_tag", "meta", "text"]
JSONLD_DATE_KEYS = {"datePublished", "dateCreated", "dateModified", "uploadDate"}
JSONLD_DATE_PRIORITY = ["datepublished", "datecreated", "uploaddate", "datemodified"]
TIME_TAG_ATTR_PRIORITY = ["datetime", "content", "data-time", "dateTime"]
COMMON_PUBLISHED_AT_HINTS = [
    "article:published_time",
    "og:published_time",
    "publishdate",
    "pubdate",
    "date",
    "datepublished",
    "datecreated",
    "dc.date.issued",
    "parsely-pub-date",
]
TITLE_META_KEYS = ["og:title", "twitter:title"]
AMBIGUOUS_DATE_RE = re.compile(r"(?<!\d)(\d{1,2})([/-])(\d{1,2})\2(\d{2,4})(?!\d)")
YEAR_FIRST_DATE_RE = re.compile(r"(?<!\d)\d{4}[/-]\d{1,2}[/-]\d{1,2}")
ISO_DATE_RE = re.compile(r"(?<!\d)\d{4}-\d{2}-\d{2}(?:[T\s]\d{2}:\d{2}(?::\d{2})?)?")
YEAR_TOKEN_RE = re.compile(r"(?<!\d)(?:19|20)\d{2}(?!\d)")
TEXT_FALLBACK_TOKENS = ("date", "time", "publish", "posted", "created", "updated", "ngay", "gio")
BLOCKED_MARKERS = [
    "access denied",
    "attention required! | cloudflare",
    "checking your browser before accessing",
    "please enable javascript and cookies to continue",
    "cf-browser-verification",
    "temporarily unavailable",
]
HTML_CONTENT_TYPES = ("text/html", "application/xhtml+xml")
FALLBACK_STATUS_CODES = {403, 429, 503}


@dataclass(slots=True)
class SourceRule:
    source_id: str
    prefer_browser: bool = False
    wait_for: str | None = None
    published_at_hints: list[str] = field(default_factory=list)
    published_at_priority: list[str] = field(default_factory=list)
    skip_published_at_meta_keys: list[str] = field(default_factory=list)
    prefer_dayfirst: bool = True


@dataclass(slots=True)
class Occurrence:
    url_hash: str
    url: str
    domain: str
    date_ref: str
    discovery_rank: int | None = None
    discovered_title: str | None = None


@dataclass(slots=True)
class FetchPayload:
    input_url: str
    final_url: str | None
    raw_html: str | None
    http_status: int | None
    headers: dict[str, str]
    fetch_method: str
    collected_at: str
    content_type: str | None
    status: str
    error: str | None = None


@dataclass(slots=True)
class ParsedDateTime:
    normalized: str
    confidence: str
    alignment_days: int | None = None


@dataclass(slots=True)
class PublishedAtCandidate:
    normalized: str
    raw_value: str
    source: str
    source_key: str | None
    confidence: str
    alignment_days: int | None


@dataclass(slots=True)
class PublishedAtResult:
    value: str | None
    raw_value: str | None
    source: str = "none"
    confidence: str = "none"
    alignment: str = "unknown"
    alignment_days: int | None = None


class ScraplingHttpClient:
    def __init__(
        self,
        timeout_sec: float,
        retries: int,
        concurrency: int,
        delay_between_requests_sec: float,
        timezone: str = DEFAULT_TIMEZONE,
    ) -> None:
        self.timeout_sec = timeout_sec
        self.retries = retries
        self.semaphore = asyncio.Semaphore(concurrency)
        self.delay_between_requests_sec = delay_between_requests_sec
        self.timezone = timezone
        self._throttle_lock = asyncio.Lock()
        self._last_request_at = 0.0

    async def fetch(self, url: str, _: SourceRule) -> FetchPayload:
        try:
            from scrapling.fetchers import AsyncFetcher
        except Exception as exc:  # pragma: no cover - import failure is environment specific
            return make_error_payload(
                url,
                fetch_method="http",
                status="failed_other",
                error=f"scrapling import failed: {exc}",
                timezone=self.timezone,
            )

        async with self.semaphore:
            await self._throttle()
            try:
                response = await AsyncFetcher.get(
                    url,
                    timeout=self.timeout_sec,
                    retries=self.retries,
                    follow_redirects=True,
                    stealthy_headers=True,
                )
                headers = normalize_headers(getattr(response, "headers", {}) or {})
                raw_html = stringify_html(
                    getattr(response, "html_content", None) or getattr(response, "body", None)
                )
                payload = FetchPayload(
                    input_url=url,
                    final_url=stringify_optional(getattr(response, "url", None)),
                    raw_html=raw_html,
                    http_status=coerce_int(getattr(response, "status", None)),
                    headers=headers,
                    fetch_method="http",
                    collected_at=current_timestamp(self.timezone),
                    content_type=header_value(headers, "content-type"),
                    status="failed_other",
                )
                payload.status = classify_payload(payload)
                return payload
            except asyncio.TimeoutError as exc:
                return make_error_payload(
                    url,
                    fetch_method="http",
                    status="failed_timeout",
                    error=str(exc) or "HTTP fetch timed out",
                    timezone=self.timezone,
                )
            except Exception as exc:  # pragma: no cover - depends on remote/network
                return make_error_payload(
                    url,
                    fetch_method="http",
                    status="failed_other",
                    error=str(exc),
                    timezone=self.timezone,
                )

    async def _throttle(self) -> None:
        if self.delay_between_requests_sec <= 0:
            return
        async with self._throttle_lock:
            now = time.monotonic()
            wait_time = self.delay_between_requests_sec - (now - self._last_request_at)
            if wait_time > 0:
                await asyncio.sleep(wait_time)
            self._last_request_at = time.monotonic()


class Crawl4AIBrowserClient:
    def __init__(
        self,
        timeout_sec: float,
        concurrency: int,
        wait_until: str,
        delay_before_return_html_sec: float,
        wait_for_timeout_ms: int,
        headless: bool = True,
        enable_stealth: bool = True,
        timezone: str = DEFAULT_TIMEZONE,
    ) -> None:
        self.timeout_sec = timeout_sec
        self.semaphore = asyncio.Semaphore(concurrency)
        self.wait_until = wait_until
        self.delay_before_return_html_sec = delay_before_return_html_sec
        self.wait_for_timeout_ms = wait_for_timeout_ms
        self.headless = headless
        self.enable_stealth = enable_stealth
        self.timezone = timezone
        self._crawler = None
        self._start_lock = asyncio.Lock()

    async def fetch(self, url: str, source_rule: SourceRule) -> FetchPayload:
        try:
            from crawl4ai import AsyncWebCrawler, BrowserConfig, CacheMode, CrawlerRunConfig
        except Exception as exc:  # pragma: no cover - import failure is environment specific
            return make_error_payload(
                url,
                fetch_method="browser",
                status="failed_other",
                error=f"crawl4ai import failed: {exc}",
                timezone=self.timezone,
            )

        async with self.semaphore:
            crawler = await self._ensure_started(AsyncWebCrawler, BrowserConfig)
            try:
                run_config = CrawlerRunConfig(
                    cache_mode=CacheMode.BYPASS,
                    verbose=False,
                    wait_until=self.wait_until,
                    page_timeout=int(self.timeout_sec * 1000),
                    wait_for=source_rule.wait_for,
                    wait_for_timeout=self.wait_for_timeout_ms,
                    delay_before_return_html=self.delay_before_return_html_sec,
                    process_iframes=False,
                    user_agent=None,
                )
                result = await crawler.arun(url, config=run_config)
                headers = normalize_headers(getattr(result, "response_headers", {}) or {})
                payload = FetchPayload(
                    input_url=url,
                    final_url=stringify_optional(
                        getattr(result, "redirected_url", None) or getattr(result, "url", None)
                    ),
                    raw_html=stringify_html(getattr(result, "html", None)),
                    http_status=coerce_int(getattr(result, "status_code", None)),
                    headers=headers,
                    fetch_method="browser",
                    collected_at=current_timestamp(self.timezone),
                    content_type=header_value(headers, "content-type"),
                    status="failed_other",
                    error=empty_to_none(getattr(result, "error_message", None)),
                )
                payload.status = classify_payload(payload)
                return payload
            except asyncio.TimeoutError as exc:
                return make_error_payload(
                    url,
                    fetch_method="browser",
                    status="failed_timeout",
                    error=str(exc) or "Browser fetch timed out",
                    timezone=self.timezone,
                )
            except Exception as exc:  # pragma: no cover - depends on browser runtime
                return make_error_payload(
                    url,
                    fetch_method="browser",
                    status="failed_other",
                    error=str(exc),
                    timezone=self.timezone,
                )

    async def close(self) -> None:
        if self._crawler is not None:
            await self._crawler.close()
            self._crawler = None

    async def _ensure_started(self, crawler_cls: Any, browser_config_cls: Any) -> Any:
        async with self._start_lock:
            if self._crawler is None:
                config = browser_config_cls(
                    headless=self.headless,
                    enable_stealth=self.enable_stealth,
                    verbose=False,
                    ignore_https_errors=True,
                )
                self._crawler = crawler_cls(config=config)
                await self._crawler.start()
        return self._crawler


class HybridScraper:
    def __init__(
        self,
        http_client: Any,
        browser_client: Any | None,
        browser_enabled: bool = True,
    ) -> None:
        self.http_client = http_client
        self.browser_client = browser_client
        self.browser_enabled = browser_enabled and browser_client is not None
        self._cache: dict[str, FetchPayload] = {}
        self._inflight: dict[str, asyncio.Task[FetchPayload]] = {}
        self._lock = asyncio.Lock()

    async def fetch_occurrence(self, occurrence: Occurrence, source_rule: SourceRule) -> FetchPayload:
        return await self._fetch_cached(occurrence.url, source_rule)

    async def close(self) -> None:
        if self.browser_client is not None:
            close = getattr(self.browser_client, "close", None)
            if close is not None:
                result = close()
                if asyncio.iscoroutine(result):
                    await result

    async def _fetch_cached(self, url: str, source_rule: SourceRule) -> FetchPayload:
        async with self._lock:
            cached = self._cache.get(url)
            if cached is not None:
                return copy.deepcopy(cached)

            inflight = self._inflight.get(url)
            if inflight is None:
                inflight = asyncio.create_task(self._fetch_url(url, source_rule))
                self._inflight[url] = inflight

        payload = await inflight

        async with self._lock:
            self._cache.setdefault(url, payload)
            if payload.final_url:
                self._cache.setdefault(payload.final_url, payload)
            self._inflight.pop(url, None)

        return copy.deepcopy(payload)

    async def _fetch_url(self, url: str, source_rule: SourceRule) -> FetchPayload:
        if source_rule.prefer_browser and self.browser_enabled:
            payload = await self.browser_client.fetch(url, source_rule)
            return payload

        payload = await self.http_client.fetch(url, source_rule)
        if self.browser_enabled and should_browser_fallback(payload):
            fallback = await self.browser_client.fetch(url, source_rule)
            if fallback.status == "success":
                return fallback

            if payload.status == "success":
                payload.status = "failed_other"
                payload.error = combine_errors(payload.error, fallback.error, "browser fallback failed")
                return payload

            payload.error = combine_errors(payload.error, fallback.error, "browser fallback failed")
        return payload


def load_json_file(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def resolve_repo_path(project_root: Path, candidate: str | Path) -> Path:
    path = Path(candidate)
    if path.is_absolute():
        return path
    return (project_root / path).resolve()


def resolve_input_paths(project_root: Path, patterns: Sequence[str]) -> list[Path]:
    resolved: list[Path] = []
    seen: set[Path] = set()
    for pattern in patterns:
        candidate = Path(pattern)
        if candidate.is_absolute():
            matches = [candidate] if candidate.exists() else list(candidate.parent.glob(candidate.name))
        else:
            matches = list(project_root.glob(pattern))
            if not matches:
                direct = (project_root / candidate).resolve()
                if direct.exists():
                    matches = [direct]
        for match in matches:
            if match.is_file():
                normalized = match.resolve()
                if normalized not in seen:
                    seen.add(normalized)
                    resolved.append(normalized)
    return sorted(resolved)


def load_source_rules(config_path: Path) -> tuple[SourceRule, dict[str, SourceRule]]:
    config = load_json_file(config_path)
    default = config.get("default", {})
    default_rule = make_source_rule(default, source_id=default.get("source_id", "generic"))
    sources: dict[str, SourceRule] = {}
    for domain, source_config in config.get("sources", {}).items():
        sources[domain.lower()] = make_source_rule(source_config, source_id=source_config.get("source_id", domain))
    return default_rule, sources


def make_source_rule(data: dict[str, Any], source_id: str) -> SourceRule:
    hints = [hint for hint in data.get("published_at_hints", []) if hint]
    priority = [p for p in data.get("published_at_priority", []) if p]
    return SourceRule(
        source_id=source_id,
        prefer_browser=bool(data.get("prefer_browser", False)),
        wait_for=data.get("wait_for"),
        published_at_hints=hints,
        published_at_priority=priority,
    )

def lookup_source_rule(domain: str, default_rule: SourceRule, rules: dict[str, SourceRule]) -> SourceRule:
    normalized = domain.lower()
    stripped = normalized[4:] if normalized.startswith("www.") else normalized
    candidates = [normalized, stripped]
    for candidate in candidates:
        if candidate in rules:
            return merge_source_rules(default_rule, rules[candidate])

    for candidate in sorted(rules, key=len, reverse=True):
        if stripped.endswith(candidate):
            return merge_source_rules(default_rule, rules[candidate])

    return merge_source_rules(default_rule, None)

def merge_source_rules(default_rule: SourceRule, override: SourceRule | None) -> SourceRule:
    if override is None:
        return copy.deepcopy(default_rule)

    hints = list(default_rule.published_at_hints)
    for hint in override.published_at_hints:
        if hint not in hints:
            hints.append(hint)

    priority = override.published_at_priority or default_rule.published_at_priority

    return SourceRule(
        source_id=override.source_id or default_rule.source_id,
        prefer_browser=override.prefer_browser,
        wait_for=override.wait_for if override.wait_for is not None else default_rule.wait_for,
        published_at_hints=hints,
        published_at_priority=priority,
    )

def flatten_discovered_inputs(paths: Sequence[Path]) -> list[Occurrence]:
    occurrences: list[Occurrence] = []
    for path in paths:
        with path.open("r", encoding="utf-8") as handle:
            for line in handle:
                line = line.strip()
                if not line or line.startswith("//"):
                    continue
                record = json.loads(line)
                date_ref = record["date"]
                for result in record.get("results", []):
                    url = result.get("url")
                    if not url:
                        continue
                    domain = result.get("domain") or extract_domain(url)
                    occurrences.append(
                        Occurrence(
                            url=url,
                            domain=domain,
                            date_ref=date_ref,
                            discovery_rank=coerce_int(result.get("rank")),
                            discovered_title=result.get("title"),
                        )
                    )
    return occurrences


def load_resume_index(output_dir: Path) -> set[tuple[str, str]]:
    index: set[tuple[str, str]] = set()
    if not output_dir.exists():
        return index

    for path in sorted(output_dir.glob("*.jsonl")):
        with path.open("r", encoding="utf-8") as handle:
            for line in handle:
                line = line.strip()
                if not line:
                    continue
                try:
                    record = json.loads(line)
                except json.JSONDecodeError:
                    continue
                url = record.get("url")
                date_ref = record.get("date_ref")
                if url and date_ref:
                    index.add((url, date_ref))
    return index


def build_record(occurrence: Occurrence, payload: FetchPayload, source_rule: SourceRule) -> dict[str, Any]:
    title = extract_title(payload.raw_html)
    pub_result = extract_published_at(payload.raw_html, occurrence.date_ref, source_rule)
    return {
        "url_hash": occurrence.url_hash,
        "url": occurrence.url,
        "domain": occurrence.domain,
        "date_ref": occurrence.date_ref,
        "collected_at": payload.collected_at,
        "title": title,
        "raw_html": payload.raw_html,
        "status": payload.status,
        "error": payload.error,
        "final_url": payload.final_url,
        "source_id": source_rule.source_id,
        "published_at": pub_result.value,
        "published_at_raw": pub_result.raw_value,
        "published_at_source": pub_result.source,
        "published_at_confidence": pub_result.confidence,
        "published_at_alignment": pub_result.alignment,
        "published_at_alignment_days": pub_result.alignment_days,
        "http_status": payload.http_status,
        "content_type": payload.content_type,
        "fetch_method": payload.fetch_method,
        "discovery_rank": occurrence.discovery_rank,
    }


async def process_occurrences(
    occurrences: Sequence[Occurrence],
    scraper: HybridScraper,
    source_lookup: Callable[[str], SourceRule],
    save_callback: Callable[[dict[str, Any]], None],
    worker_count: int = 5,
) -> Counter[str]:
    stats: Counter[str] = Counter()
    queue: asyncio.Queue[Occurrence | None] = asyncio.Queue()
    result_queue: asyncio.Queue[dict[str, Any] | None] = asyncio.Queue()

    scheduled = 0
    for occurrence in occurrences:
        queue.put_nowait(occurrence)
        scheduled += 1

    if scheduled == 0:
        return stats

    async def worker() -> None:
        while True:
            occurrence = await queue.get()
            if occurrence is None:
                queue.task_done()
                break
            try:
                source_rule = source_lookup(occurrence.domain)
                payload = await scraper.fetch_occurrence(occurrence, source_rule)
                await result_queue.put(build_record(occurrence, payload, source_rule))
            finally:
                queue.task_done()

    workers = [asyncio.create_task(worker()) for _ in range(max(1, worker_count))]

    for _ in workers:
        queue.put_nowait(None)

    written = 0
    while written < scheduled:
        record = await result_queue.get()
        if record is None:
            continue
        save_callback(record)
        stats["written"] += 1
        stats[f"status:{record['status']}"] += 1
        stats[f"method:{record['fetch_method']}"] += 1
        stats[f"domain:{record['domain']}"] += 1
        written += 1

    await queue.join()
    await asyncio.gather(*workers)
    return stats


def append_record(output_dir: Path, record: dict[str, Any]) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    target = month_output_path(output_dir, record["date_ref"])
    with target.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(record, ensure_ascii=False) + "\n")


def month_output_path(output_dir: Path, date_ref: str) -> Path:
    dt = datetime.strptime(date_ref, "%Y-%m-%d")
    return output_dir / f"{dt.year}-{dt.month:02d}.jsonl"


def extract_title(raw_html: str | None) -> str | None:
    if not raw_html:
        return None

    soup = BeautifulSoup(raw_html, "lxml")
    if soup.title and soup.title.string:
        return clean_text(soup.title.string)

    for tag in soup.find_all("meta"):
        key = (tag.get("property") or tag.get("name") or "").strip().lower()
        if key in TITLE_META_KEYS:
            content = clean_text(tag.get("content"))
            if content:
                return content

    for payload in iter_json_ld_payloads(soup):
        headline = find_first_value(payload, {"headline", "name"})
        if headline:
            return clean_text(str(headline))
    return None


def extract_published_at(
    raw_html: str | None,
    date_ref: str,
    source_rule: SourceRule,
) -> PublishedAtResult:
    if not raw_html:
        return PublishedAtResult(None, None)

    soup = BeautifulSoup(raw_html, "lxml")
    candidates: list[PublishedAtCandidate] = []

    for payload in iter_json_ld_payloads(soup):
        for key in ["datePublished", "dateCreated", "dateModified", "uploadDate"]:
            raw_value = find_first_value(payload, {key})
            if raw_value:
                dt = normalize_datetime(str(raw_value), date_ref, source_rule.prefer_dayfirst)
                if dt:
                    candidates.append(
                        PublishedAtCandidate(
                            normalized=dt.normalized,
                            raw_value=str(raw_value),
                            source="jsonld",
                            source_key=key.lower(),
                            confidence=dt.confidence,
                            alignment_days=dt.alignment_days,
                        )
                    )

    for tag in soup.find_all("time"):
        for attr in ("datetime", "content", "data-time", "dateTime"):
            raw_value = empty_to_none(tag.get(attr))
            if raw_value:
                dt = normalize_datetime(raw_value, date_ref, source_rule.prefer_dayfirst)
                if dt:
                    candidates.append(
                        PublishedAtCandidate(
                            normalized=dt.normalized,
                            raw_value=raw_value,
                            source="time_tag",
                            source_key=attr,
                            confidence=dt.confidence,
                            alignment_days=dt.alignment_days,
                        )
                    )
        text_value = clean_text(tag.get_text(" ", strip=True))
        if text_value:
            dt = normalize_datetime(text_value, date_ref, source_rule.prefer_dayfirst)
            if dt:
                candidates.append(
                    PublishedAtCandidate(
                        normalized=dt.normalized,
                        raw_value=text_value,
                        source="time_tag",
                        source_key="text",
                        confidence=dt.confidence,
                        alignment_days=dt.alignment_days,
                    )
                )

    normalized_hints = {hint.lower() for hint in (source_rule.published_at_hints or COMMON_PUBLISHED_AT_HINTS)}
    for tag in soup.find_all("meta"):
        cands = [
            (tag.get("property") or "").strip().lower(),
            (tag.get("name") or "").strip().lower(),
            (tag.get("itemprop") or "").strip().lower(),
            (tag.get("http-equiv") or "").strip().lower(),
        ]
        key = next((c for c in cands if c in normalized_hints), None)
        if key and key not in source_rule.skip_published_at_meta_keys:
            raw_value = empty_to_none(tag.get("content"))
            if raw_value:
                dt = normalize_datetime(raw_value, date_ref, source_rule.prefer_dayfirst)
                if dt:
                    candidates.append(
                        PublishedAtCandidate(
                            normalized=dt.normalized,
                            raw_value=raw_value,
                            source="meta",
                            source_key=key,
                            confidence=dt.confidence,
                            alignment_days=dt.alignment_days,
                        )
                    )

    if not candidates:
        return PublishedAtResult(None, None)

    source_priority = {
        "jsonld": 4,
        "time_tag": 3,
        "meta": 2,
        "text": 1,
    }

    def sort_key(cand: PublishedAtCandidate):
        s_score = source_priority.get(cand.source, 0)
        
        key_score = 0
        if cand.source == "jsonld":
            if cand.source_key == "datepublished": key_score = 4
            elif cand.source_key == "datecreated": key_score = 3
            elif cand.source_key == "uploaddate": key_score = 2
            elif cand.source_key == "datemodified": key_score = 1
            
        align_score = -abs(cand.alignment_days) if cand.alignment_days is not None else -9999
        conf_score = {"high": 3, "medium": 2, "low": 1, "none": 0}.get(cand.confidence, 0)
        
        return (s_score, key_score, align_score, conf_score)

    best_cand = max(candidates, key=sort_key)
    
    alignment_str = "unknown"
    if best_cand.alignment_days == 0:
        alignment_str = "same_day"
    elif best_cand.alignment_days == 1:
        alignment_str = "adjacent"
    elif best_cand.alignment_days is not None and best_cand.alignment_days > 1:
        alignment_str = "mismatch"

    return PublishedAtResult(
        value=best_cand.normalized,
        raw_value=best_cand.raw_value,
        source=best_cand.source,
        confidence=best_cand.confidence,
        alignment=alignment_str,
        alignment_days=best_cand.alignment_days,
    )


def iter_json_ld_payloads(soup: BeautifulSoup) -> Iterable[Any]:
    for tag in soup.find_all("script", attrs={"type": re.compile(r"ld\+json", re.I)}):
        content = tag.string or tag.get_text()
        if not content:
            continue
        try:
            yield json.loads(content)
        except json.JSONDecodeError:
            continue


def find_first_value(payload: Any, candidate_keys: set[str]) -> Any | None:
    if isinstance(payload, dict):
        for key, value in payload.items():
            if key in candidate_keys and value not in (None, ""):
                return value
        for value in payload.values():
            found = find_first_value(value, candidate_keys)
            if found not in (None, ""):
                return found
    elif isinstance(payload, list):
        for item in payload:
            found = find_first_value(item, candidate_keys)
            if found not in (None, ""):
                return found
    return None


def parse_date_candidates(raw_value: str) -> list[tuple[datetime, bool]]:
    value = clean_text(raw_value)
    if not value:
        return []
        
    is_ambiguous = bool(AMBIGUOUS_DATE_RE.search(value))
    results = []
    
    if is_ambiguous:
        try:
            pd_true = date_parser.parse(value, fuzzy=True, dayfirst=True)
            results.append((pd_true, True))
        except (ValueError, TypeError, OverflowError):
            pass
        try:
            pd_false = date_parser.parse(value, fuzzy=True, dayfirst=False)
            results.append((pd_false, False))
        except (ValueError, TypeError, OverflowError):
            pass
    else:
        try:
            pd = date_parser.parse(value, fuzzy=True)
            results.append((pd, True))
        except (ValueError, TypeError, OverflowError):
            pass
            
    return results


def format_iso(parsed: datetime, timezone: str = DEFAULT_TIMEZONE) -> str:
    tz = ZoneInfo(timezone)
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=tz)
    else:
        parsed = parsed.astimezone(tz)
    return parsed.isoformat(timespec="seconds")


def classify_payload(payload: FetchPayload) -> str:
    if payload.http_status == 404:
        return "failed_404"
    if payload.http_status in FALLBACK_STATUS_CODES:
        return "failed_blocked"
    if payload.error and "timed out" in payload.error.lower():
        return "failed_timeout"
    if payload.raw_html and looks_blocked(payload.raw_html):
        return "failed_blocked"
    if payload.content_type and not is_html_content_type(payload.content_type):
        return "failed_other"
    if payload.raw_html and len(payload.raw_html.strip()) < 1024:
        return "failed_other"
    if payload.raw_html and (payload.http_status is None or 200 <= payload.http_status < 400):
        return "success"
    return "failed_other"


def should_browser_fallback(payload: FetchPayload) -> bool:
    if payload.status in {"failed_timeout", "failed_blocked"}:
        return True
    if payload.http_status in FALLBACK_STATUS_CODES:
        return True
    if not payload.raw_html:
        return True
    if payload.raw_html and len(payload.raw_html.strip()) < 1024:
        return True
    if payload.raw_html and looks_blocked(payload.raw_html):
        return True
    return False


def looks_blocked(raw_html: str) -> bool:
    lowered = raw_html.lower()
    return any(marker in lowered for marker in BLOCKED_MARKERS)


def is_html_content_type(content_type: str) -> bool:
    lowered = content_type.lower()
    return any(kind in lowered for kind in HTML_CONTENT_TYPES)


def current_timestamp(timezone: str = DEFAULT_TIMEZONE) -> str:
    return datetime.now(ZoneInfo(timezone)).isoformat(timespec="seconds")


def extract_domain(url: str) -> str:
    return urlparse(url).netloc.lower()


def normalize_headers(headers: dict[str, Any]) -> dict[str, str]:
    normalized: dict[str, str] = {}
    for key, value in headers.items():
        normalized[str(key).lower()] = str(value)
    return normalized


def header_value(headers: dict[str, str], key: str) -> str | None:
    return empty_to_none(headers.get(key.lower()))


def stringify_html(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value)
    return text if text else None


def stringify_optional(value: Any) -> str | None:
    if value in (None, ""):
        return None
    return str(value)


def empty_to_none(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def clean_text(value: Any) -> str | None:
    if value is None:
        return None
    text = re.sub(r"\s+", " ", str(value)).strip()
    return text or None


def coerce_int(value: Any) -> int | None:
    if value in (None, ""):
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def make_error_payload(
    url: str,
    fetch_method: str,
    status: str,
    error: str | None,
    timezone: str = DEFAULT_TIMEZONE,
) -> FetchPayload:
    return FetchPayload(
        input_url=url,
        final_url=None,
        raw_html=None,
        http_status=None,
        headers={},
        fetch_method=fetch_method,
        collected_at=current_timestamp(timezone),
        content_type=None,
        status=status,
        error=error or status,
    )


def combine_errors(*parts: str | None) -> str | None:
    cleaned = [part.strip() for part in parts if part and part.strip()]
    if not cleaned:
        return None
    return " | ".join(cleaned)

def normalize_datetime(
    raw_value: str | None,
    date_ref: str,
    prefer_dayfirst: bool = True,
    timezone: str = DEFAULT_TIMEZONE,
) -> ParsedDateTime | None:
    value = clean_text(raw_value)
    if not value:
        return None

    try:
        dt_ref = datetime.strptime(date_ref, "%Y-%m-%d").date()
    except Exception:
        dt_ref = None

    tz = ZoneInfo(timezone)

    def diff_days(d: datetime) -> int | None:
        if dt_ref:
            return abs((d.date() - dt_ref).days)
        return None

    if ISO_DATE_RE.search(value) or YEAR_FIRST_DATE_RE.search(value):
        try:
            parsed = date_parser.parse(value)
            parsed = parsed.replace(tzinfo=tz) if parsed.tzinfo is None else parsed.astimezone(tz)
            return ParsedDateTime(parsed.isoformat(timespec="seconds"), "high", diff_days(parsed))
        except Exception:
            pass

    try:
        parsed = date_parser.parse(value, dayfirst=prefer_dayfirst, fuzzy=True)
        parsed = parsed.replace(tzinfo=tz) if parsed.tzinfo is None else parsed.astimezone(tz)
        
        is_fallback_text = any(t in value.lower() for t in TEXT_FALLBACK_TOKENS)
        confidence = "low" if is_fallback_text else "medium"
        return ParsedDateTime(parsed.isoformat(timespec="seconds"), confidence, diff_days(parsed))
    except Exception:
        return None


def classify_payload(payload: FetchPayload) -> str:
    if payload.http_status == 404:
        return "failed_404"
    if payload.http_status in FALLBACK_STATUS_CODES:
        return "failed_blocked"
    if payload.error and "timed out" in payload.error.lower():
        return "failed_timeout"
    if payload.raw_html and looks_blocked(payload.raw_html):
        return "failed_blocked"
    if payload.content_type and not is_html_content_type(payload.content_type):
        return "failed_other"
    if payload.raw_html and len(payload.raw_html.strip()) < 1024:
        return "failed_other"
    if payload.raw_html and (payload.http_status is None or 200 <= payload.http_status < 400):
        return "success"
    return "failed_other"


def should_browser_fallback(payload: FetchPayload) -> bool:
    if payload.status in {"failed_timeout", "failed_blocked"}:
        return True
    if payload.http_status in FALLBACK_STATUS_CODES:
        return True
    if not payload.raw_html:
        return True
    if payload.raw_html and len(payload.raw_html.strip()) < 1024:
        return True
    if payload.raw_html and looks_blocked(payload.raw_html):
        return True
    return False


def looks_blocked(raw_html: str) -> bool:
    lowered = raw_html.lower()
    return any(marker in lowered for marker in BLOCKED_MARKERS)


def is_html_content_type(content_type: str) -> bool:
    lowered = content_type.lower()
    return any(kind in lowered for kind in HTML_CONTENT_TYPES)


def current_timestamp(timezone: str = DEFAULT_TIMEZONE) -> str:
    return datetime.now(ZoneInfo(timezone)).isoformat(timespec="seconds")


def extract_domain(url: str) -> str:
    return urlparse(url).netloc.lower()


def normalize_headers(headers: dict[str, Any]) -> dict[str, str]:
    normalized: dict[str, str] = {}
    for key, value in headers.items():
        normalized[str(key).lower()] = str(value)
    return normalized


def header_value(headers: dict[str, str], key: str) -> str | None:
    return empty_to_none(headers.get(key.lower()))


def stringify_html(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value)
    return text if text else None


def stringify_optional(value: Any) -> str | None:
    if value in (None, ""):
        return None
    return str(value)


def empty_to_none(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def clean_text(value: Any) -> str | None:
    if value is None:
        return None
    text = re.sub(r"\s+", " ", str(value)).strip()
    return text or None


def coerce_int(value: Any) -> int | None:
    if value in (None, ""):
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def make_error_payload(
    url: str,
    fetch_method: str,
    status: str,
    error: str | None,
    timezone: str = DEFAULT_TIMEZONE,
) -> FetchPayload:
    return FetchPayload(
        input_url=url,
        final_url=None,
        raw_html=None,
        http_status=None,
        headers={},
        fetch_method=fetch_method,
        collected_at=current_timestamp(timezone),
        content_type=None,
        status=status,
        error=error or status,
    )


def combine_errors(*parts: str | None) -> str | None:
    cleaned = [part.strip() for part in parts if part and part.strip()]
    if not cleaned:
        return None
    return " | ".join(cleaned)
