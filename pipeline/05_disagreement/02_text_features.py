"""
02_text_features.py
===================
Trích xuất text-based features từ DiscoverLinks (TITLE+SNIPPET) và
coffee_articles (CONTENT) → aggregate theo ngày × TARGET → export CSV.

Pipeline:
  Tầng 1 — Relevance filter   : giữ bài có "cà phê" trong TITLE|SNIPPET
  Tầng 2 — Per-article features: ts_tang, ts_giam, ts_on_dinh, ts_price,
                                  ts_has_price, body_dir_score
  Tầng 3 — Daily aggregate     : 13 base features + lag/rolling + SIG_

Output:
  data/04_features/text_features_robusta.csv
  data/04_features/text_features_arabica.csv

Usage:
  python pipeline/05_disagreement/02_text_features.py
"""

import os
import re
import warnings
from pathlib import Path

import numpy as np
import pandas as pd

warnings.filterwarnings("ignore")

# ── Paths ─────────────────────────────────────────────────────────────────
PROJECT_ROOT = Path(__file__).resolve().parents[2]
DISCOVER_CSV = PROJECT_ROOT / "data" / "01_discovered" / "Discoverlinks.csv"
ARTICLES_CSV = PROJECT_ROOT / "data" / "03_articles" / "coffee_articles.csv"
OUTPUT_DIR   = PROJECT_ROOT / "data" / "04_features"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# ── Constants ─────────────────────────────────────────────────────────────
DATE_START = pd.Timestamp("2023-03-11")
DATE_END   = pd.Timestamp("2026-03-11")
PRICE_MIN  = 30_000   # đồng/kg
PRICE_MAX  = 250_000  # đồng/kg

# ── Regex patterns ────────────────────────────────────────────────────────
# Direction keywords
RE_TANG     = re.compile(r"\btăng\b|tăng vọt|cao hơn", re.IGNORECASE)
RE_GIAM     = re.compile(r"\bgiảm\b|sụt|lao dốc",     re.IGNORECASE)
RE_ON_DINH  = re.compile(r"ổn định|đi ngang|giữ nguyên", re.IGNORECASE)

# Price in VND: 2-3 chữ số + dấu chấm + 3 chữ số + "đồng" (vd: 57.600 đồng)
RE_PRICE_VND = re.compile(
    r"\b(\d{2,3})[.,](\d{3})\s*(?:đồng|VNĐ|VND|đ/kg|đồng/kg)",
    re.IGNORECASE,
)


# ═══════════════════════════════════════════════════════════════════════════
# STEP 1 — Load & Tầng 1: Relevance Filter
# ═══════════════════════════════════════════════════════════════════════════
def load_and_filter() -> pd.DataFrame:
    """
    Load DiscoverLinks, lọc date range, relevance filter "cà phê",
    rồi merge TITLE+SNIPPET vào coffee_articles (lấy CONTENT).
    Trả về DataFrame gồm: URL_HASH, TARGET, DOMAIN, date, TITLE, SNIPPET, CONTENT.
    """
    print("=" * 60)
    print("STEP 1 — Load & Relevance Filter")
    print("=" * 60)

    # ── 1a. Load DiscoverLinks ────────────────────────────────────────────
    dl = pd.read_csv(DISCOVER_CSV)
    dl["PUBLISHED_DATE"] = pd.to_datetime(dl["PUBLISHED_DATE"], errors="coerce")
    print(f"  DiscoverLinks loaded: {len(dl):,} rows, {dl['URL_HASH'].nunique():,} unique hashes")

    # ── 1b. Lọc date range ───────────────────────────────────────────────
    dl = dl.dropna(subset=["PUBLISHED_DATE"])
    dl = dl[(dl["PUBLISHED_DATE"] >= DATE_START) & (dl["PUBLISHED_DATE"] <= DATE_END)]
    print(f"  After date filter [{DATE_START.date()} → {DATE_END.date()}]: {len(dl):,} rows")

    # ── 1c. Relevance filter: "cà phê" in TITLE or SNIPPET ───────────────
    dl["_ts"] = dl["TITLE"].fillna("") + " " + dl["SNIPPET"].fillna("")
    mask_relevant = dl["_ts"].str.contains("cà phê", case=False, na=False)
    dl = dl[mask_relevant].copy()
    print(f"  After relevance filter ('cà phê'): {len(dl):,} rows, "
          f"{dl['URL_HASH'].nunique():,} unique hashes")

    # ── 1d. Dedup: giữ 1 row per (URL_HASH, TARGET) ─────────────────────
    #   Cùng URL_HASH + TARGET có thể xuất hiện nhiều lần (nhiều QUERY_ID).
    #   Giữ row đầu tiên (TITLE+SNIPPET giống nhau vì cùng URL).
    dl = dl.sort_values("DISCOVERED_AT").drop_duplicates(
        subset=["URL_HASH", "TARGET"], keep="first"
    )
    print(f"  After dedup (URL_HASH × TARGET): {len(dl):,} rows")

    # ── 1e. Merge với coffee_articles để lấy CONTENT ─────────────────────
    articles = pd.read_csv(ARTICLES_CSV, usecols=["URL_HASH", "CONTENT"])
    # articles có 1 row per URL_HASH
    dl = dl.merge(articles, on="URL_HASH", how="left")
    n_has_content = dl["CONTENT"].notna().sum()
    print(f"  Merged with articles: {n_has_content:,}/{len(dl):,} rows have CONTENT")

    # ── 1f. Chuẩn bị output ──────────────────────────────────────────────
    dl["date"] = dl["PUBLISHED_DATE"].dt.normalize()
    out = dl[["URL_HASH", "TARGET", "DOMAIN", "date",
              "TITLE", "SNIPPET", "CONTENT"]].copy()
    out["CONTENT"] = out["CONTENT"].fillna("")

    print(f"\n  Final per-article table: {len(out):,} rows")
    print(f"  Targets: {out['TARGET'].value_counts().to_dict()}")
    print(f"  Date range: {out['date'].min().date()} → {out['date'].max().date()}")
    return out


