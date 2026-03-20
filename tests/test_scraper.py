from __future__ import annotations

import asyncio
import importlib.util
import json
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
EXTRACTORS_PATH = REPO_ROOT / "pipeline" / "02_scraper" / "extractors.py"


def load_extractors():
    module_name = "scraper_extractors_test"
    if module_name in sys.modules:
        return sys.modules[module_name]

    spec = importlib.util.spec_from_file_location(module_name, EXTRACTORS_PATH)
    module = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    return module


extractors = load_extractors()


class MockHttpClient:
    def __init__(self, responses):
        self.responses = responses
        self.calls = []

    async def fetch(self, url, source_rule):
        self.calls.append((url, source_rule.source_id))
        payload = self.responses[url]
        return payload


class MockBrowserClient:
    def __init__(self, responses):
        self.responses = responses
        self.calls = []
        self.closed = False

    async def fetch(self, url, source_rule):
        self.calls.append((url, source_rule.source_id))
        payload = self.responses[url]
        return payload

    async def close(self):
        self.closed = True


def read_jsonl(path: Path):
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def test_flatten_discovered_inputs(tmp_path):
    input_path = tmp_path / "demo.jsonl"
    input_path.write_text(
        "\n".join(
            [
                json.dumps(
                    {
                        "date": "2026-03-01",
                        "results": [
                            {
                                "rank": 1,
                                "url": "https://example.com/a",
                                "domain": "example.com",
                                "title": "A",
                            }
                        ],
                    },
                    ensure_ascii=False,
                ),
                json.dumps(
                    {
                        "date": "2026-03-02",
                        "results": [
                            {
                                "rank": 2,
                                "url": "https://example.com/b",
                                "title": "B",
                            }
                        ],
                    },
                    ensure_ascii=False,
                ),
            ]
        ),
        encoding="utf-8",
    )

    occurrences = extractors.flatten_discovered_inputs([input_path])

    assert len(occurrences) == 2
    assert occurrences[0].date_ref == "2026-03-01"
    assert occurrences[0].domain == "example.com"
    assert occurrences[1].date_ref == "2026-03-02"
    assert occurrences[1].domain == "example.com"
    assert occurrences[1].discovery_rank == 2


def test_load_resume_index(tmp_path):
    output_dir = tmp_path / "02_raw_articles"
    output_dir.mkdir()
    (output_dir / "2026-03.jsonl").write_text(
        "\n".join(
            [
                json.dumps({"url": "https://example.com/a", "date_ref": "2026-03-01"}),
                json.dumps({"url": "https://example.com/a", "date_ref": "2026-03-02"}),
            ]
        ),
        encoding="utf-8",
    )

    index = extractors.load_resume_index(output_dir)

    assert ("https://example.com/a", "2026-03-01") in index
    assert ("https://example.com/a", "2026-03-02") in index


def test_extract_title_and_published_at():
    raw_html = """
    <html>
      <head>
        <title>Fallback Title</title>
        <meta property="og:title" content="OG Title" />
        <meta property="article:published_time" content="2026-03-11T07:15:00" />
        <script type="application/ld+json">
          {"headline":"JSON Title","datePublished":"2026-03-11T07:15:00+07:00"}
        </script>
      </head>
      <body></body>
    </html>
    """

    title = extractors.extract_title(raw_html)
    source_rule = extractors.SourceRule(source_id="test", published_at_hints=["article:published_time"])
    pub_result = extractors.extract_published_at(raw_html, "2026-03-11", source_rule)

    assert title == "Fallback Title"
    assert pub_result.value == "2026-03-11T07:15:00+07:00"
    assert pub_result.raw_value == "2026-03-11T07:15:00+07:00"
    assert pub_result.source == "jsonld"
    assert pub_result.alignment == "same_day"

