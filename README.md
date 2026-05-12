# ☕ Coffee Price Analysis — CS313

Dự án phân tích dữ liệu giá cà phê thế giới (Arabica & Robusta), bao gồm thu thập bài viết tin tức, tiền xử lý dữ liệu giá và phân tích khám phá dữ liệu (EDA) toàn diện.

---

##  Cấu trúc thư mục

```
CS313/
├── data/
│   ├── arabica.csv              # Dữ liệu giá Arabica thô (Cents/lb - ICE)
│   └── robusta.csv              # Dữ liệu giá Robusta thô (USD/Tấn - LIFFE)
├── eda/
│   └── eda.ipynb                # Notebook EDA chính (biểu đồ tương tác)
├── 03_articles/                 # Bài viết thô theo ngày xuất bản
├── coffee_articles.csv          # Bài viết đã lọc từ khóa cà phê
├── coffee_prices_extracted.csv  # Giá cà phê đã trích xuất
├── coffee_price_source_websites.csv
├── combine_eda.ipynb            # Notebook kết hợp phân tích
├── merge.ipynb                  # Notebook hợp nhất dữ liệu
├── requirements.txt
└── venv/
```

---

##  EDA — Phân tích Dữ liệu Khám phá (`eda/eda.ipynb`)

### Dữ liệu đầu vào
| Loại | Nguồn | Đơn vị gốc | Phạm vi thời gian |
|---|---|---|---|
| **Arabica** | Sàn ICE New York | Cents/lb | 03/2023 – 2025 |
| **Robusta** | Sàn LIFFE London | USD/Tấn | 03/2023 – 2025 |

Toàn bộ giá được **chuẩn hóa về VND/kg** (tỷ giá cố định 1 USD = 25,400 VND) để so sánh trực tiếp.

### Các biểu đồ phân tích

| # | Biểu đồ | Công cụ | Nội dung |
|---|---|---|---|
| 1 | **Nến Nhật & Khối lượng** | Plotly | OHLC + Volume, chuyển đổi Arabica ↔ Robusta bằng nút bấm |
| 2 | **Xu hướng & SMA** | Plotly | So sánh giá 2 loại + Moving Average 7/14/30 ngày |
| 3 | **Spread (Arbitrage)** | Plotly | Chênh lệch giá Arabica − Robusta theo thời gian |
| 4 | **Biến động & Volume** | Plotly | Intraday Volatility + xác nhận xu hướng bằng Volume |
| 5 | **Phân phối Rủi ro** | Seaborn | Histogram/KDE + Boxplot của `Change %` hàng ngày |

### Những phát hiện chính
- **Arabica** giao dịch cao hơn Robusta ~50,000–80,000 VND/kg (spread dương ổn định)
- Cả hai loại đều có **xu hướng tăng dài hạn** từ 2023 đến 2025
- **Arabica** đạt đỉnh ~230,000 VND/kg (Q3/2025); **Robusta** đỉnh ~140,000 VND/kg
- **Robusta** có tail risk cao hơn (biến động lớn nhất: **−10.62%** ngày 02/12/2024)
- Các đợt giá tăng/giảm mạnh đều đi kèm spike khối lượng giao dịch

---

## Thu thập & Lọc Bài viết

Pipeline xử lý bài viết tin tức liên quan đến thị trường cà phê:

1. **Quét & Đọc** — Duyệt toàn bộ `03_articles/`, đọc nội dung từng file
2. **Hợp nhất** — So khớp `URL_HASH` với `coffee_price_source_websites.csv`
3. **Lọc từ khóa** — Giữ lại bài viết chứa `robusta`, `arabica`, `giá cà phê` (RegEx)
4. **Xuất** — Lưu kết quả ra `coffee_articles.csv`

---

## Hướng dẫn cài đặt

```bash
# 1. Kích hoạt môi trường ảo
source venv/bin/activate        # macOS/Linux
# .\venv\Scripts\activate       # Windows

# 2. Cài đặt thư viện
pip install -r requirements.txt

# 3. Mở notebook EDA
jupyter notebook eda/eda.ipynb
```

### Thư viện chính
| Thư viện | Phiên bản | Mục đích |
|---|---|---|
| `pandas` | ≥2.0 | Xử lý dữ liệu bảng |
| `plotly` | ≥5.0 | Biểu đồ tương tác |
| `seaborn` | ≥0.12 | Biểu đồ thống kê |
| `matplotlib` | ≥3.7 | Biểu đồ tĩnh |

---

##  Thông tin dự án

- **Môn học**: CS313
- **Python**: 3.14+
- **Kernel**: `venv (3.14.4)`