# ═══════════════════════════════════════════════════════════════════════════
# STEP 2 — Tầng 2: Per-article Feature Extraction
# ═══════════════════════════════════════════════════════════════════════════
def _parse_price(match: re.Match) -> float | None:
    """Convert regex match '57.600' → 57600.0, validate range."""
    try:
        value = float(match.group(1) + match.group(2))
        if PRICE_MIN <= value <= PRICE_MAX:
            return value
    except (ValueError, IndexError):
        pass
    return None


def extract_per_article(df: pd.DataFrame) -> pd.DataFrame:
    """
    Trích xuất 6 features per article từ TITLE+SNIPPET và CONTENT.
    """
    print("\n" + "=" * 60)
    print("STEP 2 — Per-article Feature Extraction")
    print("=" * 60)

    title_snippet = df["TITLE"].fillna("") + " " + df["SNIPPET"].fillna("")
    content       = df["CONTENT"].fillna("")

    # ── ts_tang, ts_giam, ts_on_dinh (from TITLE+SNIPPET) ────────────────
    df["ts_tang"]     = title_snippet.str.contains(RE_TANG,    na=False).astype(int)
    df["ts_giam"]     = title_snippet.str.contains(RE_GIAM,    na=False).astype(int)
    df["ts_on_dinh"]  = title_snippet.str.contains(RE_ON_DINH, na=False).astype(int)

    # ── ts_price, ts_has_price (from SNIPPET, ưu tiên) ────────────────────
    def extract_price(text: str) -> float:
        matches = list(RE_PRICE_VND.finditer(text))
        prices = []
        for m in matches:
            p = _parse_price(m)
            if p is not None:
                prices.append(p)
        return float(np.median(prices)) if prices else np.nan

    snippet_series = df["SNIPPET"].fillna("")
    df["ts_price"]     = snippet_series.apply(extract_price)
    df["ts_has_price"] = df["ts_price"].notna().astype(int)

    # ── body_dir_score (from CONTENT) ─────────────────────────────────────
    #   (n_tăng − n_giảm) / (n_tăng + n_giảm + 1)
    #   Chỉ tính cho bài có CONTENT (>0 ký tự).
    def calc_body_dir(text: str) -> float:
        if len(text) < 50:
            return np.nan
        n_tang = len(RE_TANG.findall(text))
        n_giam = len(RE_GIAM.findall(text))
        return (n_tang - n_giam) / (n_tang + n_giam + 1)

    df["body_dir_score"] = content.apply(calc_body_dir)

    # ── Stats ─────────────────────────────────────────────────────────────
    print(f"  ts_tang   : {df['ts_tang'].mean():.1%}")
    print(f"  ts_giam   : {df['ts_giam'].mean():.1%}")
    print(f"  ts_on_dinh: {df['ts_on_dinh'].mean():.1%}")
    print(f"  ts_has_price: {df['ts_has_price'].mean():.1%}")
    print(f"  body_dir_score available: {df['body_dir_score'].notna().mean():.1%}")

    return df


