import json

with open('/Users/minh/Documents/Ky_2_nam_3/CS313/eda/eda.ipynb', 'r', encoding='utf-8') as f:
    nb = json.load(f)

def md_cell(text):
    return {
        "cell_type": "markdown",
        "id": "",
        "metadata": {},
        "source": [text]
    }

md0 = """# 📊 Phân Tích Dữ Liệu Thị Trường Cà Phê (EDA)

Notebook này thực hiện **Phân tích Dữ liệu Khám phá (Exploratory Data Analysis - EDA)** cho dữ liệu giá cà phê thế giới, tập trung vào hai loại chính là **Arabica** và **Robusta**.

## 🎯 Mục tiêu phân tích
- Hiểu cấu trúc và chất lượng dữ liệu thô
- Chuẩn hóa giá quốc tế về đơn vị **VND/kg** để dễ so sánh
- Phân tích xu hướng giá, biến động và khối lượng giao dịch
- Tìm hiểu mối tương quan giữa hai loại cà phê
- Đánh giá rủi ro thông qua phân phối lợi nhuận hàng ngày

## 📦 Thư viện sử dụng
| Thư viện | Mục đích |
|---|---|
| `pandas` | Đọc và xử lý dữ liệu dạng bảng |
| `matplotlib` / `seaborn` | Vẽ biểu đồ tĩnh (histogram, boxplot) |
| `plotly` | Vẽ biểu đồ tương tác (nến, đường xu hướng) |
| `io` | Xử lý chuỗi văn bản thô như file CSV |"""

md1 = """## 1️⃣ Bước 1: Đọc và Tiền xử lý Dữ liệu

### Nguồn dữ liệu
- **Arabica**: Dữ liệu giá giao dịch hàng ngày trên sàn ICE (đơn vị gốc: **Cents/lb**)
- **Robusta**: Dữ liệu giá giao dịch hàng ngày trên sàn LIFFE (đơn vị gốc: **USD/Tấn**)
- Phạm vi thời gian: Từ **03/2023** đến **2025**

### Các thách thức xử lý
Hàm `load_and_preprocess_coffee()` giải quyết đồng thời nhiều vấn đề:
1. **Lỗi file Arabica**: Các dòng bị bọc trong dấu ngoặc kép thừa → dùng `strip('"')`
2. **Định dạng số phức tạp**: Số có dấu phẩy phân cách nghìn (vd: `3,692.00`) → tham số `thousands=','`
3. **Cột Volume**: Ký hiệu `K` (nghìn), `M` (triệu) → hàm `parse_volume()` tùy chỉnh
4. **Định dạng ngày tháng hỗn hợp**: Vừa `MM/DD/YYYY` vừa `YYYY-MM-DD` → `format='mixed'`
5. **Cột Change %**: Có ký tự `%` → loại bỏ trước khi chuyển sang `float`

### Kết quả
- Dữ liệu được sắp xếp theo thời gian từ quá khứ → hiện tại (`sort_values('Date')`)
- Hai DataFrame sạch: `arabica_df` và `robusta_df` với 7 cột: `Date`, `Price`, `Open`, `High`, `Low`, `Vol.`, `Change %`"""

md2 = """## 2️⃣ Bước 2: Chuẩn hóa Đơn vị về VND/kg

Để so sánh công bằng giữa hai loại cà phê, toàn bộ dữ liệu giá được quy đổi sang **VND/kg** bằng tỷ giá cố định `USD/VND = 25,400`.

### Công thức quy đổi

| Loại cà phê | Đơn vị gốc | Hệ số chuyển đổi | Đơn vị sau |
|---|---|---|---|
| **Arabica** | Cents/lb | `× 22.0462 × 25,400 ÷ 1,000` | VND/kg |
| **Robusta** | USD/Tấn | `× 25,400 ÷ 1,000` | VND/kg |

> 💡 **Giải thích**: 1 pound ≈ 0.4536 kg, nên 1 USD/lb = 22.0462 USD/Tấn. Nhân tỷ giá rồi chia 1000 để ra VND/kg."""

