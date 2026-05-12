"""
03_eda_text_features.py
=======================
EDA toàn diện cho text_features_{robusta,arabica}.csv
Mục tiêu: tạo hình ảnh + số liệu để:
  1. Đánh giá data quality (coverage, consistency)
  2. Justify đưa text features vào model dự đoán
  3. Cung cấp figures cho slide báo cáo

Output figures: pipeline/05_disagreement/output/eda/*.png

Usage:
  python pipeline/05_disagreement/03_eda_text_features.py
"""

import os
import warnings
from pathlib import Path

import matplotlib
matplotlib.use("Agg")

import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import numpy as np
import pandas as pd
import seaborn as sns
from scipy import stats

warnings.filterwarnings("ignore")

# ── Paths ─────────────────────────────────────────────────────────────────
PROJECT_ROOT = Path(__file__).resolve().parents[2]
FEATURES_DIR = PROJECT_ROOT / "data" / "04_features"
PRICE_DIR    = PROJECT_ROOT / "data" / "06_ground_truth" / "Investing"
OUTPUT_DIR   = Path(__file__).resolve().parent / "output" / "eda"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# ── Style ─────────────────────────────────────────────────────────────────
plt.rcParams.update({
    "figure.dpi": 150,
    "figure.facecolor": "white",
    "axes.facecolor": "white",
    "font.size": 10,
    "axes.titlesize": 12,
    "axes.titleweight": "bold",
    "axes.grid": True,
    "grid.alpha": 0.3,
})
C_BULL  = "#27AE60"
C_BEAR  = "#E74C3C"
C_NEUT  = "#7F8C8D"
C_PRICE = "#2C3E50"
C_CV    = "#E07B39"
C_ART   = "#3498DB"


# ═══════════════════════════════════════════════════════════════════════════
# DATA LOADING
# ═══════════════════════════════════════════════════════════════════════════
def load_all():
    """Load text features + price data, merge, compute next-day return."""
    data = {}
    for target in ["robusta", "arabica"]:
        tf = pd.read_csv(FEATURES_DIR / f"text_features_{target}.csv")
        tf["date"] = pd.to_datetime(tf["date"])

        pf = pd.read_csv(PRICE_DIR / f"{target}_clean.csv")
        pf["date"] = pd.to_datetime(pf["date"])

        # Next-day return (%) — target variable
        pf["next_day_ret"] = pf["Gia_Viet_Nam"].pct_change().shift(-1) * 100
        # Next-day direction
        pf["next_day_dir"] = np.where(pf["next_day_ret"] > 0, 1, 0)

        merged = pf.merge(tf, on="date", how="inner")
        data[target] = {
            "text": tf,
            "price": pf,
            "merged": merged,
        }
        print(f"  {target}: text={len(tf)}, price={len(pf)}, merged={len(merged)}")

    return data