# ═══════════════════════════════════════════════════════════════════════════
# STEP 3 — Tầng 3: Daily Aggregation
# ═══════════════════════════════════════════════════════════════════════════
def aggregate_one_day(grp: pd.DataFrame) -> pd.Series:
    """Aggregate per-article features → 1 row per (TARGET, date)."""
    n = len(grp)

    # Coverage
    n_articles  = n
    n_sources   = grp["DOMAIN"].nunique()

    # Direction from TITLE+SNIPPET
    pct_tang    = grp["ts_tang"].mean()
    pct_giam    = grp["ts_giam"].mean()
    pct_on_dinh = grp["ts_on_dinh"].mean()

    # dir_score_ts = mean(ts_tang) - mean(ts_giam): media sentiment chính
    dir_score_ts = pct_tang - pct_giam

    # body_dir_score cross-check
    body_vals = grp["body_dir_score"].dropna()
    dir_score_body = body_vals.mean() if len(body_vals) > 0 else np.nan

    # Direction entropy
    probs = np.array([pct_tang, pct_giam, pct_on_dinh])
    probs = probs[probs > 0]
    dir_entropy = float(-np.sum(probs * np.log2(probs))) if len(probs) > 0 else 0.0

    # Price from snippets
    prices = grp["ts_price"].dropna()
    n_with_price    = len(prices)
    pct_has_price   = grp["ts_has_price"].mean()
    price_median    = float(prices.median()) if n_with_price > 0 else np.nan
    if n_with_price >= 2 and prices.mean() > 0:
        price_cv = float(prices.std() / prices.mean())
    else:
        price_cv = 0.0

    return pd.Series({
        "n_articles_d"       : n_articles,
        "n_sources_d"        : n_sources,
        "pct_tang_d"         : round(pct_tang, 4),
        "pct_giam_d"         : round(pct_giam, 4),
        "pct_on_dinh_d"      : round(pct_on_dinh, 4),
        "dir_score_ts_d"     : round(dir_score_ts, 4),
        "dir_score_body_d"   : round(dir_score_body, 4) if not np.isnan(dir_score_body) else np.nan,
        "dir_entropy_d"      : round(dir_entropy, 4),
        "price_cv_ts_d"      : round(price_cv, 6),
        "price_median_ts_d"  : round(price_median, 1) if not np.isnan(price_median) else np.nan,
        "pct_has_price_ts_d" : round(pct_has_price, 4),
    })


def daily_aggregate(df: pd.DataFrame) -> dict[str, pd.DataFrame]:
    """
    Group by (TARGET, date) → aggregate → split per target.
    Returns dict: {"robusta": DataFrame, "arabica": DataFrame}.
    """
    print("\n" + "=" * 60)
    print("STEP 3 — Daily Aggregation")
    print("=" * 60)

    daily = (
        df.groupby(["TARGET", "date"])
        .apply(aggregate_one_day)
        .reset_index()
    )
    daily["date"] = pd.to_datetime(daily["date"])
    print(f"  Daily rows (target × date): {len(daily):,}")

    result = {}
    for target in ["robusta", "arabica"]:
        sub = daily[daily["TARGET"] == target].drop(columns=["TARGET"]).copy()
        sub = sub.sort_values("date").reset_index(drop=True)
        result[target] = sub
        print(f"  {target}: {len(sub):,} days "
              f"[{sub['date'].min().date()} → {sub['date'].max().date()}]")

    return result


# ═══════════════════════════════════════════════════════════════════════════
# STEP 4 — Lag / Rolling Features
# ═══════════════════════════════════════════════════════════════════════════
CORE_LAG_FEATURES = [
    "dir_score_ts_d",
    "dir_score_body_d",
    "pct_tang_d",
    "pct_giam_d",
    "dir_entropy_d",
    "price_cv_ts_d",
    "n_articles_d",
    "n_sources_d",
]

CORE_ROLLING_FEATURES = [
    "dir_score_ts_d",
    "price_cv_ts_d",
    "n_articles_d",
]


def add_lag_rolling(df: pd.DataFrame, lags=(1, 2, 3), window=3) -> pd.DataFrame:
    """Thêm lag 1,2,3 + rolling mean (window=3) cho core features."""
    df = df.sort_values("date").copy()

    for col in CORE_LAG_FEATURES:
        for lag in lags:
            df[f"{col}_lag{lag}"] = df[col].shift(lag)

    for col in CORE_ROLLING_FEATURES:
        df[f"{col}_roll{window}"] = (
            df[col].shift(1).rolling(window, min_periods=1).mean()
        )

    return df


