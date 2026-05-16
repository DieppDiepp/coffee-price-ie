# pipeline/04_ie/ — LLM Information Extraction

## Tổng quan

Pipeline dùng LLM (DeepSeek V4 Flash) để trích xuất thông tin giá cà phê có cấu trúc từ bài báo tiếng Việt. Output là JSON 6 trường cho mỗi bài, sau đó gom theo ngày thành file features cho model ML.

**Tại sao dùng LLM thay vì regex/rule-based?**
Pipeline trích xuất thủ công trước đó (regex trên TITLE+SNIPPET) cho kết quả không hiệu quả — miss nhiều case phức tạp, không phân biệt được giá thế giới vs nội địa, không trích được `content_date` chính xác. LLM đọc hiểu ngữ cảnh tốt hơn rất nhiều.

---

## Pipeline flow

```
coffee_articles.csv (9,553 bài, CONTENT đầy đủ)
        │
        ├── Join với DiscoverLinks.csv (lấy TITLE, SNIPPET, PUBLISHED_DATE, TARGET)
        ├── Date filter: 2023-03-11 → 2026-03-11
        ├── Relevance filter: TITLE hoặc SNIPPET chứa "cà phê"
        ├── Dedup: 1 row per URL_HASH
        │
        ▼
  Smart Truncation (content_cleaner.py)
        │  Tách paragraphs → loại noise (nav/footer/stock) → chấm điểm keyword → top paragraphs
        │  Max 1,500 chars/bài
        │
        ▼
  LLM Extraction (llm_client.py + prompts.py)
        │  DeepSeek V4 Flash, non-thinking mode
        │  System prompt tiếng Việt, JSON output mode
        │  → 6 trường có cấu trúc per bài
        │
        ▼
  Cache + Resume (pipeline/04_ie/cache/llm_extracted.csv)
        │  Auto-save mỗi 10 bài, retry lỗi tự động
        │
        ▼
  data/04_features/llm_extracted.csv (7,048 bài, 100% ok)
        │
        ▼
  Daily Aggregation (build_llm_features.py)
        │  Join url_hash → TARGET + PUBLISHED_DATE
        │  Group by date → base features → lags → rolling → signals
        │
        ▼
  llm_features_{arabica,robusta,combined}.csv (1,097 ngày × 63 cột)
```

---

## Chiến thuật LLM

### Model & cấu hình

| Setting | Giá trị | Lý do |
|---|---|---|
| **Model** | `deepseek-v4-flash` | Rẻ nhất trong các model mạnh, hỗ trợ JSON mode |
| **Thinking mode** | `disabled` | Thinking mode mặc định ăn hết output budget → JSON rỗng. Tắt thinking giảm completion tokens từ ~182 xuống ~56/bài |
| **max_tokens** | 300 | JSON output chỉ ~60 tokens; 300 là dư dả khi không có reasoning overhead |
| **temperature** | 0.0 | Deterministic, đảm bảo reproducibility |
| **response_format** | `json_object` | Bắt buộc output JSON hợp lệ |

### Vấn đề thinking mode (đã fix)

Ban đầu dùng thinking mode mặc định → 3/5 bài fail (JSON rỗng):
- `max_tokens` bao gồm CẢ reasoning + content tokens
- Reasoning dùng 147–860 chars, không còn token cho JSON
- Fix: `extra_body={"thinking": {"type": "disabled"}}`
- Kết quả: 5/5 success, completion ~56 tokens, cost giảm ~70%

### Smart Truncation

`content_cleaner.py` xử lý CONTENT trước khi gửi LLM:

1. Tách paragraphs (>20 ký tự)
2. Loại noise: nav menus, footer, stock tickers, weather, ads (regex)
3. Chấm điểm keyword:
   - +3: "giá cà phê", "đồng/kg", giá VND format
   - +2: "cà phê", "robusta", "arabica"
   - +1: "tăng", "giảm", "Đắk Lắk", "thị trường", etc.
4. Lấy top paragraphs cho đến 1,500 chars

### System Prompt

Prompt tiếng Việt, yêu cầu trích xuất 6 trường:

| Trường | Kiểu | Mô tả |
|---|---|---|
| `is_coffee_price` | bool | Bài có đề cập giá cà phê nội địa VN không |
| `direction` | enum | UP / DOWN / STABLE / MIXED / NONE |
| `price_vnd` | int \| null | Giá VND/kg, ưu tiên Đắk Lắk/Tây Nguyên |
| `price_change` | int \| null | Delta so với ngày trước (dương = tăng, âm = giảm) |
| `certainty` | 1–5 | 1 = giá thực tế, 5 = không có giá |
| `content_date` | date \| null | Ngày thực sự được đề cập trong bài |

