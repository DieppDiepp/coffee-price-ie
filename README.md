# Coffee Price Information Extraction (IE) Project

Dự án Đồ án Data Mining: **Multi-Source Agricultural Price IE with Disagreement Modeling & Forecasting Signal** (Nghiên cứu trường hợp: Cà phê Robusta — Tây Nguyên, Việt Nam).
Hệ thống tự động trích xuất thông tin giá cà phê từ văn bản đa nguồn tiếng Việt, đo lường sự bất đồng thông tin (Disagreement) và ứng dụng làm tín hiệu dự báo giá cho ngày hôm sau.

## Mục tiêu chính
1. **Trích xuất thông tin (IE)**: Tự động trích xuất các đề cập giá (price mention) kèm ngữ cảnh định tính (loại giá, nguồn báo, mức độ chắc chắn - uncertainty) từ luồng văn bản đa nguồn bằng LLM.
2. **Mô hình hóa bất đồng (Disagreement Modeling)**: Tổng hợp (aggregate) và đo lường sự bất đồng thông tin giữa các nguồn theo ba chiều: Thời gian (TEMPORAL), Phương pháp (METHODOLOGY), và Chuỗi giá trị (VALUE_CHAIN).
3. **Dự báo (Forecasting)**: Đánh giá xem chỉ số bất đồng (Disagreement score) có mang lại giá trị dự báo cho biến động giá ngày hôm sau hay không.

## Output dự án
* **Dataset Gold-standard**: Tập dữ liệu 2.000–3.000 price mentions được gán nhãn chi tiết (certainty, price_type, reporter), là tài nguyên tiên phong cho nông sản Việt Nam.
* **Hệ thống Disagreement Records**: Phân loại bất đồng và tính điểm bất đồng hàng ngày.
* **Kết quả dự báo**: So sánh các mô hình (SARIMA, XGBoost, LSTM) khi có/không có tín hiệu bất đồng làm đặc trưng.

## Ý nghĩa
* Cung cấp một Ontology / Schema gán nhãn mới cho tiếng Việt về giá cả kèm uncertainty.
* Giúp hiểu được mâu thuẫn thông tin (noise) hiện diện có cấu trúc trên thị trường và sử dụng nó như một tín hiệu (signal) để dự báo thay vì loại bỏ.
* Xây dựng baseline cho cộng đồng nghiên cứu về bài toán trích xuất văn bản giá nông sản.

## Cấu trúc Repository

```text
coffee-price-ie/
│
├── .env                  # Cấu hình biến môi trường cục bộ
├── .gitignore            # Các tệp/thư mục bị bỏ qua bởi Git
├── README.md             # Tổng quan dự án và Tài liệu gốc
├── requirements.txt      # Thông tin Dependencies và Packages
│
├── database/             
│   ├── schema.sql        # Lược đồ database
│   └── db_utils.py       # Các script hỗ trợ thao tác Database
│
├── config/
│   ├── sources.json      # List các trang báo và thông tin crawl (vd xpath...)
│   ├── event_calendar.json # Các data sự kiện
│   └── prompts/          # Thư mục lưu cấu hình/prompts cho các task vụ
│       ├── ie_v1_gpt4.txt        
│       └── disagr_type_v1.txt    
│
├── logs/                 # Thư mục chứa logs files trong quá trình chạy Pipeline
│   ├── scraper.log       
│   └── pipeline.log      
│
├── pipeline/             # Core scripts và Pipeline Logic
│   ├── 01_discovery/
│   │   ├── main.py              # File chạy chính để tìm link
│   │   └── tavily_client.py     # File chứa hàm gọi API của Tavily
│   ├── 02_scraper/
│   │   ├── main.py
│   │   └── extractors.py        # Các hàm bóc tách HTML theo từng trang báo
│   ├── 03_parser/
│   ├── 04_ie/
│   ├── 05_disagreement/
│   ├── 06_ground_truth/
│   └── 07_forecasting/
│
├── data/                 # Thư mục chứa data theo format JSONL (Mỗi tháng)
│   ├── 01_discovered/    
│   ├── 03_articles/      
│   ├── 04_price_mentions/
│   ├── 05_disagreement/
│   ├── 06_ground_truth/
│   └── 07_exports/       
│
├── annotation/           # Thư mục cho quá trình làm Annotation / Gắn nhãn
│   ├── guidelines.md     # Hướng dẫn Annotation cho con người/LLM
│   ├── samples/          # Dữ liệu Sample (có thể để debug)
│   └── labels/           # Dữ liệu chứa Ground-truth/Labels 
│
├── notebooks/            # Notebook (.ipynb) để phân tích Exploratory Data Analysis & Visualize
│
├── dashboard/            # Mã nguồn cho Giao diện UI/Dashboard
│
└── experiments/          # Script chạy thử nghiệm / Thí nghiệm 
```