# ═══════════════════════════════════════════════════════════════════════════
# SECTION 1 — Coverage theo thời gian
# ═══════════════════════════════════════════════════════════════════════════
def plot_coverage(data: dict):
    """Số bài và số nguồn báo theo ngày — đánh giá data đủ dùng không."""
    fig, axes = plt.subplots(2, 2, figsize=(16, 8))

    for col_idx, target in enumerate(["robusta", "arabica"]):
        tf = data[target]["text"]

        # n_articles_d
        ax = axes[0][col_idx]
        ax.bar(tf["date"], tf["n_articles_d"], width=1, color=C_ART, alpha=0.6, linewidth=0)
        med = tf["n_articles_d"].median()
        ax.axhline(med, color="red", linestyle="--", linewidth=1, label=f"Median={med:.0f}")
        ax.set_title(f"{target.capitalize()} — Số bài/ngày")
        ax.set_ylabel("n_articles_d")
        ax.legend(fontsize=9)
        ax.xaxis.set_major_formatter(mdates.DateFormatter("%Y-%m"))
        ax.xaxis.set_major_locator(mdates.MonthLocator(interval=4))
        plt.setp(ax.xaxis.get_majorticklabels(), rotation=45, ha="right")

        # n_sources_d
        ax = axes[1][col_idx]
        ax.bar(tf["date"], tf["n_sources_d"], width=1, color="#8E44AD", alpha=0.6, linewidth=0)
        med_s = tf["n_sources_d"].median()
        ax.axhline(med_s, color="red", linestyle="--", linewidth=1, label=f"Median={med_s:.0f}")
        ax.set_title(f"{target.capitalize()} — Số nguồn/ngày")
        ax.set_ylabel("n_sources_d")
        ax.legend(fontsize=9)
        ax.xaxis.set_major_formatter(mdates.DateFormatter("%Y-%m"))
        ax.xaxis.set_major_locator(mdates.MonthLocator(interval=4))
        plt.setp(ax.xaxis.get_majorticklabels(), rotation=45, ha="right")

    fig.suptitle("Section 1 — Coverage: Mật độ thu thập bài báo", fontsize=14, fontweight="bold", y=1.01)
    plt.tight_layout()
    path = OUTPUT_DIR / "01_coverage_timeline.png"
    fig.savefig(path, bbox_inches="tight")
    plt.close(fig)
    print(f"  ✅ {path.name}")

    # Print stats
    for target in ["robusta", "arabica"]:
        tf = data[target]["text"]
        print(f"  [{target}] articles/day: mean={tf['n_articles_d'].mean():.1f}, "
              f"median={tf['n_articles_d'].median():.0f}, "
              f"min={tf['n_articles_d'].min():.0f}, max={tf['n_articles_d'].max():.0f}")


# ═══════════════════════════════════════════════════════════════════════════
# SECTION 2 — Sentiment timeline vs giá thực
# ═══════════════════════════════════════════════════════════════════════════
def plot_sentiment_vs_price(data: dict):
    """
    Overlay dir_score_ts_d lên Gia_Viet_Nam.
    Câu hỏi: Báo chí có phản ánh đúng xu hướng giá không?
    """
    fig, axes = plt.subplots(2, 1, figsize=(16, 10))

    for ax, target in zip(axes, ["robusta", "arabica"]):
        m = data[target]["merged"].sort_values("date")

        # Giá (trục trái)
        ax.plot(m["date"], m["Gia_Viet_Nam"], color=C_PRICE, linewidth=1.2,
                label="Giá VND/kg", zorder=3)
        ax.set_ylabel("Giá VND/kg", color=C_PRICE)
        ax.tick_params(axis="y", labelcolor=C_PRICE)

        # Dir score (trục phải)
        ax2 = ax.twinx()
        # Smoothed dir_score (rolling 7 ngày) cho dễ đọc
        dir_smooth = m["dir_score_ts_d"].rolling(7, min_periods=1).mean()
        ax2.fill_between(m["date"], dir_smooth, 0,
                         where=dir_smooth > 0, alpha=0.25, color=C_BULL,
                         label="Bullish", interpolate=True)
        ax2.fill_between(m["date"], dir_smooth, 0,
                         where=dir_smooth < 0, alpha=0.25, color=C_BEAR,
                         label="Bearish", interpolate=True)
        ax2.plot(m["date"], dir_smooth, color="#7F8C8D", linewidth=0.6, alpha=0.5)
        ax2.axhline(0, color="gray", linewidth=0.5, linestyle="--")
        ax2.set_ylabel("dir_score_ts_d (7-day MA)", color=C_NEUT)
        ax2.set_ylim(-1.2, 1.2)
        ax2.tick_params(axis="y", labelcolor=C_NEUT)

        ax.set_title(f"{target.capitalize()} — Media Sentiment vs Giá thực")
        ax.xaxis.set_major_formatter(mdates.DateFormatter("%Y-%m"))
        ax.xaxis.set_major_locator(mdates.MonthLocator(interval=3))
        plt.setp(ax.xaxis.get_majorticklabels(), rotation=45, ha="right")

        # Combined legend
        h1, l1 = ax.get_legend_handles_labels()
        h2, l2 = ax2.get_legend_handles_labels()
        ax.legend(h1 + h2, l1 + l2, loc="upper left", fontsize=9,
                  framealpha=0.9)

    fig.suptitle("Section 2 — Sentiment (TITLE+SNIPPET) vs Giá thực",
                 fontsize=14, fontweight="bold", y=1.01)
    plt.tight_layout()
    path = OUTPUT_DIR / "02_sentiment_vs_price.png"
    fig.savefig(path, bbox_inches="tight")
    plt.close(fig)
    print(f"  ✅ {path.name}")