Chi tiết prompt xem `prompts.py`.

---

## Kết quả extraction

### Tổng quan (7,048 bài)

| Metric | Giá trị |
|---|---|
| **Status** | 100% ok (0 lỗi) |
| **is_coffee_price = True** | 4,828 (68.5%) |
| **Valid prices** | 4,719 bài (range 31,900 – 250,000 VND/kg) |
| **Certainty 1–2** | 4,796 (68.0%) — giá thực tế hoặc mơ hồ |
| **Date mismatch > 2 ngày** | 360/4,717 (7.6%) |

### Direction distribution

| Direction | Count | % (tổng) | % (coffee only) |
|---|---|---|---|
| UP | 2,434 | 34.5% | 50.4% |
| NONE | 2,231 | 31.7% | — |
| DOWN | 1,581 | 22.4% | 32.7% |
| STABLE | 475 | 6.7% | 9.8% |
| MIXED | 327 | 4.6% | 6.8% |

### Cost & Performance

| Metric | Giá trị |
|---|---|
| **Avg tokens/bài** | prompt=2,166 + completion=56 = 2,222 |
| **Cache hit rate** | 95.7% |
| **Avg response time** | 0.87s/bài |
| **Total cost** | ~$0.24 (7,048 bài) |
| **Budget** | $2.00 → dư $1.76 |

---

## Output files

### llm_extracted.csv (raw, per-article)

Path: `data/04_features/llm_extracted.csv`

| Cột | Kiểu | Mô tả |
|---|---|---|
| `is_coffee_price` | bool | Bài liên quan giá cà phê VN |
| `direction` | str | UP / DOWN / STABLE / MIXED / NONE |
| `price_vnd` | float | Giá VND/kg (30k–250k), null nếu không có |
| `price_change` | float | Delta VND/kg, null nếu không có |
| `certainty` | int | 1 = giá thực tế → 5 = không có giá |
| `content_date` | str | YYYY-MM-DD, null nếu không xác định |
| `_status` | str | "ok" (tất cả) |
| `_tokens_used` | int | Total tokens consumed |
| `url_hash` | str | SHA256 hash, join key với DiscoverLinks |

### llm_features_{target}.csv (daily aggregated)

Path: `data/04_features/llm_features_{arabica,robusta,combined}.csv`

Generated by: `pipeline/04_ie/build_llm_features.py`

#### Base features (17 cột)

| Cột | Kiểu | Mô tả |
|---|---|---|
| `date` | date | Ngày (key join với price data) |
| `n_articles` | int | Tổng bài trong ngày |
| `n_coffee` | int | Bài có is_coffee_price=True |
| `n_sources` | int | Số domain khác nhau |
| `pct_up` | float [0,1] | Tỉ lệ bài direction=UP (trong coffee) |
| `pct_down` | float [0,1] | Tỉ lệ bài direction=DOWN |
| `pct_stable` | float [0,1] | Tỉ lệ bài direction=STABLE |
| `pct_mixed` | float [0,1] | Tỉ lệ bài direction=MIXED |
| `dir_score` | float [-1,1] | (n_UP - n_DOWN) / n_coffee |
| `dir_entropy` | float >= 0 | Shannon entropy phân phối direction |
| `price_median` | float | Median giá VND/kg trong ngày |
| `price_mean` | float | Mean giá VND/kg trong ngày |
| `price_cv` | float >= 0 | Coefficient of Variation giá (std/mean) |
| `pct_has_price` | float [0,1] | Tỉ lệ bài coffee có giá cụ thể |
| `price_change_median` | float | Median price_change trong ngày |
| `certainty_mean` | float [1,5] | Mean certainty (thấp = tin cậy hơn) |
| `pct_high_cert` | float [0,1] | Tỉ lệ bài certainty <= 2 |

#### Lag features (30 cột)

Format: `{base}_lag{N}` với N = 1, 2, 3

Lag cho 10 base features: `dir_score`, `pct_up`, `pct_down`, `dir_entropy`, `price_cv`, `n_articles`, `n_sources`, `n_coffee`, `price_change_median`, `certainty_mean`.

#### Rolling features (6 cột)

