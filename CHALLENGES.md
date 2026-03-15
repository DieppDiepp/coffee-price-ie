# Nhật ký Khó khăn và Thách thức Dự án (Project Challenges Log)

Tệp này ghi lại những khó khăn kỹ thuật, rào cản dữ liệu và các vấn đề phát sinh trong quá trình phát triển hệ thống trích xuất thông tin giá cà phê.

## 1. Discovery (Khám phá nguồn tin)
* **Thách thức:** Các nguồn tin tiếng Việt có cấu trúc URL không đồng nhất, gây khó khăn cho việc lọc link tự động.
* **Giải pháp:** Sử dụng Tavily API kết hợp với các quy tắc lọc domain trong `config/sources.json`.

## 2. Scraping (Thu thập dữ liệu thô)
* **Thách thức:** Nhiều trang báo tài chính (như VnEconomy, CafeF) áp dụng cơ chế chặn bot hoặc yêu cầu render JavaScript để hiển thị nội dung.
* **Giải pháp:** Triển khai cơ chế Hybrid Scraper: ưu tiên dùng HTTP client nhẹ (Scrapling) và tự động chuyển sang Headless Browser (Crawl4AI) khi gặp lỗi hoặc trang trống.

## 3. Parsing (Xử lý nội dung)
* **Thách thức:** Nội dung bài viết thường lẫn lộn quảng cáo, các bảng giá loại hạt khác (hồ tiêu, cao su) hoặc thông tin giá thế giới (London/New York) dễ gây nhiễu cho LLM. Ngoài ra, thư viện bóc tách text (như trafilatura) thường làm hỏng hoặc bỏ qua cấu trúc bảng biểu chứa giá trị.
* **Giải pháp:** Áp dụng chiến lược **"Sentence-first Candidate Mining"**. Cụ thể:
  1. Sử dụng `trafilatura` để lấy text cơ bản, nếu fail hoặc gặp bảng (table), fallback sang `BeautifulSoup` để "trải phẳng" (flatten) cấu trúc bảng thành các câu giả (pseudo-sentences: `Dak Lak | 96.000 đ/kg`).
  2. Chặt câu bằng `underthesea` (tiếng Việt).
  3. Lọc câu bằng các từ khóa tín hiệu (Signals): Chỉ giữ lại câu có chứa tín hiệu Cà phê (VD: robusta, đắk lắk) VÀ tín hiệu Giá (VD: đ/kg, tăng, giảm). Đánh cờ cảnh báo (noise flags) nếu có từ khóa hàng hóa khác (hồ tiêu, cao su) trong cùng câu.

## 4. Information Extraction (Trích xuất thông tin - IE)
* **Thách thức:** Trích xuất chi tiết (địa điểm, giá thấp, giá cao, đơn vị) từ câu văn chứa nhiều loại giá hoặc định dạng phức tạp. Sử dụng API trả phí (như GPT-4) cho toàn bộ corpus quá tốn kém và chậm.
* **Giải pháp:** Chuyển sang sử dụng các mô hình LLM mã nguồn mở tối ưu cho trích xuất JSON:
  *   **Mô hình chính (Extractor): Qwen2.5-7B-Instruct.** 
      * *Lý do chọn:* Đây là mô hình kích thước nhỏ (có thể chạy mượt mà trên GPU Kaggle P100/T4x2 với cấu hình 4-bit) nhưng lại sở hữu năng lực hiểu tiếng Việt cực kỳ vượt trội. Nó bám sát hướng dẫn prompt (Instruction-following), có khả năng phân biệt rõ "Mức giá" và "Biên độ tăng/giảm", đồng thời hỗ trợ xuất dữ liệu ra định dạng cấu trúc JSON rất nghiêm ngặt, ít bị lỗi cú pháp.
  *   **Mô hình đối chứng (Comparator): Llama-3.1-8B-Instruct.**
      * *Lý do chọn:* Llama 3.1 là mô hình State-of-the-Art (SOTA) trong phân khúc 8B tham số, có khả năng suy luận logic và xử lý ngữ cảnh sâu sắc. Việc dùng mô hình này đối chứng song song với Qwen giúp tạo ra một góc nhìn độc lập (hạn chế thiên kiến của một mô hình duy nhất). 
  *   **Mô hình cơ sở (Regex Baseline):**
      * *Lý do chọn:* Để đánh giá hiệu quả thực sự của LLM, dự án xây dựng thêm một bộ trích xuất bằng biểu thức chính quy (Regex) làm mốc cơ sở. Thực nghiệm cho thấy Regex thường xuyên nhận diện sai các mốc thay đổi giá (ví dụ "tăng 500đ") thành giá bán thực tế, làm nổi bật giá trị của khả năng hiểu ngữ cảnh từ LLM.
  *   Chỉ đưa "Candidate Sentences" (kèm 1 câu trước và sau để lấy ngữ cảnh) vào LLM thay vì cả bài viết, giúp tiết kiệm triệt để Token và loại bỏ hoàn toàn nhiễu (hallucination).

## 5. Disagreement Modeling (Mô hình hóa sự bất đồng)
* **Thách thức:** Việc định nghĩa "bất đồng" giữa các nguồn tin khi chúng đăng bài tại các thời điểm khác nhau trong ngày hoặc sử dụng phương pháp khảo sát khác nhau. Đặc biệt là làm sao so sánh tự động sự khác biệt trong kết quả trích xuất của hai mô hình (VD: Qwen và Llama/Baseline).
* **Giải pháp:** 
  * Chia chỉ số Disagreement theo 3 khía cạnh: Temporal (Thời gian), Methodology (Phương pháp), và Value Chain (Chuỗi giá trị).
  * **Sử dụng PhoBERT (`vinai/phobert-base-v2`) để đo độ đo tương đồng ngữ nghĩa (Semantic Similarity):**
    * *Lý do chọn:* Thay vì so sánh chuỗi văn bản cứng nhắc (String matching), việc chuẩn hóa thông tin trích xuất thành câu văn tiếng Việt và dùng PhoBERT để tính Cosine Similarity giúp hệ thống đánh giá mức độ bất đồng một cách mềm dẻo và chính xác hơn. PhoBERT là mô hình nhúng (embedding) tối ưu nhất cho tiếng Việt hiện nay. Ngưỡng (threshold) được đặt ở mức < 0.92 để đánh dấu (flag) các điểm bất đồng.

## 6. Xử lý Thời gian (Date/Time Handling)
* **Thách thức:** Xử lý và chuẩn hóa ngày tháng xuất bản (publication date) và ngày tham chiếu (`date_ref`) từ nhiều nguồn dữ liệu (định dạng không đồng nhất, lệch múi giờ, các cụm từ tiếng Việt như "Hôm nay", "Hôm qua", sai lệch ngày đăng so với ngày của giá cà phê).
* **Giải pháp:** Xây dựng module chuẩn hóa ngày tháng riêng biệt, hỗ trợ múi giờ Việt Nam (UTC+7) và phân tích các biểu thức ngày tháng tiếng Việt. Tất cả các mốc thời gian đều được quy đổi chuẩn xác về định dạng ISO 8601. Thiết lập quy tắc rõ ràng để gán `date_ref` dựa trên ngữ cảnh bài viết thay vì chỉ dùng ngày đăng bài.

---
*Ghi chú: Cập nhật tệp này mỗi khi gặp vấn đề mới trong pipeline.*