# ═══════════════════════════════════════════════════════════════════════════
# SECTION 3 — Cross-check: dir_score_ts vs dir_score_body
# ═══════════════════════════════════════════════════════════════════════════
def plot_crosscheck(data: dict):
    """
    Scatter: TITLE+SNIPPET sentiment vs CONTENT sentiment.
    Nếu correlate cao → TITLE+SNIPPET đáng tin (không bịa).
    """
    fig, axes = plt.subplots(1, 2, figsize=(12, 5))

    for ax, target in zip(axes, ["robusta", "arabica"]):
        tf = data[target]["text"].dropna(subset=["dir_score_body_d"])
        x = tf["dir_score_ts_d"]
        y = tf["dir_score_body_d"]

        ax.scatter(x, y, s=8, alpha=0.3, color=C_ART, edgecolors="none")

        # Regression line
        slope, intercept, r, p, _ = stats.linregress(x, y)
        x_line = np.linspace(x.min(), x.max(), 100)
        ax.plot(x_line, slope * x_line + intercept, color=C_BEAR, linewidth=2,
                label=f"r = {r:.3f} (p={p:.1e})")

        ax.axhline(0, color="gray", linewidth=0.5, linestyle="--")
        ax.axvline(0, color="gray", linewidth=0.5, linestyle="--")
        ax.set_xlabel("dir_score_ts_d (TITLE+SNIPPET)")
        ax.set_ylabel("dir_score_body_d (CONTENT)")
        ax.set_title(f"{target.capitalize()}")
        ax.legend(fontsize=10, loc="upper left")

    fig.suptitle("Section 3 — Cross-check: TITLE+SNIPPET vs CONTENT sentiment\n"
                 "(Pearson r cao = hai nguồn nhất quán)",
                 fontsize=13, fontweight="bold")
    plt.tight_layout()
    path = OUTPUT_DIR / "03_crosscheck_ts_vs_body.png"
    fig.savefig(path, bbox_inches="tight")
    plt.close(fig)
    print(f"  ✅ {path.name}")

    for target in ["robusta", "arabica"]:
        tf = data[target]["text"].dropna(subset=["dir_score_body_d"])
        r, p = stats.pearsonr(tf["dir_score_ts_d"], tf["dir_score_body_d"])
        print(f"  [{target}] Pearson r = {r:.4f}, p = {p:.2e}")