def test_baomoi_jsonld_priority():
    raw_html = """
    <html>
      <head>
        <meta property="article:published_time" content="2021-04-07T00:00:00" />
        <script type="application/ld+json">
          {"datePublished":"2026-03-02T10:00:00+07:00"}
        </script>
      </head>
      <body></body>
    </html>
    """
    source_rule = extractors.SourceRule(source_id="baomoi", published_at_priority=["jsonld", "meta"])
    pub_result = extractors.extract_published_at(raw_html, "2026-03-02", source_rule)
    
    assert pub_result.value == "2026-03-02T10:00:00+07:00"
    assert pub_result.source == "jsonld"

def test_ambiguous_date():
    raw_html = '<html><body><time>2/3/2026</time></body></html>'
    source_rule_dayfirst = extractors.SourceRule(source_id="test", prefer_dayfirst=True)
    source_rule_monthfirst = extractors.SourceRule(source_id="test", prefer_dayfirst=False)
    
    # Should be parsed as March 2 (day 2, month 3)
    res1 = extractors.extract_published_at(raw_html, "2026-05-01", source_rule_dayfirst)
    assert "2026-03-02" in res1.value
    
    # Should be parsed as Feb 3 (month 2, day 3)
    res2 = extractors.extract_published_at(raw_html, "2026-05-01", source_rule_monthfirst)
    assert "2026-02-03" in res2.value

def test_mismatch_date():
    raw_html = '<html><body><meta name="date" content="2025-01-01"></body></html>'
    source_rule = extractors.SourceRule(source_id="test", published_at_hints=["date"])
    
    res = extractors.extract_published_at(raw_html, "2026-03-02", source_rule)
    assert "2025-01-01" in res.value
    assert res.alignment == "mismatch"
    assert res.alignment_days is not None and res.alignment_days > 1

def test_no_timestamp():
    raw_html = '<html><body><p>No date here</p></body></html>'
    source_rule = extractors.SourceRule(source_id="test")
    res = extractors.extract_published_at(raw_html, "2026-03-02", source_rule)
    assert res.value is None
    assert res.alignment == "unknown"


def test_classify_payload_variants():
    blocked = extractors.FetchPayload(
        input_url="https://example.com",
        final_url="https://example.com",
        raw_html="<html>Access denied</html>",
        http_status=403,
        headers={"content-type": "text/html"},
        fetch_method="http",
        collected_at="2026-03-11T10:00:00+07:00",
        content_type="text/html",
        status="failed_other",
    )
    non_html = extractors.FetchPayload(
        input_url="https://example.com/file",
        final_url="https://example.com/file",
        raw_html="binary-ish",
        http_status=200,
        headers={"content-type": "application/pdf"},
        fetch_method="http",
        collected_at="2026-03-11T10:00:00+07:00",
        content_type="application/pdf",
        status="failed_other",
    )

    assert extractors.classify_payload(blocked) == "failed_blocked"
    assert extractors.classify_payload(non_html) == "failed_other"


def test_redirect_cache_reuses_final_url(tmp_path):
    output_dir = tmp_path / "02_raw_articles"
    output_dir.mkdir()

    occurrence_a = extractors.Occurrence(
        url="https://example.com/redirect",
        domain="example.com",
        date_ref="2026-03-01",
        discovery_rank=1,
    )
    occurrence_b = extractors.Occurrence(
        url="https://example.com/final",
        domain="example.com",
        date_ref="2026-03-02",
        discovery_rank=2,
    )

    payload = extractors.FetchPayload(
        input_url="https://example.com/redirect",
        final_url="https://example.com/final",
        raw_html="<html><head><title>Article</title></head><body>" + ("x" * 1200) + "</body></html>",
        http_status=200,
        headers={"content-type": "text/html"},
        fetch_method="http",
        collected_at="2026-03-11T10:00:00+07:00",
        content_type="text/html",
        status="success",
    )

    http_client = MockHttpClient({"https://example.com/redirect": payload})
    scraper = extractors.HybridScraper(http_client=http_client, browser_client=None, browser_enabled=False)
    default_rule = extractors.SourceRule(source_id="generic")

    stats = asyncio.run(
        extractors.process_occurrences(
            occurrences=[occurrence_a, occurrence_b],
            output_dir=output_dir,
            scraper=scraper,
            source_lookup=lambda _: default_rule,
            resume_index=set(),
            worker_count=1,
        )
    )
    asyncio.run(scraper.close())

    rows = read_jsonl(output_dir / "2026-03.jsonl")
    assert stats["written"] == 2
    assert len(http_client.calls) == 1
    assert [row["url"] for row in rows] == [
        "https://example.com/redirect",
        "https://example.com/final",
    ]
    assert all(row["final_url"] == "https://example.com/final" for row in rows)


