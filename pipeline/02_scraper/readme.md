# Bước 2 — Thu thập Raw HTML (Web Crawling)

## Mục tiêu

Mục tiêu của **Bước 2** trong pipeline là thu thập và lưu trữ **raw HTML** của các bài báo được phát hiện ở **Bước 1 (Discovery)**.

Việc lưu raw HTML giúp:

* Giữ lại **toàn bộ nội dung gốc của trang web**
* Phục vụ cho các bước xử lý sau như:

  * parsing nội dung bài báo
  * trích xuất thông tin (information extraction)
  * phân tích dữ liệu (EDA)

Raw HTML được lưu **nguyên bản**, không chỉnh sửa.

---

# Dữ liệu đầu vào

Dữ liệu đầu vào của bước này là kết quả từ bước discovery:

```text
data/01_discovered/2026-03.jsonl
```

File `.jsonl` chứa kết quả tìm kiếm theo nhiều query khác nhau.

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

Mỗi record chứa danh sách các URL bài báo.

---

# Quy trình crawl

Crawler thực hiện các bước sau:

### 1. Đọc dữ liệu discovery

* Đọc file `.jsonl`
* Trích xuất tất cả URL từ trường `results`.

---

### 2. Loại bỏ URL trùng lặp

Một bài báo có thể xuất hiện trong **nhiều query khác nhau**, vì vậy cần loại bỏ trùng lặp trước khi crawl.

Ví dụ:

```
query 1 → bài báo A  
query 2 → bài báo A  
query 3 → bài báo A
```

Crawler chỉ tải **1 lần**.

---

### 3. Tải HTML của trang web

Crawler gửi HTTP request đến từng URL.

Trong trường hợp:

* HTML quá ngắn
* request thất bại

crawler sẽ **retry bằng browser** để render trang.

---

### 4. Lưu raw HTML

HTML của mỗi trang được lưu **nguyên bản**.

---

### 5. Lưu metadata

Mỗi file HTML đi kèm một file metadata chứa thông tin:

* URL gốc
* domain
* thời gian crawl

Ví dụ metadata:

```json
{
  "url": "https://example.com/article",
  "domain": "example.com",
  "crawl_time": "2026-03-15T16:00:00"
}
```

---

### 6. Tổ chức dữ liệu theo ngày

Các file được lưu theo cấu trúc thư mục theo ngày.

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

Mỗi bài báo tạo ra:

```
<hash>.html  → raw HTML
<hash>.json  → metadata
```

---

# Kết quả sơ bộ

Sau khi chạy crawler trên dataset discovery:

### Thống kê discovery

```
Total URLs: 430
Unique URLs: 148
Duplicate URLs: 282
Number of duplicated URLs: 97
```

Nguyên nhân:

Các query tìm kiếm khác nhau có thể trả về **cùng một bài báo**, dẫn đến nhiều URL trùng.

---

### Kết quả crawl

```
Unique URLs: 148
HTML files downloaded: 129
Missing pages: 19
```

Tỷ lệ crawl thành công:

```
129 / 148 ≈ 87%
```

Tỷ lệ này được xem là **chấp nhận được** trong web crawling.

Các URL không crawl được thường do:

* trang dynamic
* redirect
* trang không phải bài báo
* trang bị chặn

---

### Kiểm tra chất lượng HTML

```
Bad HTML: 0
```

Không có file HTML nào quá nhỏ hoặc lỗi.

---

### Kiểm tra metadata

```
HTML files: 129
Metadata files: 129
```

Mỗi file HTML đều có metadata tương ứng.

---

### Phân bố domain

Các nguồn báo phổ biến:

```
baomoi.com
trangtraiviet.danviet.vn
vov.vn
laodong.vn
nld.com.vn
vietnambiz.vn
thoibaotaichinhvietnam.vn
cafef.vn
```

Đây là các trang báo thường đăng tin về:

* thị trường nông sản
* giá cà phê
* thông tin kinh tế

---

# Nhận xét

* Discovery dataset có **nhiều URL trùng lặp** do nhiều query khác nhau.
* Crawler đã loại bỏ trùng lặp và chỉ crawl mỗi URL một lần.
* Phần lớn nguồn dữ liệu đến từ các trang báo Việt Nam về thị trường nông sản.
* Một số trang dynamic hoặc không phải bài báo có thể không crawl được.

---

# Tổng kết

Bước 2 đã thu thập thành công dataset raw HTML phục vụ cho bước xử lý tiếp theo.

```
Discovery URLs:        430
Unique article URLs:   148
HTML crawled:          129
Coverage:              ~87%
HTML errors:           0
```

Dataset này sẽ được sử dụng trong bước tiếp theo của pipeline để **parse nội dung và trích xuất thông tin giá cà phê**.