# ═══════════════════════════════════════════════════════════════════════════
# SECTION 4 — Disagreement (price_cv) vs Price Volatility
# ═══════════════════════════════════════════════════════════════════════════
def plot_disagreement_vs_volatility(data: dict):
    """
    Khi báo chí bất đồng về giá (price_cv_ts_d cao),
    giá thực có biến động mạnh hơn không?
    """
    fig, axes = plt.subplots(2, 2, figsize=(16, 10))

    for row_idx, target in enumerate(["robusta", "arabica"]):
        m = data[target]["merged"].sort_values("date").copy()

        # Price volatility = |daily return|
        m["abs_ret"] = m["Gia_Viet_Nam"].pct_change().abs() * 100

        # ── 4a. Timeline ──────────────────────────────────────────────
        ax = axes[row_idx][0]
        ax.plot(m["date"], m["price_cv_ts_d"].rolling(7, min_periods=1).mean(),
                color=C_CV, linewidth=1, label="price_cv (7d MA)")
        q75 = m["price_cv_ts_d"].quantile(0.75)
        ax.axhline(q75, color="red", linewidth=0.8, linestyle="--",
                   label=f"Q75 = {q75:.4f}")
        ax.set_title(f"{target.capitalize()} — Price Disagreement theo thời gian")
        ax.set_ylabel("price_cv_ts_d")
        ax.legend(fontsize=9)
        ax.xaxis.set_major_formatter(mdates.DateFormatter("%Y-%m"))
        ax.xaxis.set_major_locator(mdates.MonthLocator(interval=4))
        plt.setp(ax.xaxis.get_majorticklabels(), rotation=45, ha="right")

        # ── 4b. Scatter: price_cv vs |return| ─────────────────────────
        ax = axes[row_idx][1]
        valid = m.dropna(subset=["price_cv_ts_d", "abs_ret"])
        valid = valid[valid["price_cv_ts_d"] > 0]  # bỏ ngày cv=0
        x = valid["price_cv_ts_d"]
        y = valid["abs_ret"]

        ax.scatter(x, y, s=10, alpha=0.3, color=C_CV, edgecolors="none")

        # Bin means
        try:
            bins = pd.qcut(x, q=5, duplicates="drop")
            bin_means = valid.groupby(bins)["abs_ret"].mean()
            bin_x = [iv.mid for iv in bin_means.index]
            ax.plot(bin_x, bin_means.values, "ro-", linewidth=2, markersize=6,
                    label="Bin mean", zorder=5)
        except Exception:
            pass

        r, p = stats.spearmanr(x, y)
        ax.set_xlabel("price_cv_ts_d (disagreement)")
        ax.set_ylabel("|daily return| (%)")
        ax.set_title(f"{target.capitalize()} — Disagreement vs Volatility\n"
                     f"Spearman ρ = {r:.3f} (p={p:.2e})")
        ax.legend(fontsize=9)

    fig.suptitle("Section 4 — Khi báo chí bất đồng về giá, giá thực biến động thế nào?",
                 fontsize=13, fontweight="bold", y=1.01)
    plt.tight_layout()
    path = OUTPUT_DIR / "04_disagreement_vs_volatility.png"
    fig.savefig(path, bbox_inches="tight")
    plt.close(fig)
    print(f"  ✅ {path.name}")


# ═══════════════════════════════════════════════════════════════════════════
# SECTION 5 — Correlation matrix: text features vs next-day return
# ═══════════════════════════════════════════════════════════════════════════
def plot_correlation(data: dict):
    """
    Ranking feature nào correlate mạnh nhất với next-day return.
    Đây là evidence chính để quyết định đưa feature nào vào model.
    """
    base_features = [
        "dir_score_ts_d", "dir_score_body_d",
        "pct_tang_d", "pct_giam_d", "pct_on_dinh_d",
        "dir_entropy_d", "price_cv_ts_d",
        "price_median_ts_d", "pct_has_price_ts_d",
        "n_articles_d", "n_sources_d",
    ]
    lag_features = [f"{f}_lag1" for f in [
        "dir_score_ts_d", "dir_score_body_d",
        "pct_tang_d", "pct_giam_d",
        "dir_entropy_d", "price_cv_ts_d",
        "n_articles_d", "n_sources_d",
    ]]
    roll_features = ["dir_score_ts_d_roll3", "price_cv_ts_d_roll3", "n_articles_d_roll3"]

    all_feats = base_features + lag_features + roll_features

    fig, axes = plt.subplots(1, 2, figsize=(14, 10))

    for ax, target in zip(axes, ["robusta", "arabica"]):
        m = data[target]["merged"].dropna(subset=["next_day_ret"])
        feats_present = [f for f in all_feats if f in m.columns]
        corrs = m[feats_present + ["next_day_ret"]].corr()["next_day_ret"].drop("next_day_ret")
        corrs = corrs.dropna().sort_values()

        colors = [C_BULL if v > 0 else C_BEAR for v in corrs]
        corrs.plot(kind="barh", ax=ax, color=colors, edgecolor="white", linewidth=0.5)
        ax.axvline(0, color="gray", linewidth=1)
        ax.set_xlabel("Pearson correlation with next-day return")
        ax.set_title(f"{target.capitalize()}")

        # Mark significant ones
        for i, (feat, val) in enumerate(corrs.items()):
            if abs(val) > 0.05:
                ax.text(val + (0.002 if val > 0 else -0.002), i,
                        f"{val:.3f}", va="center", fontsize=7,
                        fontweight="bold", color="black")

    fig.suptitle("Section 5 — Tương quan text features → next-day return\n"
                 "(Features có |r| lớn hơn → ứng viên mạnh cho model)",
                 fontsize=13, fontweight="bold")
    plt.tight_layout()
    path = OUTPUT_DIR / "05_correlation_vs_return.png"
    fig.savefig(path, bbox_inches="tight")
    plt.close(fig)
    print(f"  ✅ {path.name}")

    # Print top features
    for target in ["robusta", "arabica"]:
        m = data[target]["merged"].dropna(subset=["next_day_ret"])
        feats_present = [f for f in all_feats if f in m.columns]
        corrs = m[feats_present + ["next_day_ret"]].corr()["next_day_ret"].drop("next_day_ret")
        corrs = corrs.dropna().reindex(corrs.abs().sort_values(ascending=False).index)
        print(f"\n  [{target}] Top 10 correlations with next-day return:")
        for feat, val in corrs.head(10).items():
            print(f"    {feat:<30}: r = {val:+.4f}")