# ═══════════════════════════════════════════════════════════════════════════
# STEP 5 — Discretize → SIG_ signals
# ═══════════════════════════════════════════════════════════════════════════
def discretize(df: pd.DataFrame) -> pd.DataFrame:
    """
    Chuyển continuous features → binary SIG_ signals.
    Thresholds dùng percentile (robust với outlier), fit riêng mỗi target.
    """
    d = df.copy()

    # Direction consensus (từ TITLE+SNIPPET — tín hiệu chính)
    d["SIG_MAJORITY_TANG"]  = (d["pct_tang_d"]  > 0.50).astype(int)
    d["SIG_MAJORITY_GIAM"]  = (d["pct_giam_d"]  > 0.50).astype(int)
    d["SIG_BULLISH"]        = (d["dir_score_ts_d"] >  0.15).astype(int)
    d["SIG_BEARISH"]        = (d["dir_score_ts_d"] < -0.15).astype(int)
    d["SIG_NEUTRAL"]        = (
        (d["dir_score_ts_d"] >= -0.15) & (d["dir_score_ts_d"] <= 0.15)
    ).astype(int)

    # Direction conflict
    d["SIG_SPLIT_SIGNAL"]   = (
        (d["pct_tang_d"] > 0.25) & (d["pct_giam_d"] > 0.25)
    ).astype(int)

    # Disagreement (price CV from snippets)
    q75_cv = d["price_cv_ts_d"].quantile(0.75)
    q25_cv = d["price_cv_ts_d"].quantile(0.25)
    d["SIG_HIGH_DISAGR"]    = (d["price_cv_ts_d"] > q75_cv).astype(int)
    d["SIG_LOW_DISAGR"]     = (d["price_cv_ts_d"] <= q25_cv).astype(int)

    # Entropy
    q75_ent = d["dir_entropy_d"].quantile(0.75)
    d["SIG_HIGH_ENTROPY"]   = (d["dir_entropy_d"] > q75_ent).astype(int)

    # Coverage
    d["SIG_MANY_SOURCES"]   = (d["n_sources_d"] >= 3).astype(int)
    d["SIG_MANY_ARTICLES"]  = (d["n_articles_d"] >= d["n_articles_d"].median()).astype(int)

    # Combo: high disagreement + many sources = more trustworthy signal
    d["SIG_CONFIDENT_DISAGR"] = (
        (d["SIG_HIGH_DISAGR"] == 1) & (d["SIG_MANY_SOURCES"] == 1)
    ).astype(int)

    return d


# ═══════════════════════════════════════════════════════════════════════════
# STEP 6 — Export
# ═══════════════════════════════════════════════════════════════════════════
def export(daily_dict: dict[str, pd.DataFrame]):
    print("\n" + "=" * 60)
    print("STEP 6 — Export")
    print("=" * 60)

    for target, df in daily_dict.items():
        path = OUTPUT_DIR / f"text_features_{target}.csv"
        df.to_csv(path, index=False)

        sig_cols  = [c for c in df.columns if c.startswith("SIG_")]
        lag_cols  = [c for c in df.columns if "lag" in c or "roll" in c]
        base_cols = [c for c in df.columns if c not in sig_cols + lag_cols + ["date"]]

        print(f"  ✅ {path.name}: {len(df):,} rows × {len(df.columns)} cols")
        print(f"     Base: {len(base_cols)} | Lag/Rolling: {len(lag_cols)} | SIG_: {len(sig_cols)}")


# ═══════════════════════════════════════════════════════════════════════════
# MAIN
# ═══════════════════════════════════════════════════════════════════════════
def main():
    print("╔══════════════════════════════════════════════════════════╗")
    print("║     02_text_features — Text Feature Extraction          ║")
    print("╚══════════════════════════════════════════════════════════╝\n")

    # Step 1: Load + relevance filter + merge CONTENT
    articles = load_and_filter()

    # Step 2: Per-article feature extraction
    articles = extract_per_article(articles)

    # Step 3: Daily aggregation per target
    daily_dict = daily_aggregate(articles)

    # Step 4 & 5: Lag/rolling + discretize, per target
    print("\n" + "=" * 60)
    print("STEP 4+5 — Lag/Rolling + Discretize")
    print("=" * 60)

    for target in daily_dict:
        df = daily_dict[target]
        df = add_lag_rolling(df)
        df = discretize(df)
        daily_dict[target] = df

        sig_cols = [c for c in df.columns if c.startswith("SIG_")]
        print(f"\n  [{target}] SIG_ signal rates:")
        for col in sig_cols:
            print(f"    {col:<28}: {df[col].mean():.1%}")

    # Step 6: Export
    export(daily_dict)

    print("\n✅ Pipeline hoàn thành.")


if __name__ == "__main__":
    main()
