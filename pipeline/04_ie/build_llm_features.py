"""
build_llm_features.py — Gom dữ liệu LLM-extracted theo ngày,
tạo file features tương tự text_features_*.csv cho model ML.

Usage:
  python pipeline/04_ie/build_llm_features.py
"""
import sys
from pathlib import Path

import pandas as pd
import numpy as np

PROJECT_ROOT = Path(__file__).resolve().parents[2]
LLM_CSV = PROJECT_ROOT / "data" / "04_features" / "llm_extracted.csv"
DISC_CSV = PROJECT_ROOT / "data" / "01_discovered" / "Discoverlinks.csv"
OUTPUT_DIR = PROJECT_ROOT / "data" / "04_features"

DATE_START = pd.Timestamp("2023-03-11")
DATE_END = pd.Timestamp("2026-03-11")
PRICE_MIN, PRICE_MAX = 30_000, 250_000


def load_and_join():
    df = pd.read_csv(LLM_CSV)
    dl = pd.read_csv(DISC_CSV)
    dl_meta = dl.drop_duplicates(subset=["URL_HASH"], keep="first")[
        ["URL_HASH", "TARGET", "PUBLISHED_DATE", "DOMAIN"]
    ].copy()
    dl_meta["PUBLISHED_DATE"] = pd.to_datetime(dl_meta["PUBLISHED_DATE"], errors="coerce")

    merged = df.merge(dl_meta, left_on="url_hash", right_on="URL_HASH", how="left")
    merged["content_date"] = pd.to_datetime(merged["content_date"], errors="coerce")
    merged["date"] = merged["content_date"].fillna(merged["PUBLISHED_DATE"])
    merged["price_vnd"] = pd.to_numeric(merged["price_vnd"], errors="coerce")
    merged["price_change"] = pd.to_numeric(merged["price_change"], errors="coerce")

    valid_price = merged["price_vnd"].between(PRICE_MIN, PRICE_MAX) | merged["price_vnd"].isna()
    merged.loc[~valid_price, "price_vnd"] = np.nan

    merged = merged.dropna(subset=["date"])
    merged = merged[(merged["date"] >= DATE_START) & (merged["date"] <= DATE_END)]
    merged["d"] = merged["date"].dt.normalize()

    print(f"  Loaded: {len(merged):,} rows, date range {merged['d'].min().date()} → {merged['d'].max().date()}")
    return merged


def build_daily(group):
    all_dates = pd.date_range(DATE_START, DATE_END, freq="D")

    coffee = group[group["is_coffee_price"] == True]

    records = []
    for d in all_dates:
        day_all = group[group["d"] == d]
        day_cof = coffee[coffee["d"] == d]

        n_articles = len(day_all)
        n_coffee = len(day_cof)
        n_sources = day_all["DOMAIN"].nunique() if n_articles > 0 else 0

        if n_coffee > 0:
            dirs = day_cof["direction"].value_counts()
            n_up = dirs.get("UP", 0)
            n_down = dirs.get("DOWN", 0)
            n_stable = dirs.get("STABLE", 0)
            n_mixed = dirs.get("MIXED", 0)

            pct_up = n_up / n_coffee
            pct_down = n_down / n_coffee
            pct_stable = n_stable / n_coffee
            pct_mixed = n_mixed / n_coffee

            dir_score = (n_up - n_down) / n_coffee

            dir_counts = np.array([n_up, n_down, n_stable, n_mixed,
                                   n_coffee - n_up - n_down - n_stable - n_mixed])
            dir_counts = dir_counts[dir_counts > 0]
            probs = dir_counts / dir_counts.sum()
            dir_entropy = -np.sum(probs * np.log2(probs)) if len(probs) > 1 else 0.0

            p = day_cof["price_vnd"].dropna()
            price_median = p.median() if len(p) > 0 else np.nan
            price_mean = p.mean() if len(p) > 0 else np.nan
            price_cv = p.std() / p.mean() if len(p) > 1 and p.mean() > 0 else 0.0
            pct_has_price = len(p) / n_coffee

            pc = day_cof["price_change"].dropna()
            price_change_median = pc.median() if len(pc) > 0 else np.nan

            cert = day_cof["certainty"].dropna()
            certainty_mean = cert.mean() if len(cert) > 0 else np.nan
            pct_high_cert = (cert <= 2).mean() if len(cert) > 0 else 0.0
        else:
            pct_up = pct_down = pct_stable = pct_mixed = 0.0
            dir_score = 0.0
            dir_entropy = 0.0
            price_median = price_mean = np.nan
            price_cv = 0.0
            pct_has_price = 0.0
            price_change_median = np.nan
            certainty_mean = np.nan
            pct_high_cert = 0.0

        records.append({
            "date": d.date(),
            "n_articles": n_articles,
            "n_coffee": n_coffee,
            "n_sources": n_sources,
            "pct_up": pct_up,
            "pct_down": pct_down,
            "pct_stable": pct_stable,
            "pct_mixed": pct_mixed,
            "dir_score": dir_score,
            "dir_entropy": dir_entropy,
            "price_median": price_median,
            "price_mean": price_mean,
            "price_cv": price_cv,
            "pct_has_price": pct_has_price,
            "price_change_median": price_change_median,
            "certainty_mean": certainty_mean,
            "pct_high_cert": pct_high_cert,
        })

    return pd.DataFrame(records)


