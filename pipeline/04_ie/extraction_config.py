"""
extraction_config.py — Paths, constants, thresholds.
"""
from pathlib import Path
import pandas as pd

# ── Paths ──
PROJECT_ROOT = Path(__file__).resolve().parents[2]
DISCOVER_CSV = PROJECT_ROOT / "data" / "01_discovered" / "Discoverlinks.csv"
ARTICLES_CSV = PROJECT_ROOT / "data" / "03_articles" / "coffee_articles.csv"
CACHE_DIR    = PROJECT_ROOT / "pipeline" / "04_ie" / "cache"
CACHE_FILE   = CACHE_DIR / "llm_extracted.csv"
OUTPUT_FILE  = PROJECT_ROOT / "data" / "04_features" / "llm_extracted.csv"

CACHE_DIR.mkdir(parents=True, exist_ok=True)

# ── Date range ──
DATE_START = pd.Timestamp("2023-03-11")
DATE_END   = pd.Timestamp("2026-03-11")

# ── LLM defaults ──
DEFAULT_MAX_CHARS  = 1500
MAX_TOKENS_OUT     = 300   # JSON output ~60 tokens; 300 is safe margin without reasoning overhead
SLEEP_BETWEEN      = 0.5
SAVE_EVERY         = 10

# ── Price validation ──
PRICE_MIN = 30_000
PRICE_MAX = 250_000

# ── Provider presets ──
# Dùng --provider deepseek hoặc --provider openai
PROVIDERS = {
    "openai": {
        "base_url": None,  # default OpenAI
        "model": "gpt-4o-mini",
        "env_key": "OPENAI_API_KEY",
    },
    "deepseek": {
        "base_url": "https://api.deepseek.com",
        "model": "deepseek-v4-flash",
        "env_key": "DEEPSEEK_API_KEY",
    },
}
