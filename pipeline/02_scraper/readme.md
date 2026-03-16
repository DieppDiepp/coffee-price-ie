# Bước 2 — Thu thập Raw HTML (Web Crawling)

## Mục tiêu

Mục tiêu của **Bước 2** trong pipeline là thu thập và lưu trữ **raw HTML** của các bài báo được phát hiện ở **Bước 1 (Discovery)**.

Việc lưu raw HTML giúp:

* Lưu lại **toàn bộ nội dung gốc của trang web**
* Phục vụ cho các bước xử lý tiếp theo như:

  * parsing nội dung bài báo
  * trích xuất thông tin (information extraction)
  * phân tích dữ liệu (EDA)

Raw HTML được lưu **nguyên bản**, không chỉnh sửa.

---

# Dữ liệu đầu vào

Dữ liệu đầu vào của bước này là kết quả từ bước discovery:

```
data/01_discovered/2026-03.jsonl
```

File `.jsonl` chứa kết quả tìm kiếm từ nhiều query khác nhau.

Ví dụ một record:

```json
{
  "date": "2026-03-01",
  "query_id": "robusta_general",
  "query": "giá cà phê hôm nay",
  "results": [
    {
      "rank": 1,
      "url": "https://example.com/article"
    }
  ]
}
```

Mỗi record chứa danh sách các URL bài báo được tìm thấy.

---

# Quy trình crawl

Crawler thực hiện các bước sau:

## 1. Đọc dữ liệu discovery

* Đọc file `.jsonl`
* Trích xuất tất cả URL từ trường `results`.

---

## 2. Loại bỏ URL trùng lặp

Một bài báo có thể xuất hiện trong **nhiều query khác nhau**, vì vậy cần loại bỏ trùng lặp trước khi crawl.

Ví dụ:

```
query 1 → bài báo A  
query 2 → bài báo A  
query 3 → bài báo A
```

Crawler chỉ tải **một lần duy nhất** cho mỗi URL.


---

## 3. Tải HTML của trang web

Crawler sử dụng hai phương pháp:

### Requests

Phương pháp mặc định là gửi HTTP request trực tiếp bằng thư viện `requests`.

### Browser rendering

Trong các trường hợp:

* HTML quá ngắn
* trang yêu cầu JavaScript
* trang bị chặn bởi Cloudflare

crawler sẽ **fallback sang browser (Playwright)** để render trang trước khi lấy HTML.

---

## 4. Phát hiện Cloudflare

Một số trang báo sử dụng hệ thống bảo vệ của Cloudflare, có thể trả về trang trung gian với nội dung như:

```
Just a moment...
Checking your browser before accessing
```

Crawler sẽ:

* phát hiện trang Cloudflare
* chờ một khoảng thời gian
* thử tải lại trang

Điều này giúp tăng tỷ lệ crawl thành công.

---

## 5. Lưu raw HTML

HTML của mỗi trang được lưu **nguyên bản** dưới dạng file `.html`.

Tên file được tạo bằng **hash của URL** để tránh trùng lặp và lỗi ký tự.

Ví dụ:

```
a1b2c3.html
```

---

## 6. Lưu metadata

Mỗi file HTML đi kèm một file metadata chứa thông tin crawl.

Ví dụ:

```json
{
  "url": "https://example.com/article",
  "domain": "example.com",
  "date": "2026-03-01",
  "rank": 1,
  "crawl_time": "2026-03-15T16:00:00",
  "crawl_method": "requests",
  "html_size": 45231
}
```

---

# Cấu trúc thư mục output

Kết quả crawl được lưu tại:

```
data/02_rawhtml
```

Cấu trúc thư mục:

```
data
└── 02_rawhtml
    ├── 2026-03-01
    │   ├── a1b2c3.html
    │   ├── a1b2c3.json
    │   ├── d4e5f6.html
    │   └── d4e5f6.json
    │
    ├── 2026-03-02
    └── 2026-03-03
```

Mỗi bài báo sẽ tạo ra:

```
<hash>.html   → raw HTML
<hash>.json   → metadata
```

---

# Kết quả sơ bộ

Sau khi chạy crawler trên dataset discovery:

## Thống kê discovery

```
Total URLs: 430
Unique URLs: 148
Duplicate URLs: 282
Number of duplicated URLs: 97
```

Nguyên nhân:

Các query tìm kiếm khác nhau có thể trả về **cùng một bài báo**, dẫn đến nhiều URL trùng lặp.

---

# Kết quả crawl

```
Unique URLs: 148
HTML files: 143
Missing pages: 5
```

Tỷ lệ crawl thành công:

```
143 / 148 ≈ 97%
```

Đây là **tỷ lệ crawl rất cao** đối với web crawling.

Các URL không crawl được thường do:

* trang dynamic
* redirect
* timeout khi tải trang
* nội dung không phải bài báo

---

# Kiểm tra metadata

```
HTML files: 143
META files: 143
```

Mỗi file HTML đều có metadata tương ứng.

---

# Phân bố domain

Các nguồn dữ liệu phổ biến trong dataset:

```
baomoi.com                 96
trangtraiviet.danviet.vn   55
vov.vn                     50
laodong.vn                 45
nld.com.vn                 28
vietnambiz.vn              28
thoibaotaichinhvietnam.vn  25
giacaphe.com               10
cafef.vn                   7
```

Ngoài ra discovery còn chứa một số URL từ:

```
instagram.com
```

Tuy nhiên các URL này **không được crawl** vì không phải bài báo.

---

# Nhận xét

* Discovery dataset chứa **nhiều URL trùng lặp** do nhiều query khác nhau.
* Crawler đã loại bỏ trùng lặp và chỉ crawl mỗi URL một lần.
* Phần lớn nguồn dữ liệu đến từ **các trang báo kinh tế và nông sản tại Việt Nam**.
* Crawler xử lý được các trường hợp:

  * Cloudflare
  * trang yêu cầu JavaScript
  * HTML rỗng

Điều này giúp tăng đáng kể **tỷ lệ crawl thành công**.

---

# Tổng kết

Bước 2 đã thu thập thành công dataset raw HTML phục vụ cho bước xử lý tiếp theo.

```
Discovery URLs:        430
Unique article URLs:   148
HTML crawled:          143
Missing pages:         5
Coverage:              ~97%
```

Dataset này sẽ được sử dụng trong bước tiếp theo của pipeline để **parse nội dung bài báo và trích xuất thông tin giá cà phê**.