md3 = """## 3️⃣ Biểu đồ 1: Nến Nhật & Khối lượng Giao dịch

### Mô tả biểu đồ
Biểu đồ tương tác 2 hàng, có nút chuyển đổi giữa **Arabica** và **Robusta**:
- **Hàng trên (70%)**: Biểu đồ nến Nhật (Candlestick) — mỗi nến biểu diễn `Open`, `High`, `Low`, `Close (Price)` trong một phiên giao dịch
  - 🟢 **Nến xanh**: Giá đóng cửa ≥ giá mở cửa (phiên tăng)
  - 🔴 **Nến đỏ**: Giá đóng cửa < giá mở cửa (phiên giảm)
- **Hàng dưới (30%)**: Biểu đồ cột khối lượng giao dịch (`Vol.`), tô màu xanh/đỏ tương ứng với nến

### Nhận xét
- Giai đoạn **2023-2024**: Arabica giao dịch trong vùng **~100,000 – 150,000 VND/kg**, khối lượng ổn định
- Giai đoạn **2024-2025**: Giá Arabica tăng mạnh lên vùng **200,000+ VND/kg**, biên độ nến rộng hơn cho thấy biến động cao hơn
- Robusta duy trì vùng giá thấp hơn (~55,000 – 140,000 VND/kg) và có biên độ biến động hẹp hơn"""

md4 = """## 4️⃣ Biểu đồ 2: Xu hướng Giá & Đường Trung bình Động (SMA)

### Mô tả biểu đồ
Biểu đồ 3 hàng, cùng chia sẻ trục thời gian và thanh trượt ở hàng cuối:

1. **Hàng 1 — So sánh xu hướng chung**: Vẽ đường giá Arabica (đỏ) và Robusta (xanh) trên cùng một đồ thị
2. **Hàng 2 — Phân tích kỹ thuật Robusta**: Giá thực tế + 3 đường SMA (7, 14, 30 ngày)
3. **Hàng 3 — Phân tích kỹ thuật Arabica**: Giá thực tế + 3 đường SMA (7, 14, 30 ngày)

### Ý nghĩa các đường SMA
| Đường | Ý nghĩa |
|---|---|
| **SMA 7** (cam) | Xu hướng ngắn hạn, phản ứng nhanh với biến động |
| **SMA 14** (xanh lá) | Xu hướng trung hạn, cân bằng giữa nhạy và ổn định |
| **SMA 30** (hồng) | Xu hướng dài hạn, lọc bỏ nhiễu thị trường |

### Nhận xét
- Cả Arabica và Robusta đều có **xu hướng tăng dài hạn** từ 2023 đến 2025
- Arabica tăng mạnh hơn và đạt đỉnh cao hơn (~230,000 VND/kg vào Q3/2025)
- Khi SMA 7 cắt lên trên SMA 30 → **tín hiệu mua** (Golden Cross); cắt xuống → **tín hiệu bán** (Death Cross)
- Hai loại cà phê có xu hướng di chuyển **cùng chiều** nhưng biên độ khác nhau"""

md5 = """## 5️⃣ Biểu đồ 3: Chênh lệch Giá (Spread) — Phân tích Arbitrage

### Mô tả biểu đồ
Biểu đồ đường duy nhất thể hiện **Spread = Giá Arabica − Giá Robusta** (đơn vị: VND/kg) theo thời gian, kèm đường trung bình Spread làm mốc tham chiếu.

### Ý nghĩa
- **Spread dương**: Arabica đắt hơn Robusta (thường xuyên xảy ra do chất lượng khác nhau)
- **Spread tăng**: Arabica đang tăng giá nhanh hơn hoặc Robusta giảm
- **Spread giảm** (hội tụ về trung bình): Cơ hội arbitrage giảm dần

### Nhận xét
- Spread trung bình duy trì ở mức **~50,000 – 80,000 VND/kg**
- Cuối năm 2024 và 2025, Spread mở rộng mạnh khi Arabica bùng nổ
- Spread không ổn định cho thấy hai thị trường vẫn có **đặc tính riêng biệt**"""

md6 = """## 6️⃣ Biểu đồ 4: Biến động Nội ngày & Phân tích Khối lượng

### Mô tả biểu đồ
Dashboard 2 hàng:

**Hàng 1 — Biến động nội ngày (Intraday Volatility)**:
- Tính bằng `High − Low` mỗi phiên (VND/kg)
- So sánh biên độ dao động của Arabica (đỏ) và Robusta (xanh)

**Hàng 2 — Xác nhận xu hướng bằng khối lượng (Robusta)**:
- **Cột màu xanh/đỏ**: Khối lượng giao dịch từng phiên (trục trái)
- **Đường cam**: SMA 20 ngày của Volume, làm đường mốc trung bình
- **Đường trắng**: Giá đóng cửa (trục phải) — để xem liệu xu hướng giá có được xác nhận bởi volume không

### Nhận xét
- Arabica có **biên độ nội ngày lớn hơn** Robusta, phản ánh tính đầu cơ cao hơn
- Các đợt tăng/giảm giá mạnh thường đi kèm với **spike volume** — xác nhận tín hiệu xu hướng
- Volume Robusta ổn định và có xu hướng tăng theo giá, cho thấy xu hướng tăng được xác nhận"""

