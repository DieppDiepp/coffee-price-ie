"""
llm_extraction.py — Main entry point.

Usage:
  # DeepSeek (re nhat, chay 1 lan la xong ~$0.70):
  export DEEPSEEK_API_KEY="sk-..."
  python pipeline/04_ie/llm_extraction.py --provider deepseek

  # OpenAI:
  export OPENAI_API_KEY="sk-..."
  python pipeline/04_ie/llm_extraction.py --provider openai

  # Test truoc:
  python pipeline/04_ie/llm_extraction.py --provider deepseek --limit 20 --dry-run

  # Resume (tu dong skip bai da xu ly):
  python pipeline/04_ie/llm_extraction.py --provider deepseek
"""
import argparse
import sys
import time
import warnings
from pathlib import Path

import pandas as pd
import numpy as np

# Add parent to path so imports work when run from project root
sys.path.insert(0, str(Path(__file__).resolve().parent))

from extraction_config import (
    DISCOVER_CSV, ARTICLES_CSV, CACHE_FILE, OUTPUT_FILE,
    DATE_START, DATE_END, DEFAULT_MAX_CHARS,
    SAVE_EVERY, SLEEP_BETWEEN, PRICE_MIN, PRICE_MAX,
)
from content_cleaner import smart_truncate
from llm_client import init_client, extract_one

warnings.filterwarnings("ignore")


# ═══════════════════════════════════════════════════════════════════
# DATA LOADING
# ═══════════════════════════════════════════════════════════════════
def load_articles():
    """Load articles da qua relevance filter, merge TITLE+SNIPPET."""
    print("Loading data...")
    dl = pd.read_csv(DISCOVER_CSV)
    dl["PUBLISHED_DATE"] = pd.to_datetime(dl["PUBLISHED_DATE"], errors="coerce")
    dl = dl.dropna(subset=["PUBLISHED_DATE"])
    dl = dl[(dl["PUBLISHED_DATE"] >= DATE_START) & (dl["PUBLISHED_DATE"] <= DATE_END)]

    ts = dl["TITLE"].fillna("") + " " + dl["SNIPPET"].fillna("")
    dl = dl[ts.str.contains("cà phê", case=False, na=False)]
    dl = dl.sort_values("DISCOVERED_AT").drop_duplicates(
        subset=["URL_HASH", "TARGET"], keep="first")
    relevant_hashes = set(dl["URL_HASH"].unique())
    print(f"  Relevant hashes: {len(relevant_hashes):,}")

    dl_meta = dl.drop_duplicates(subset=["URL_HASH"], keep="first")[
        ["URL_HASH", "TITLE", "SNIPPET", "PUBLISHED_DATE", "TARGET", "DOMAIN"]
    ].copy()

    ca = pd.read_csv(ARTICLES_CSV)
    ca = ca[ca["URL_HASH"].isin(relevant_hashes)].copy()
    print(f"  Articles with CONTENT: {len(ca):,}")

    merged = ca[["URL_HASH", "CONTENT"]].merge(dl_meta, on="URL_HASH", how="inner")
    merged["PUBLISHED_DATE"] = pd.to_datetime(merged["PUBLISHED_DATE"])
    print(f"  Final for LLM: {len(merged):,}")
    return merged


# ═══════════════════════════════════════════════════════════════════
# CACHE
# ═══════════════════════════════════════════════════════════════════
def load_cache():
    if CACHE_FILE.exists():
        df = pd.read_csv(CACHE_FILE)
        ok = df[df["_status"] == "ok"]
        skipped = df[df["_status"] != "ok"]
        records = ok.to_dict("records")
        done = set(ok["url_hash"].tolist())
        print(f"  Cache: {len(done):,} ok, {len(skipped):,} errors (will retry)")
        return records, done
    return [], set()


def save_cache(records):
    pd.DataFrame(records).to_csv(CACHE_FILE, index=False)