# ═══════════════════════════════════════════════════════════════════════════
# SECTION 6 — Conditional returns theo SIG_ signals
# ═══════════════════════════════════════════════════════════════════════════
def plot_conditional_returns(data: dict):
    """
    Box plot: distribution of next-day return khi mỗi SIG_ = 1 vs = 0.
    Evidence trực tiếp nhất: signal này có predictive power không?
    """
    sig_cols = [
        "SIG_MAJORITY_TANG", "SIG_MAJORITY_GIAM",
        "SIG_BULLISH", "SIG_BEARISH", "SIG_NEUTRAL",
        "SIG_SPLIT_SIGNAL",
        "SIG_HIGH_DISAGR", "SIG_LOW_DISAGR",
        "SIG_HIGH_ENTROPY",
        "SIG_MANY_SOURCES", "SIG_MANY_ARTICLES",
        "SIG_CONFIDENT_DISAGR",
    ]

    fig, axes = plt.subplots(2, 1, figsize=(16, 12))

    for ax, target in zip(axes, ["robusta", "arabica"]):
        m = data[target]["merged"].dropna(subset=["next_day_ret"])

        records = []
        for sig in sig_cols:
            if sig not in m.columns:
                continue
            ret_1 = m.loc[m[sig] == 1, "next_day_ret"]
            ret_0 = m.loc[m[sig] == 0, "next_day_ret"]

            mean_1 = ret_1.mean()
            mean_0 = ret_0.mean()
            diff   = mean_1 - mean_0

            # t-test
            if len(ret_1) > 5 and len(ret_0) > 5:
                t_stat, p_val = stats.ttest_ind(ret_1, ret_0, equal_var=False)
            else:
                t_stat, p_val = 0, 1

            records.append({
                "signal": sig.replace("SIG_", ""),
                "mean_when_1": mean_1,
                "mean_when_0": mean_0,
                "diff": diff,
                "n_1": len(ret_1),
                "p_val": p_val,
            })

        rec_df = pd.DataFrame(records).sort_values("diff")

        colors = [C_BULL if d > 0 else C_BEAR for d in rec_df["diff"]]
        bars = ax.barh(rec_df["signal"], rec_df["diff"], color=colors, alpha=0.8,
                       edgecolor="white", linewidth=0.5)
        ax.axvline(0, color="gray", linewidth=1)
        ax.set_xlabel("Δ mean next-day return (%) : signal=1 vs signal=0")
        ax.set_title(f"{target.capitalize()} — Effect of each SIG_ on next-day return")

        # Annotate significance
        for i, (_, row) in enumerate(rec_df.iterrows()):
            star = "***" if row["p_val"] < 0.01 else "**" if row["p_val"] < 0.05 else "*" if row["p_val"] < 0.1 else ""
            text = f"{row['diff']:+.3f}% {star}  (n={int(row['n_1'])})"
            x_pos = row["diff"] + (0.005 if row["diff"] >= 0 else -0.005)
            ha = "left" if row["diff"] >= 0 else "right"
            ax.text(x_pos, i, text, va="center", ha=ha, fontsize=8)

    fig.suptitle("Section 6 — Conditional Returns: mỗi signal ảnh hưởng return ngày sau?\n"
                 "(* p<0.1  ** p<0.05  *** p<0.01)",
                 fontsize=13, fontweight="bold")
    plt.tight_layout()
    path = OUTPUT_DIR / "06_conditional_returns.png"
    fig.savefig(path, bbox_inches="tight")
    plt.close(fig)
    print(f"  ✅ {path.name}")


