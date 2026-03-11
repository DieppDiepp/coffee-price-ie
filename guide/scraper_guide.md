# Hướng dẫn Scraper - `pipeline/02_scraper`

## Mục tiêu

Đọc URL từ file discovered JSONL, tải HTML nguyên bản, và ghi ra `data/02_raw_articles/{year}-{month}.jsonl`.

Stage này chỉ làm nhiệm vụ thu thập raw article + metadata nhẹ. Không làm sạch HTML và không bóc main text.

## Cách chạy

```bash
python -m pip install -r requirements.txt
python -m playwright install chromium
python pipeline/02_scraper/main.py --input ..\demo.jsonl --resume
```

Nếu muốn chạy theo pipeline mặc định:

```bash
python pipeline/02_scraper/main.py --resume
```

## Input

Đầu vào là một hoặc nhiều file JSONL có cấu trúc:

```json
{
  "date": "2026-03-05",
  "query": "giá cà phê ngày 5 tháng 3 năm 2026",
  "results": [
    {
      "rank": 1,
      "url": "https://laodong.vn/...",
      "domain": "laodong.vn",
      "title": "..."
    }
  ]
}
```

Scraper sẽ flatten từng `result` thành một occurrence độc lập, nhưng vẫn giữ `date_ref` gốc.

## Output

Mỗi dòng trong `data/02_raw_articles/{year}-{month}.jsonl` là một object:

```json
{
  "url": "https://...",
  "domain": "laodong.vn",
  "date_ref": "2026-03-05",
  "collected_at": "2026-03-11T21:00:00+07:00",
  "title": "...",
  "raw_html": "<html>...</html>",
  "status": "success",
  "error": null,
  "final_url": "https://...",
  "source_id": "laodong",
  "published_at": "2026-03-05T06:30:00+07:00",
  "published_at_raw": "2026-03-05T06:30:00",
  "published_at_source": "jsonld",
  "published_at_confidence": "high",
  "published_at_alignment": "same_day",
  "published_at_alignment_days": 0,
  "http_status": 200,
  "content_type": "text/html; charset=utf-8",
  "fetch_method": "http",
  "discovery_rank": 1
}
```

## Quy tắc chính

1. Mỗi cặp `(url, date_ref)` phải có đúng một record output.
2. Nếu cùng URL xuất hiện ở nhiều ngày khác nhau, vẫn ghi nhiều record để giữ provenance.
3. Resume chỉ skip theo `(url, date_ref)`, không skip theo URL đơn lẻ.
4. `raw_html` phải là HTML nguyên bản lấy được từ site.
5. Nếu HTTP bị block hoặc HTML bất thường, scraper sẽ fallback sang browser.

## Mismatch Guard & Ambiguous Date Parsing

- Hệ thống thu thập tự động đánh giá mức độ tương thích giữa ngày đăng bài thực tế (`published_at`) và ngày truy vấn mục tiêu (`date_ref`).
- **Alignment Tags**:
  - `same_day`: Lệch 0 ngày.
  - `adjacent`: Lệch 1 ngày.
  - `mismatch`: Lệch > 1 ngày (dùng để chặn bài cũ do bộ máy tìm kiếm nhầm lẫn).
  - `unknown`: Không parse được ngày.
- **Ambiguous Date Parsing**: Trình trích xuất `published_at` không "ép" ngày khớp `date_ref`. Chuỗi ngày mơ hồ (ví dụ: `03/01/2026`) được dịch nghiêm ngặt theo quy tắc ngôn ngữ (`prefer_dayfirst`) đã cấu hình ở `sources.json`. Qua đó giữ được tính nguyên bản cho bài báo tiếng Việt và tránh việc ẩn lấp các bài báo `mismatch`.
- **JSON-LD**: Dữ liệu timestamp trong block `<script type="application/ld+json">` được ưu tiên cao nhất, rồi mới tới `<time>`, và thẻ `<meta>`.

## Hybrid strategy

- HTTP-first bằng Scrapling cho đa số domain báo chí.
- Browser fallback bằng Crawl4AI khi:
  - HTTP trả `403`, `429`, `503`
  - timeout
  - body quá ngắn (`< 1024` bytes)
  - có marker như `captcha`, `cloudflare`, `access denied`, `enable javascript`
- `giacaphe.com` được cấu hình browser-first trong `config/sources.json`.

## Kiểm tra nhanh

```bash
pytest -q
python pipeline/02_scraper/main.py --input ..\demo.jsonl --limit 30 --resume
```

Sau khi chạy, kiểm tra:

```bash
python -c "from pathlib import Path; print(Path('data/02_raw_articles/2026-03.jsonl').exists())"
python -c "import json, pathlib; p=pathlib.Path('data/02_raw_articles/2026-03.jsonl'); print(sum(1 for _ in p.open(encoding='utf-8')))"
```