# ═══════════════════════════════════════════════════════════════════
# EXTRACTION LOOP
# ═══════════════════════════════════════════════════════════════════
def run_extraction(articles, provider, limit=None, dry_run=False,
                   max_chars=DEFAULT_MAX_CHARS):
    print("\n" + "=" * 55)
    print("LLM Extraction")
    print("=" * 55)

    records, done_hashes = load_cache()
    pending = articles[~articles["URL_HASH"].isin(done_hashes)]
    if limit:
        pending = pending.head(limit)
    print(f"  Pending: {len(pending):,}")

    if len(pending) == 0:
        print("  Nothing to do!")
        return records

    # Smart truncation
    print("  Truncating content...")
    pending = pending.copy()
    pending["_trunc"] = pending["CONTENT"].fillna("").apply(
        lambda x: smart_truncate(x, max_chars=max_chars))

    avg_ch = pending["_trunc"].apply(len).mean()
    est_in  = len(pending) * (avg_ch / 2.5 + 250)
    est_out = len(pending) * 80
    est_tot = est_in + est_out
    cost_ds = est_in / 1e6 * 0.14 + est_out / 1e6 * 0.28
    print(f"  Avg content: {avg_ch:.0f} chars")
    print(f"  Est. tokens: {est_tot:,.0f} (in={est_in:,.0f} out={est_out:,.0f})")
    print(f"  Est. DeepSeek cost: ${cost_ds:.2f}")

    if dry_run:
        print("\n  [DRY RUN] 3 samples:\n")
        for _, row in pending.head(3).iterrows():
            print(f"  TITLE: {row['TITLE'][:80]}")
            print(f"  TRUNCATED ({len(row['_trunc'])} chars):")
            print(f"    {row['_trunc'][:200]}...")
            print()
        return records

    client, model = init_client(provider)
    total_tok, n_ok, n_err = 0, 0, 0
    t0 = time.time()

    for i, (_, row) in enumerate(pending.iterrows()):
        pub_date = (row["PUBLISHED_DATE"].strftime("%Y-%m-%d")
                    if pd.notna(row["PUBLISHED_DATE"]) else "unknown")

        result = extract_one(
            client, model,
            title=str(row["TITLE"] or ""),
            snippet=str(row["SNIPPET"] or ""),
            pub_date=pub_date,
            content=row["_trunc"],
        )
        result["url_hash"] = row["URL_HASH"]

        # Validate price
        pv = result.get("price_vnd")
        if pv is not None:
            try:
                pv = int(pv)
                if not (PRICE_MIN <= pv <= PRICE_MAX):
                    result["price_vnd"] = None
            except (ValueError, TypeError):
                result["price_vnd"] = None

        records.append(result)
        total_tok += result.get("_tokens_used", 0)
        if result["_status"] == "ok":
            n_ok += 1
        else:
            n_err += 1

        if (i + 1) % 10 == 0:
            el = time.time() - t0
            rate = (i + 1) / el * 60
            pct = (i + 1) / len(pending) * 100
            print(f"  [{i+1:,}/{len(pending):,}] {pct:.1f}% | "
                  f"{rate:.0f}/min | tok={total_tok:,} | "
                  f"ok={n_ok} err={n_err}", end="\r")

        if (i + 1) % SAVE_EVERY == 0:
            save_cache(records)

        time.sleep(SLEEP_BETWEEN)

    save_cache(records)
    el = time.time() - t0
    print(f"\n\n  Done! {len(pending):,} in {el:.0f}s")
    print(f"  ok={n_ok:,} err={n_err:,} tokens={total_tok:,}")
    return records


# ═══════════════════════════════════════════════════════════════════
# POST-PROCESS
# ═══════════════════════════════════════════════════════════════════
def post_process(records, articles):
    print("\n" + "=" * 55)
    print("Post-processing")
    print("=" * 55)

    ext = pd.DataFrame(records)
    print(f"  Total: {len(ext):,}")
    print(f"  Status: {ext['_status'].value_counts().to_dict()}")

    if "is_coffee_price" in ext.columns:
        n_coffee = ext["is_coffee_price"].sum()
        print(f"  is_coffee_price=True: {n_coffee:,} ({n_coffee/len(ext):.1%})")

    if "direction" in ext.columns:
        print(f"  Direction: {ext['direction'].value_counts().to_dict()}")

    prices = pd.to_numeric(ext.get("price_vnd"), errors="coerce").dropna()
    vp = prices[(prices >= PRICE_MIN) & (prices <= PRICE_MAX)]
    if len(vp) > 0:
        print(f"  Valid prices: {len(vp):,} ({vp.min():,.0f} - {vp.max():,.0f})")

    certs = pd.to_numeric(ext.get("certainty"), errors="coerce").dropna()
    if len(certs) > 0:
        print(f"  Certainty: mean={certs.mean():.2f}, dist={certs.value_counts().sort_index().to_dict()}")

    # Date mismatch
    meta = articles[["URL_HASH", "PUBLISHED_DATE"]].drop_duplicates(subset=["URL_HASH"])
    ext2 = ext.merge(meta, left_on="url_hash", right_on="URL_HASH", how="left")
    ext2["cd"] = pd.to_datetime(ext2.get("content_date"), errors="coerce")
    has = ext2.dropna(subset=["cd", "PUBLISHED_DATE"])
    if len(has) > 0:
        dd = (has["cd"] - has["PUBLISHED_DATE"]).dt.days.abs()
        nm = (dd > 2).sum()
        print(f"  Date mismatch (>2d): {nm:,}/{len(has):,} ({nm/len(has):.1%})")

    OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)
    ext.to_csv(OUTPUT_FILE, index=False)
    print(f"\n  Exported: {OUTPUT_FILE}")


# ═══════════════════════════════════════════════════════════════════
# MAIN
# ═══════════════════════════════════════════════════════════════════
def main():
    p = argparse.ArgumentParser(
        description="LLM extraction for coffee price articles")
    p.add_argument("--provider", default="deepseek",
                   choices=["openai", "deepseek"],
                   help="API provider (default: deepseek)")
    p.add_argument("--limit", type=int, default=None,
                   help="Max articles to process")
    p.add_argument("--dry-run", action="store_true",
                   help="Preview only, no API calls")
    p.add_argument("--max-chars", type=int, default=DEFAULT_MAX_CHARS,
                   help=f"Max chars per article (default: {DEFAULT_MAX_CHARS})")
    args = p.parse_args()

    print("=" * 55)
    print("  LLM Extraction — Coffee Price Information")
    print("=" * 55 + "\n")

    articles = load_articles()
    records = run_extraction(
        articles, provider=args.provider,
        limit=args.limit, dry_run=args.dry_run,
        max_chars=args.max_chars)

    if not args.dry_run and records:
        post_process(records, articles)

    print("\nDone.")


if __name__ == "__main__":
    main()
