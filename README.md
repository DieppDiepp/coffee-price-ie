# Dự án Lọc và Xử lý Dữ liệu Bài viết Cà phê

Dự án này cung cấp một công cụ bằng Python (thông qua Jupyter Notebook) để tự động hóa việc trích xuất, hợp nhất và lọc dữ liệu bài viết từ các tập tin cục bộ. Mục tiêu chính là xác định và gom nhóm các bài viết liên quan đến chủ đề cà phê (như Robusta, Arabica, giá cả) từ một kho dữ liệu thô.

## 📂 Cấu trúc thư mục (Project Structure)

Dự án bao gồm các tệp và thư mục chính sau:

* **`03_articles/`**: Thư mục chứa các tệp văn bản/HTML thô. Mỗi tệp đại diện cho một bài viết (được tổ chức trong các thư mục con theo ngày xuất bản).
* **`coffee_price_source_websites.csv`**: File dữ liệu đầu vào chứa danh sách các nguồn bài viết (bao gồm cột `URL_HASH` để đối chiếu).
* **`coffee_articles.csv`**: File dữ liệu đầu ra chứa kết quả cuối cùng sau khi đã hợp nhất và lọc từ khóa.
* **`test.ipynb`**: File Jupyter Notebook chứa mã nguồn chính thực thi toàn bộ quy trình.
* **`requirements.txt`**: Danh sách các thư viện Python cần thiết để chạy dự án.
* **`venv/`**: Thư mục môi trường ảo Python (Virtual Environment) của dự án.

## ⚙️ Luồng xử lý dữ liệu (Workflow)

Chương trình thực hiện qua 3 bước chính:

1.  **Quét và Đọc File (Load Articles):** Quét toàn bộ thư mục `03_articles`, đọc nội dung từng tệp và tổng hợp thành một DataFrame với các thông tin: Ngày xuất bản, Tên file, Nội dung và Đường dẫn.
2.  **Hợp nhất Dữ liệu (Merge Data):** So khớp cột `URL_HASH` từ file `coffee_price_source_websites.csv` với tên tệp bài viết. Loại bỏ các dữ liệu trùng lặp hoặc không cần thiết để giữ lại các bản ghi hợp lệ.
3.  **Lọc Từ khóa & Xuất File (Filter & Export):** Sử dụng Regular Expressions (RegEx) để quét nội dung bài viết. Nếu nội dung chứa các từ khóa liên quan đến cà phê (`robusta`, `arabica`, `giá cà phê`), bài viết đó sẽ được giữ lại và lưu ra file `coffee_articles.csv`.

## 🚀 Hướng dẫn cài đặt và sử dụng

### 1. Cài đặt môi trường

Đảm bảo bạn đã cài đặt Python 3.x trên máy. Mở Terminal/Command Prompt trong thư mục dự án và thực hiện các lệnh sau:

**Kích hoạt môi trường ảo (nếu bạn chưa kích hoạt):**
* Trên Windows:
    ```bash
    .\venv\Scripts\activate
    ```
* Trên macOS/Linux:
    ```bash
    source venv/bin/activate
    ```

**Cài đặt thư viện:**
```bash
pip install -r requirements.txt