# ═══════════════════════════════════════════════════════════════════════════
# SECTION 7 — Lead-lag analysis: lag nào correlate mạnh nhất?
# ═══════════════════════════════════════════════════════════════════════════
def plot_leadlag(data: dict):
    """
    So sánh correlation của base vs lag1 vs lag2 vs lag3.
    Giúp chọn lag tối ưu cho model.
    """
    core_bases = [
        "dir_score_ts_d", "dir_score_body_d",
        "pct_tang_d", "pct_giam_d",
        "dir_entropy_d", "price_cv_ts_d",
        "n_articles_d", "n_sources_d",
    ]

    fig, axes = plt.subplots(1, 2, figsize=(14, 8))

    for ax, target in zip(axes, ["robusta", "arabica"]):
        m = data[target]["merged"].dropna(subset=["next_day_ret"])

        rows = []
        for base in core_bases:
            for lag_suffix in ["", "_lag1", "_lag2", "_lag3"]:
                col = base + lag_suffix
                if col in m.columns:
                    valid = m[[col, "next_day_ret"]].dropna()
                    if len(valid) > 10:
                        r, p = stats.pearsonr(valid[col], valid["next_day_ret"])
                        lag_label = lag_suffix.replace("_", "") if lag_suffix else "t"
                        rows.append({
                            "feature": base.replace("_d", ""),
                            "lag": lag_label,
                            "r": r,
                            "abs_r": abs(r),
                        })

        lag_df = pd.DataFrame(rows)
        pivot = lag_df.pivot(index="feature", columns="lag", values="r")
        # Reorder columns
        col_order = [c for c in ["t", "lag1", "lag2", "lag3"] if c in pivot.columns]
        pivot = pivot[col_order]
        # Sort by max |r| across lags
        pivot["max_abs"] = pivot.abs().max(axis=1)
        pivot = pivot.sort_values("max_abs", ascending=True).drop(columns="max_abs")

        cmap = sns.diverging_palette(10, 130, as_cmap=True)
        sns.heatmap(pivot, annot=True, fmt=".3f", cmap=cmap, center=0,
                    vmin=-0.1, vmax=0.1,
                    linewidths=0.5, ax=ax, cbar_kws={"shrink": 0.8})
        ax.set_title(f"{target.capitalize()}")
        ax.set_xlabel("Lag (t = same-day, lag1 = yesterday, ...)")
        ax.set_ylabel("")

    fig.suptitle("Section 7 — Lead-Lag: correlation với next-day return tại mỗi lag\n"
                 "(Chọn lag nào cho |r| lớn nhất → lag tối ưu cho model)",
                 fontsize=13, fontweight="bold")
    plt.tight_layout()
    path = OUTPUT_DIR / "07_leadlag_heatmap.png"
    fig.savefig(path, bbox_inches="tight")
    plt.close(fig)
    print(f"  ✅ {path.name}")


