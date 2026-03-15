# BÁO CÁO KỸ THUẬT: PHÂN TÍCH VÀ TỐI ƯU HÓA TỪ KHÓA TRUY VẤN (QUERY EDA)

## 1. Đặt vấn đề và Mục tiêu
Trong quy trình thu thập dữ liệu tự động (Data Scraping) từ báo chí, việc lựa chọn từ khóa truy vấn (Search Query) đóng vai trò quyết định đến **độ phủ (Coverage)** và **độ chính xác (Precision)** của tập dữ liệu. 

Nếu từ khóa được chọn theo cảm tính chủ quan của người nghiên cứu (ví dụ: chỉ tìm cụm `"giá cà phê robusta"`), hệ thống có thể bỏ lỡ lượng lớn dữ liệu thực tế do các tòa soạn báo có thói quen đặt tiêu đề khác. Do đó, mục tiêu của báo cáo này là **sử dụng dữ liệu để chứng minh hành vi đặt tiêu đề của báo chí Việt Nam**, từ đó xây dựng bộ từ khóa tối ưu nhất cho hệ thống.

## 2. Quy mô Dữ liệu và Phương pháp Thu thập (Methodology)

Để đảm bảo tính khách quan, nhóm nghiên cứu đã áp dụng kỹ thuật **Khai phá Văn bản (Text Analytics)** trên một tập dữ liệu mẫu được thu thập theo các bước sau:

* **Bước 1: Khởi tạo & Mở rộng (Seed Expansion):** Sử dụng API Google Autocomplete để thu thập các từ khóa mà người Việt Nam thực tế hay gõ nhất từ 3 hạt giống ban đầu: `giá cà phê`, `giá cà phê robusta`, `giá cà phê arabica`. Kết quả thu được khoảng **30 từ khóa phổ biến** (long-tail keywords).
* **Bước 2: Lấy mẫu Văn bản Báo chí (Sampling):** Sử dụng 30 từ khóa trên để tìm kiếm qua Google Search API (Serper) trong phạm vi **3 ngày gần nhất**. Nhóm lấy Top 10 bài báo cho mỗi từ khóa (tương đương **~300 bài báo**).
* **Bước 3: Phạm vi quét (Corpus Scope):** Hệ thống tiến hành bóc tách và quét trên **CẢ Tiêu đề (Title) VÀ Đoạn trích tóm tắt (Snippet)**. 
    * *Lý do:* Tiêu đề phản ánh cách báo chí "giật tít" thu hút người đọc, trong khi Snippet (đoạn text nhỏ dưới tiêu đề trên Google) thường chứa nội dung cô đọng nhất về mức giá thực tế. Quét cả hai (tương đương **~600 đoạn văn bản**) giúp tăng độ tin cậy của thống kê.
* **Bước 4: Phân tích N-gram:** Làm sạch 600 đoạn văn bản trên (bỏ dấu câu, số liệu) và đếm tần suất xuất hiện của các cụm từ đi liền nhau. Phân tích tập trung vào **Tri-grams** (cụm 3 từ) và **4-grams** (cụm 4 từ) để tìm ra các cụm từ có nghĩa hoàn chỉnh nhất.

## 3. Kết quả Định lượng (Quantitative Results)

Kết quả phân tích N-gram trên tập mẫu 600 đoạn văn bản (Title + Snippet) cho thấy sự phân hóa rõ rệt trong ngôn ngữ báo chí:

**Top các cụm 4 từ (4-grams) xuất hiện nhiều nhất:**
1.  `giá cà phê hôm nay`: **97 lần** (Áp đảo hoàn toàn)
2.  `giá cà phê trực tuyến`: **64 lần**
3.  `cà phê thế giới`: **40 lần**
4.  `giá cà phê arabica`: **37 lần**
5.  `giá cà phê robusta`: **27 lần**
6.  `sàn london new york`: **24 lần**

**Phân tích từ Google Autocomplete (Hành vi người dùng):**
* Người dùng tìm kiếm chung chung thường gõ: `giá cà phê`, `giá cà phê hôm nay`, `giá cà phê tươi`.
* Người dùng tìm kiếm theo địa phương thường gõ: `giá cà phê đắk lắk`, `giá cà phê lâm đồng`.
* Tên định danh chuyên ngành: `arabica cầu đất`, `arabica sơn la`, `robusta london`.

## 4. Phân tích Chuyên sâu (Insights) và Lựa chọn Từ khóa

Dựa trên các con số biết nói ở phần 3, nhóm nghiên cứu rút ra các kết luận mang tính định hướng cho việc cấu hình hệ thống:

* **Sự áp đảo của "Giá cà phê hôm nay":** Tại thị trường Việt Nam, Robusta chiếm hơn 90% sản lượng. Do đó, cụm từ chung chung `"giá cà phê hôm nay"` được báo chí mặc định dùng để chỉ giá Robusta nội địa (xuất hiện tới 97 lần, gấp gần 4 lần so với chữ `"giá cà phê robusta"`). 
* **Định danh riêng của Arabica:** Khi muốn nhắc đến Arabica, báo chí và người dùng bắt buộc phải gọi đích danh tên loại hạt này (`giá cà phê arabica` xuất hiện 37 lần) để tránh nhầm lẫn với giá chung (Robusta).
* **Tính địa phương:** Tỉnh Đắk Lắk (thủ phủ Robusta) và Lâm Đồng (thánh địa Arabica) là hai "từ khóa neo" cực kỳ mạnh để hệ thống tìm kiếm khoanh vùng chính xác loại cà phê mong muốn.

## 5. Cấu hình Truy vấn Chính thức (Final Query Templates)

Từ các lập luận trên, nhóm quyết định thay thế chữ "hôm nay" bằng chuỗi biến số `ngày {day} tháng {month} năm {year}` (để phù hợp với việc cào dữ liệu quá khứ), và chốt lại 4 mẫu truy vấn (Query Templates) cho dự án:

```json
  "query_templates": [
    {
      "id": "robusta_general",
      "target": "robusta",
      "template": "giá cà phê ngày {day} tháng {month} năm {year}",
      "priority": 1,
      "_comment": "Query chủ lực cho Robusta (Kế thừa từ cụm 'giá cà phê hôm nay' với tần suất 97 lần)"
    },
    {
      "id": "robusta_local",
      "target": "robusta",
      "template": "giá cà phê đắk lắk ngày {day} tháng {month} năm {year}",
      "priority": 2,
      "_comment": "Query vét dữ liệu địa phương (Dựa trên gợi ý Autocomplete hàng đầu cho Robusta)"
    },
    {
      "id": "arabica_explicit",
      "target": "arabica",
      "template": "giá cà phê arabica ngày {day} tháng {month} năm {year}",
      "priority": 1,
      "_comment": "Query chủ lực cho Arabica (Tần suất xuất hiện 37 lần trên báo chí)"
    },
    {
      "id": "arabica_local",
      "target": "arabica",
      "template": "giá cà phê lâm đồng ngày {day} tháng {month} năm {year}",
      "priority": 2,
      "_comment": "Query vét dữ liệu địa phương (Dựa trên gợi ý Autocomplete hàng đầu cho Arabica)"
    }
  ]