def add_lags_and_rolling(feat):
    lag_cols = ["dir_score", "pct_up", "pct_down", "dir_entropy",
                "price_cv", "n_articles", "n_sources", "n_coffee",
                "price_change_median", "certainty_mean"]

    for col in lag_cols:
        if col not in feat.columns:
            continue
        for lag in [1, 2, 3]:
            feat[f"{col}_lag{lag}"] = feat[col].shift(lag)

    roll_cols = ["dir_score", "price_cv", "n_articles", "n_coffee",
                 "price_change_median", "certainty_mean"]
    for col in roll_cols:
        if col not in feat.columns:
            continue
        feat[f"{col}_roll3"] = feat[col].rolling(3, min_periods=1).mean()

    return feat


def add_signals(feat):
    feat["SIG_MAJORITY_UP"] = (feat["pct_up"] > 0.5).astype(int)
    feat["SIG_MAJORITY_DOWN"] = (feat["pct_down"] > 0.5).astype(int)
    feat["SIG_BULLISH"] = ((feat["dir_score"] > 0.2) & (feat["n_coffee"] >= 2)).astype(int)
    feat["SIG_BEARISH"] = ((feat["dir_score"] < -0.2) & (feat["n_coffee"] >= 2)).astype(int)
    feat["SIG_NEUTRAL"] = (feat["dir_score"].abs() <= 0.1).astype(int)
    feat["SIG_SPLIT_SIGNAL"] = (
        (feat["pct_up"] > 0.3) & (feat["pct_down"] > 0.3)
    ).astype(int)
    feat["SIG_HIGH_ENTROPY"] = (feat["dir_entropy"] > 1.0).astype(int)
    feat["SIG_MANY_ARTICLES"] = (feat["n_articles"] >= 8).astype(int)
    feat["SIG_MANY_SOURCES"] = (feat["n_sources"] >= 5).astype(int)
    feat["SIG_HIGH_CONFIDENCE"] = (feat["pct_high_cert"] > 0.7).astype(int)
    return feat


def main():
    print("=" * 55)
    print("  Build LLM Daily Features")
    print("=" * 55 + "\n")

    merged = load_and_join()

    for target in ["arabica", "robusta"]:
        print(f"\n--- {target} ---")
        subset = merged[merged["TARGET"] == target]
        print(f"  Articles: {len(subset):,}")

        feat = build_daily(subset)
        feat = add_lags_and_rolling(feat)
        feat = add_signals(feat)

        out_path = OUTPUT_DIR / f"llm_features_{target}.csv"
        feat.to_csv(out_path, index=False)
        print(f"  Columns: {len(feat.columns)}")
        print(f"  Days: {len(feat):,}")
        print(f"  Days with coffee articles: {(feat['n_coffee'] > 0).sum():,}")
        print(f"  Exported: {out_path}")

    # Combined (cả hai targets gộp)
    print(f"\n--- combined ---")
    feat_all = build_daily(merged)
    feat_all = add_lags_and_rolling(feat_all)
    feat_all = add_signals(feat_all)

    out_all = OUTPUT_DIR / f"llm_features_combined.csv"
    feat_all.to_csv(out_all, index=False)
    print(f"  Columns: {len(feat_all.columns)}")
    print(f"  Days: {len(feat_all):,}")
    print(f"  Days with coffee articles: {(feat_all['n_coffee'] > 0).sum():,}")
    print(f"  Exported: {out_all}")

    print("\nDone.")


if __name__ == "__main__":
    main()