Format: `{base}_roll3` — rolling mean 3 ngày

Cho: `dir_score`, `price_cv`, `n_articles`, `n_coffee`, `price_change_median`, `certainty_mean`.

#### Signal flags (10 cột, binary 0/1)

| Cột | Logic | Ý nghĩa |
|---|---|---|
| `SIG_MAJORITY_UP` | pct_up > 0.50 | Đa số bài nói tăng |
| `SIG_MAJORITY_DOWN` | pct_down > 0.50 | Đa số bài nói giảm |
| `SIG_BULLISH` | dir_score > 0.2 AND n_coffee >= 2 | Sentiment tổng hợp tăng, đủ sample |
| `SIG_BEARISH` | dir_score < -0.2 AND n_coffee >= 2 | Sentiment tổng hợp giảm, đủ sample |
| `SIG_NEUTRAL` | \|dir_score\| <= 0.1 | Sentiment trung lập |
| `SIG_SPLIT_SIGNAL` | pct_up > 0.3 AND pct_down > 0.3 | Tín hiệu xung đột |
| `SIG_HIGH_ENTROPY` | dir_entropy > 1.0 | Bất đồng quan điểm cao |
| `SIG_MANY_ARTICLES` | n_articles >= 8 | Ngày nhiều tin |
| `SIG_MANY_SOURCES` | n_sources >= 5 | Nhiều nguồn báo |
| `SIG_HIGH_CONFIDENCE` | pct_high_cert > 0.7 | Đa số bài có giá tin cậy (certainty 1–2) |

---

## Cách sử dụng

### Join với price data

```python
import pandas as pd

price = pd.read_csv("data/06_ground_truth/Investing/arabica_clean.csv")
llm   = pd.read_csv("data/04_features/llm_features_arabica.csv")

price["date"] = pd.to_datetime(price["date"])
llm["date"]   = pd.to_datetime(llm["date"])

combined = price.merge(llm, on="date", how="left")
```

### So sánh với text features cũ

```python
text_old = pd.read_csv("data/04_features/text_features_arabica.csv")
text_llm = pd.read_csv("data/04_features/llm_features_arabica.csv")

# Join cả hai để so sánh hiệu quả
both = price.merge(text_old, on="date", how="left", suffixes=("", "_old"))
both = both.merge(text_llm, on="date", how="left", suffixes=("", "_llm"))
```

---

## So sánh: Text Features (cũ) vs LLM Features (mới)

| Khía cạnh | Text Features (regex) | LLM Features (DeepSeek) |
|---|---|---|
| **Phương pháp** | Regex trên TITLE+SNIPPET | LLM đọc hiểu CONTENT |
| **Direction** | Keyword matching (tăng/giảm) | Hiểu ngữ cảnh, phân biệt VN vs thế giới |
| **Giá** | Regex trên SNIPPET only | Extract từ CONTENT, ưu tiên Đắk Lắk |
| **Certainty** | Không có | 5 mức, phân biệt giá thực vs dự báo |
| **Content date** | Không có (dùng PUBLISHED_DATE) | Extract ngày thực sự trong bài |
| **Cost** | Free | ~$0.24 / 7,048 bài |
| **Coverage** | Tất cả bài | 68.5% bài được đánh giá liên quan giá |

---

## Files trong pipeline/04_ie/

| File | Mô tả |
|---|---|
| `extraction_config.py` | Paths, constants, provider config |
| `content_cleaner.py` | Smart truncation: loại noise, ưu tiên paragraphs liên quan |
| `prompts.py` | System prompt + user prompt template |
| `llm_client.py` | OpenAI-compatible client, extract_one() |
| `llm_extraction.py` | Main entry point — chạy extraction loop |
| `build_llm_features.py` | Gom theo ngày → daily features |
| `test_deepseek.py` | Test 5 bài, phân tích token & cache |
| `EDA_coffee_articles.ipynb` | EDA trên raw articles |
| `EDA_llm_extracted.ipynb` | EDA trên kết quả LLM extraction |

---

## Reproduce

```bash
# 1. Extract (cần DEEPSEEK_API_KEY trong .env)
cd pipeline/04_ie
python llm_extraction.py --provider deepseek

# 2. Build daily features
python build_llm_features.py

# Dry-run 20 bài trước:
python llm_extraction.py --provider deepseek --limit 20 --dry-run

# Resume (tự động skip bài đã ok):
python llm_extraction.py --provider deepseek
```