md7 = """## 7️⃣ Biểu đồ 5: Phân tích Rủi ro & Phân phối Lợi nhuận

### Mô tả biểu đồ
Lưới 2×2 gồm 4 biểu đồ Seaborn/Matplotlib:

| Vị trí | Loại biểu đồ | Nội dung |
|---|---|---|
| Trên trái | Histogram + KDE | Phân phối `Change %` của Arabica |
| Trên phải | Histogram + KDE | Phân phối `Change %` của Robusta |
| Dưới trái | Boxplot | Nhận diện outlier — Arabica |
| Dưới phải | Boxplot | Nhận diện outlier — Robusta |

### Kết quả thống kê — Top 10 ngày biến động mạnh nhất

**Arabica** — Các ngày biến động lớn nhất:
| # | Ngày | Giá (VND/kg) | Thay đổi |
|---|---|---|---|
| 1 | 2025-09-17 | 217,578 | **-7.98%** |
| 2 | 2025-12-17 | 197,055 | -7.22% |
| 3 | 2023-11-30 | 109,195 | **+7.08%** |
| 4 | 2024-12-02 | 167,544 | -6.98% |
| 5 | 2024-07-09 | 141,113 | +6.69% |

**Robusta** — Biến động cực đoan hơn (lớn nhất -10.62%):
| # | Ngày | Giá (VND/kg) | Thay đổi |
|---|---|---|---|
| 1 | 2024-12-02 | 122,072 | **-10.62%** |
| 2 | 2025-07-14 | 88,011 | +9.31% |
| 3 | 2024-05-02 | 93,472 | -7.49% |
| 4 | 2024-11-27 | 139,598 | +7.47% |
| 5 | 2025-09-19 | 105,029 | -7.02% |

### Nhận xét
- Phân phối `Change %` của cả hai loại xấp xỉ **chuẩn (Normal)** với đỉnh tập trung quanh 0%
- **Arabica** có đuôi phân phối đối xứng hơn; **Robusta** có tail nặng hơn ở phía âm
- Boxplot cho thấy nhiều **outlier** ở cả hai phía, đặc biệt Robusta với ngày -10.62%
- Robusta có thể rủi ro hơn xét về **tail risk** (rủi ro đuôi phân phối)"""

md_summary = """---

## 📋 Tổng kết EDA

### Những phát hiện chính

| Chủ đề | Arabica | Robusta |
|---|---|---|
| **Mức giá (VND/kg)** | 100,000 – 230,000 | 55,000 – 140,000 |
| **Xu hướng dài hạn** | Tăng mạnh 2023-2025 | Tăng, biên độ nhỏ hơn |
| **Biến động nội ngày** | Cao hơn | Thấp hơn |
| **Tail risk hàng ngày** | ~±7-8% | ~±10% |
| **Spread so với Robusta** | Luôn cao hơn | — |

### Định hướng bước tiếp theo
- Feature Engineering: Tạo thêm các đặc trưng kỹ thuật (RSI, MACD, Bollinger Bands)
- Kiểm định tương quan: Pearson/Spearman giữa hai loại cà phê và yếu tố vĩ mô
- Mô hình dự báo: ARIMA, LSTM hoặc XGBoost cho chuỗi thời gian
- Phân tích mùa vụ: Tìm hiểu ảnh hưởng của mùa thu hoạch đến biến động giá"""

original = nb['cells']
new_cells = []

insertions = {
    0: md_cell(md0),
    1: md_cell(md1),
    2: md_cell(md2),
    3: md_cell(md3),
    4: md_cell(md4),
    5: md_cell(md5),
    6: md_cell(md6),
    7: md_cell(md7),
}

for i, cell in enumerate(original):
    if i in insertions:
        new_cells.append(insertions[i])
    new_cells.append(cell)

new_cells.append(md_cell(md_summary))

nb['cells'] = new_cells

with open('/Users/minh/Documents/Ky_2_nam_3/CS313/eda/eda.ipynb', 'w', encoding='utf-8') as f:
    json.dump(nb, f, ensure_ascii=False, indent=1)

print("Done! Total cells:", len(nb['cells']), "(was", len(original), ")")
