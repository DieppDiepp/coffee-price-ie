# Hướng dẫn Scraper — pipeline/02_scraper

## Nhiệm vụ

Nhận danh sách URL → tải HTML → lưu vào file JSONL theo tháng.

---

## Input

Đọc URL từ các file trong `data/01_discovered/*.jsonl`.

Mỗi dòng trong file discovered có dạng:

```json
{
  "date": "2024-03-05",
  "query": "giá cà phê hôm nay 5/3/2024",
  "results": [
    { "rank": 1, "url": "https://laodong.vn/...", "domain": "laodong.vn", "title": "..." },
    { "rank": 2, "url": "https://giacaphe.com/...", "domain": "giacaphe.com", "title": "..." }
  ]
}
```

Lấy `url` và `date` từ mỗi result — đây là 2 field quan trọng nhất.

---

## Output

Ghi vào `data/02_raw_articles/{year}-{month}.jsonl`.

Mỗi dòng là một JSON object — xem file mẫu `2026-03.jsonl`.

**Các field bắt buộc:**

| Field | Lấy từ đâu |
|---|---|
| `url` | Từ discovered record |
| `domain` | Extract từ URL |
| `date_ref` | Field `date` từ discovered record — **không tự parse từ URL** |
| `collected_at` | Thời điểm scrape, format ISO 8601 timezone +07:00 |
| `title` | Lấy từ thẻ `<title>` của HTML |
| `raw_html` | Full HTML — không trim, không xử lý gì thêm |
| `status` | Xem bảng bên dưới |
| `error` | null nếu success, message lỗi nếu failed |

**Các giá trị `status`:**

| Giá trị | Ý nghĩa |
|---|---|
| `success` | Lấy được HTML |
| `failed_404` | Bài đã bị xóa |
| `failed_blocked` | Site trả về 403 hoặc captcha |
| `failed_timeout` | Request timeout |
| `failed_other` | Lỗi khác |

---

## Quy tắc quan trọng

**1. Mọi URL đều phải có record** — kể cả URL failed. Không được bỏ qua.

Lý do: cần biết URL nào đã xử lý rồi để không retry lại.

**2. Không scrape URL trùng.**

Trước khi scrape, kiểm tra URL đó đã có trong output file chưa. Nếu có thì bỏ qua.

**3. Không chỉnh sửa raw_html.**

Parser ở bước sau sẽ xử lý — scraper chỉ cần lấy đúng và đủ.

**4. Append vào file, không overwrite.**

File `2024-03.jsonl` có thể đang có data từ lần chạy trước — chỉ append thêm dòng mới.

---

## Gợi ý kỹ thuật

- Tool: repo open source bạn đang dùng, hoặc `requests` + `BeautifulSoup` cho site đơn giản.
- Delay giữa các request: 1-2 giây để tránh bị block.
- Nếu site trả về 429 (rate limit): tăng delay lên 10 giây rồi retry 1 lần.
- Chạy thử 20-30 URL trước khi chạy full để kiểm tra output đúng format chưa.

---

## Kiểm tra output

Sau khi chạy xong một batch, kiểm tra nhanh:

```bash
# Đếm số dòng
wc -l data/02_raw_articles/2024-03.jsonl

# Xem 2 dòng đầu
head -2 data/02_raw_articles/2024-03.jsonl | python -m json.tool

# Đếm theo status
cat data/02_raw_articles/2024-03.jsonl | python -c "
import sys, json
from collections import Counter
c = Counter(json.loads(l)['status'] for l in sys.stdin)
print(c)
"
```

Kết quả mong đợi: `success` chiếm > 70%, `failed_blocked` < 20%.