def test_browser_fallback_and_resume(tmp_path):
    output_dir = tmp_path / "02_raw_articles"
    output_dir.mkdir()

    occurrences = [
        extractors.Occurrence(
            url="https://blocked.example.com/article",
            domain="blocked.example.com",
            date_ref="2026-03-01",
            discovery_rank=1,
        ),
        extractors.Occurrence(
            url="https://blocked.example.com/article",
            domain="blocked.example.com",
            date_ref="2026-03-02",
            discovery_rank=2,
        ),
    ]

    http_payload = extractors.FetchPayload(
        input_url="https://blocked.example.com/article",
        final_url="https://blocked.example.com/article",
        raw_html="<html>Access denied</html>",
        http_status=403,
        headers={"content-type": "text/html"},
        fetch_method="http",
        collected_at="2026-03-11T10:00:00+07:00",
        content_type="text/html",
        status="failed_blocked",
        error="HTTP 403",
    )
    browser_payload = extractors.FetchPayload(
        input_url="https://blocked.example.com/article",
        final_url="https://blocked.example.com/article",
        raw_html="<html><head><title>Recovered</title></head><body>" + ("y" * 1300) + "</body></html>",
        http_status=200,
        headers={"content-type": "text/html"},
        fetch_method="browser",
        collected_at="2026-03-11T10:01:00+07:00",
        content_type="text/html",
        status="success",
    )

    http_client = MockHttpClient({"https://blocked.example.com/article": http_payload})
    browser_client = MockBrowserClient({"https://blocked.example.com/article": browser_payload})
    scraper = extractors.HybridScraper(http_client=http_client, browser_client=browser_client, browser_enabled=True)
    default_rule = extractors.SourceRule(source_id="generic")

    first_stats = asyncio.run(
        extractors.process_occurrences(
            occurrences=occurrences,
            output_dir=output_dir,
            scraper=scraper,
            source_lookup=lambda _: default_rule,
            resume_index=set(),
            worker_count=1,
        )
    )
    asyncio.run(scraper.close())

    rows = read_jsonl(output_dir / "2026-03.jsonl")
    assert first_stats["written"] == 2
    assert len(http_client.calls) == 1
    assert len(browser_client.calls) == 1
    assert all(row["fetch_method"] == "browser" for row in rows)
    assert all(row["status"] == "success" for row in rows)

    resume_index = extractors.load_resume_index(output_dir)
    http_client_second = MockHttpClient({"https://blocked.example.com/article": http_payload})
    browser_client_second = MockBrowserClient({"https://blocked.example.com/article": browser_payload})
    scraper_second = extractors.HybridScraper(
        http_client=http_client_second,
        browser_client=browser_client_second,
        browser_enabled=True,
    )

    second_stats = asyncio.run(
        extractors.process_occurrences(
            occurrences=occurrences,
            output_dir=output_dir,
            scraper=scraper_second,
            source_lookup=lambda _: default_rule,
            resume_index=resume_index,
            worker_count=1,
        )
    )
    asyncio.run(scraper_second.close())

    assert second_stats["written"] == 0
    assert second_stats["skipped_resume"] == 2
    assert http_client_second.calls == []
    assert browser_client_second.calls == []