# ═══════════════════════════════════════════════════════════════════════════
# SUMMARY TABLE — Tổng hợp key metrics
# ═══════════════════════════════════════════════════════════════════════════
def print_summary(data: dict):
    """Print tổng hợp các con số quan trọng cho báo cáo."""
    print("\n" + "=" * 70)
    print("SUMMARY — Key findings cho báo cáo")
    print("=" * 70)

    for target in ["robusta", "arabica"]:
        m = data[target]["merged"].dropna(subset=["next_day_ret"])
        tf = data[target]["text"]

        print(f"\n{'─' * 50}")
        print(f"  {target.upper()}")
        print(f"{'─' * 50}")
        print(f"  Tổng ngày text features  : {len(tf):,}")
        print(f"  Ngày join được với price : {len(m):,}")
        print(f"  Coverage (articles/day)  : {tf['n_articles_d'].mean():.1f} ± {tf['n_articles_d'].std():.1f}")
        print(f"  Coverage (sources/day)   : {tf['n_sources_d'].mean():.1f} ± {tf['n_sources_d'].std():.1f}")

        # Best feature
        base_feats = [c for c in m.columns
                      if c.endswith("_d") and not c.startswith("SIG_")
                      and c != "next_day_ret" and c != "next_day_dir"]
        corrs = {}
        for f in base_feats:
            valid = m[[f, "next_day_ret"]].dropna()
            if len(valid) > 10:
                r, _ = stats.pearsonr(valid[f], valid["next_day_ret"])
                corrs[f] = r
        if corrs:
            best = max(corrs, key=lambda k: abs(corrs[k]))
            print(f"  Best base feature        : {best} (r={corrs[best]:+.4f})")

        # dir_score_ts cross-check
        tf_clean = tf.dropna(subset=["dir_score_body_d"])
        if len(tf_clean) > 10:
            r_cross, _ = stats.pearsonr(tf_clean["dir_score_ts_d"], tf_clean["dir_score_body_d"])
            print(f"  Cross-check (ts vs body) : r = {r_cross:.4f}")

        # SIG_ hit rates
        print(f"  SIG_BULLISH rate         : {m['SIG_BULLISH'].mean():.1%}")
        print(f"  SIG_BEARISH rate         : {m['SIG_BEARISH'].mean():.1%}")
        if "SIG_BULLISH" in m.columns:
            bull_ret = m.loc[m["SIG_BULLISH"] == 1, "next_day_ret"].mean()
            bear_ret = m.loc[m["SIG_BEARISH"] == 1, "next_day_ret"].mean()
            base_ret = m["next_day_ret"].mean()
            print(f"  Next-day return (all)    : {base_ret:+.4f}%")
            print(f"  Next-day return (BULL)   : {bull_ret:+.4f}%")
            print(f"  Next-day return (BEAR)   : {bear_ret:+.4f}%")


# ═══════════════════════════════════════════════════════════════════════════
# MAIN
# ═══════════════════════════════════════════════════════════════════════════
def main():
    print("╔══════════════════════════════════════════════════════════════╗")
    print("║   03_eda_text_features — EDA for text features             ║")
    print("╚══════════════════════════════════════════════════════════════╝\n")
    print(f"Output: {OUTPUT_DIR}\n")

    data = load_all()

    print("\n── Section 1: Coverage ──")
    plot_coverage(data)

    print("\n── Section 2: Sentiment vs Price ──")
    plot_sentiment_vs_price(data)

    print("\n── Section 3: Cross-check ts vs body ──")
    plot_crosscheck(data)

    print("\n── Section 4: Disagreement vs Volatility ──")
    plot_disagreement_vs_volatility(data)

    print("\n── Section 5: Correlation matrix ──")
    plot_correlation(data)

    print("\n── Section 6: Conditional returns ──")
    plot_conditional_returns(data)

    print("\n── Section 7: Lead-lag analysis ──")
    plot_leadlag(data)

    print_summary(data)

    print(f"\n✅ EDA hoàn thành. Tất cả figures lưu tại: {OUTPUT_DIR}")


if __name__ == "__main__":
    main()
