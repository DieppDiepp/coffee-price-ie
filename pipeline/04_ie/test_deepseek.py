"""
test_deepseek.py — Test 5 bài qua DeepSeek API + phân tích token & cache.

Usage:
  cd pipeline/04_ie
  python test_deepseek.py
"""
import sys, json, time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from dotenv import load_dotenv
load_dotenv(Path(__file__).resolve().parent / ".env")

import pandas as pd
from extraction_config import (
    DISCOVER_CSV, ARTICLES_CSV, DATE_START, DATE_END, DEFAULT_MAX_CHARS,
    MAX_TOKENS_OUT,
)
from content_cleaner import smart_truncate
from llm_client import init_client
from prompts import SYSTEM_PROMPT, USER_PROMPT_TEMPLATE


def load_sample(n=5):
    dl = pd.read_csv(DISCOVER_CSV)
    dl["PUBLISHED_DATE"] = pd.to_datetime(dl["PUBLISHED_DATE"], errors="coerce")
    dl = dl.dropna(subset=["PUBLISHED_DATE"])
    dl = dl[(dl["PUBLISHED_DATE"] >= DATE_START) & (dl["PUBLISHED_DATE"] <= DATE_END)]
    ts = dl["TITLE"].fillna("") + " " + dl["SNIPPET"].fillna("")
    dl = dl[ts.str.contains("cà phê", case=False, na=False)]
    dl = dl.sort_values("DISCOVERED_AT").drop_duplicates(
        subset=["URL_HASH", "TARGET"], keep="first")
    dl_meta = dl.drop_duplicates(subset=["URL_HASH"], keep="first")[
        ["URL_HASH", "TITLE", "SNIPPET", "PUBLISHED_DATE", "TARGET", "DOMAIN"]
    ].copy()
    ca = pd.read_csv(ARTICLES_CSV)
    ca = ca[ca["URL_HASH"].isin(set(dl_meta["URL_HASH"]))].copy()
    merged = ca[["URL_HASH", "CONTENT"]].merge(dl_meta, on="URL_HASH", how="inner")
    merged["PUBLISHED_DATE"] = pd.to_datetime(merged["PUBLISHED_DATE"])
    return merged.sample(n, random_state=42)


def main():
    sample = load_sample(5)
    client, model = init_client("deepseek")

    print("\n" + "=" * 60)
    print("PROMPT SIZE ANALYSIS")
    print("=" * 60)
    print(f"System prompt: {len(SYSTEM_PROMPT):,} chars")

    print("\n" + "=" * 60)
    print("RUNNING 5 TEST ARTICLES")
    print("=" * 60)

    all_usage = []
    for i, (_, row) in enumerate(sample.iterrows()):
        title = str(row["TITLE"] or "")
        snippet = str(row["SNIPPET"] or "")
        pub_date = (row["PUBLISHED_DATE"].strftime("%Y-%m-%d")
                    if pd.notna(row["PUBLISHED_DATE"]) else "unknown")
        content = smart_truncate(str(row["CONTENT"] or ""),
                                 max_chars=DEFAULT_MAX_CHARS)
        user_msg = USER_PROMPT_TEMPLATE.format(
            title=title, snippet=snippet,
            pub_date=pub_date, content=content)

        print(f"\n--- Article {i+1} ---")
        print(f"TITLE: {title[:80]}")
        print(f"Content chars: {len(content):,} | User msg chars: {len(user_msg):,}")

        t0 = time.time()
        try:
            resp = client.chat.completions.create(
                model=model,
                messages=[
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user",   "content": user_msg},
                ],
                max_tokens=MAX_TOKENS_OUT,
                temperature=0.0,
                response_format={"type": "json_object"},
                extra_body={"thinking": {"type": "disabled"}},
            )
            elapsed = time.time() - t0

            # Check for reasoning_content (thinking model)
            msg = resp.choices[0].message
            reasoning = getattr(msg, 'reasoning_content', None)
            if reasoning:
                print(f"REASONING ({len(reasoning)} chars): {reasoning[:200]}...")

            raw = msg.content
            if raw is None:
                raw = ""
            raw = raw.strip()

            print(f"RAW RESPONSE ({len(raw)} chars):")
            print(f"  >>>{raw[:500]}<<<")

            clean = raw
            if clean.startswith("```"):
                parts = clean.split("```")
                if len(parts) >= 2:
                    clean = parts[1]
                    if clean.startswith("json"):
                        clean = clean[4:]
                    clean = clean.strip()
            result = json.loads(clean)

            usage = resp.usage
            prompt_tok = usage.prompt_tokens if usage else 0
            comp_tok = usage.completion_tokens if usage else 0
            total_tok = usage.total_tokens if usage else 0

            # DeepSeek returns cache info in usage
            cache_hit = getattr(usage, 'prompt_cache_hit_tokens', None)
            cache_miss = getattr(usage, 'prompt_cache_miss_tokens', None)

            print(f"PARSED: {json.dumps(result, ensure_ascii=False)}")
            print(f"TOKENS: prompt={prompt_tok} | completion={comp_tok} | total={total_tok}")
            if cache_hit is not None:
                print(f"CACHE:  hit={cache_hit} | miss={cache_miss}")
            print(f"TIME:   {elapsed:.2f}s")

            # Print full usage dict for debugging
            if hasattr(usage, 'model_dump'):
                ud = usage.model_dump()
            elif hasattr(usage, '__dict__'):
                ud = {k: v for k, v in usage.__dict__.items() if not k.startswith('_')}
            else:
                ud = {}
            extra = {k: v for k, v in ud.items()
                     if k not in ('prompt_tokens', 'completion_tokens', 'total_tokens')
                     and v is not None}
            if extra:
                print(f"EXTRA:  {extra}")

            all_usage.append({
                "prompt_tokens": prompt_tok,
                "completion_tokens": comp_tok,
                "total_tokens": total_tok,
                "content_chars": len(content),
                "user_msg_chars": len(user_msg),
                "elapsed": elapsed,
                "cache_hit": cache_hit,
                "cache_miss": cache_miss,
            })

        except json.JSONDecodeError as e:
            elapsed = time.time() - t0
            print(f"JSON ERROR: {e}")
            print(f"TIME:  {elapsed:.2f}s")
        except Exception as e:
            elapsed = time.time() - t0
            print(f"ERROR: {type(e).__name__}: {e}")
            print(f"TIME:  {elapsed:.2f}s")

        time.sleep(0.5)

    # ── Summary ──
    if all_usage:
        print("\n" + "=" * 60)
        print("SUMMARY")
        print("=" * 60)
        n = len(all_usage)
        avg = lambda key: sum(u[key] for u in all_usage) / n

        avg_prompt = avg("prompt_tokens")
        avg_comp = avg("completion_tokens")
        avg_total = avg("total_tokens")
        avg_chars = avg("content_chars")
        avg_time = avg("elapsed")

        print(f"Avg prompt tokens:     {avg_prompt:.0f}")
        print(f"Avg completion tokens: {avg_comp:.0f}")
        print(f"Avg total tokens:      {avg_total:.0f}")
        print(f"Avg content chars:     {avg_chars:.0f}")
        print(f"Avg response time:     {avg_time:.2f}s")

        # Cache analysis
        hits = [u["cache_hit"] for u in all_usage if u["cache_hit"] is not None]
        misses = [u["cache_miss"] for u in all_usage if u["cache_miss"] is not None]
        if hits:
            print(f"\nCache hit tokens:  {hits}")
            print(f"Cache miss tokens: {misses}")
            avg_hit = sum(hits) / len(hits)
            avg_miss = sum(misses) / len(misses)
            hit_rate = avg_hit / (avg_hit + avg_miss) * 100 if (avg_hit + avg_miss) > 0 else 0
            print(f"Avg cache hit rate: {hit_rate:.1f}%")

        # Cost for 7k articles
        N = 7000
        total_in = N * avg_prompt
        total_out = N * avg_comp
        cost_miss = total_in / 1e6 * 0.14 + total_out / 1e6 * 0.28
        cost_hit  = total_in / 1e6 * 0.0028 + total_out / 1e6 * 0.28

        # Mixed cost (first call miss, rest hit)
        if hits and misses:
            avg_cache_hit = sum(hits) / len(hits)
            avg_cache_miss_tok = sum(misses) / len(misses)
            # Cost with cache: miss portion at $0.14, hit portion at $0.0028
            cost_mixed = (N * avg_cache_miss_tok / 1e6 * 0.14 +
                          N * avg_cache_hit / 1e6 * 0.0028 +
                          total_out / 1e6 * 0.28)
        else:
            cost_mixed = cost_miss

        print(f"\n--- Cost estimate for {N:,} articles ---")
        print(f"All cache MISS:  ${cost_miss:.3f}")
        print(f"All cache HIT:   ${cost_hit:.3f}")
        print(f"Mixed (actual):  ${cost_mixed:.3f}")
        print(f"Budget: $2.00 → {'OK' if cost_mixed < 2 else 'OVER BUDGET'}")


if __name__ == "__main__":
    main()
