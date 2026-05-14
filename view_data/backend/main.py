import os
import re
import pandas as pd
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional

print("🚀 KHỞI ĐỘNG HỆ THỐNG COFFEE FINANCE BACKEND (V8.5 - DUAL GROUND TRUTH)")

# ==========================================
# 1. CẤU HÌNH ĐƯỜNG DẪN DỮ LIỆU
# ==========================================
BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
NEWS_DATA_PATH = os.path.join(BASE_DIR, 'data', 'html', 'final_enriched_dataset.csv')
ROBUSTA_GT_PATH = os.path.join(BASE_DIR, 'data', 'ground_truth', 'robusta_vnd.csv')
ARABICA_GT_PATH = os.path.join(BASE_DIR, 'data', 'ground_truth', 'arabica_vnd.csv')

# ==========================================
# 2. KHỞI TẠO FASTAPI VÀ MIDDLEWARE
# ==========================================
app = FastAPI(title="Coffee Finance API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], 
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ==========================================
# 3. ĐỊNH NGHĨA SCHEMA
# ==========================================
class CoffeeNews(BaseModel):
    date: str
    region: str
    domain: str
    url: str
    content_snippet: str
    price_llm: str
    price_dl: str
    # Bỏ trường target đi vì không cần thiết nữa

class SearchResponse(BaseModel):
    market_insight: str
    data: List[CoffeeNews]

# ==========================================
# 4. CÁC HÀM XỬ LÝ LOGIC PHỤ TRỢ
# ==========================================
def clean_price(price_str: str) -> int:
    """Làm sạch chuỗi giá thành số nguyên (VD: '95.700 VNĐ/kg' -> 95700)"""
    try:
        num_str = re.sub(r'[^\d]', '', str(price_str))
        return int(num_str) if num_str else 0
    except:
        return 0

def fetch_price_from_csv(file_path: str, query_date: str) -> Optional[int]:
    """Hàm chung để đọc giá từ file CSV Ground Truth"""
    if not os.path.exists(file_path):
        return None
    try:
        df = pd.read_csv(file_path)
        df['Date'] = pd.to_datetime(df['Date']).dt.strftime('%Y-%m-%d')
        row = df[df['Date'] == query_date]
        if not row.empty:
            return int(row.iloc[0]['Price'])
        return None
    except Exception as e:
        print(f"Lỗi khi đọc file {file_path}: {e}")
        return None

def get_dual_ground_truth(query_date: str) -> dict:
    """Lấy giá của cả Robusta và Arabica trong ngày"""
    return {
        "robusta": fetch_price_from_csv(ROBUSTA_GT_PATH, query_date),
        "arabica": fetch_price_from_csv(ARABICA_GT_PATH, query_date)
    }

def generate_market_insight(news_data: list, gt_prices: dict) -> str:
    """Hệ thống Rule-based đối chiếu chênh lệch và đoán loại cà phê"""
    if not news_data:
        return "Không có đủ dữ liệu báo chí trong ngày này để đưa ra phân tích."

    dl_prices = [clean_price(item['price_dl']) for item in news_data if clean_price(item['price_dl']) > 0]
    llm_prices = [clean_price(item['price_llm']) for item in news_data if clean_price(item['price_llm']) > 0]

    if not dl_prices or not llm_prices:
        return "Dữ liệu giá bóc tách bị lỗi hoặc không đầy đủ để phân tích thống kê."

    avg_dl = sum(dl_prices) / len(dl_prices)
    avg_llm = sum(llm_prices) / len(llm_prices)
    
    insight_parts = []

    # 1. Đánh giá sự đồng thuận AI
    ai_diff = abs(avg_llm - avg_dl)
    if ai_diff > 3000:
        insight_parts.append(f" Các mô hình AI bất đồng lớn (lệch trung bình {ai_diff:,.0f} VNĐ).")
    elif ai_diff <= 1000:
        insight_parts.append(" Hai mô hình AI bóc tách đồng thuận cao.")

    # 2. So sánh với CẢ 2 LOẠI Ground Truth
    rob_price = gt_prices["robusta"]
    ara_price = gt_prices["arabica"]

    if rob_price and ara_price:
        # Tính khoảng cách từ giá báo chí tới 2 mốc thực tế
        diff_rob = abs(avg_dl - rob_price)
        diff_ara = abs(avg_dl - ara_price)

        # Đoán loại cà phê dựa trên khoảng cách ngắn hơn
        if diff_rob < diff_ara:
            closest_type = "Robusta"
            real_price = rob_price
            diff_value = avg_dl - rob_price
        else:
            closest_type = "Arabica"
            real_price = ara_price
            diff_value = avg_dl - ara_price

        insight_parts.append(f"Dựa trên khoảng giá, báo chí đang tập trung đưa tin về cà phê {closest_type} (Giá thực tế: {real_price:,.0f} VNĐ).")

        # Đánh giá độ chênh lệch
        if abs(diff_value) <= 1500:
            insight_parts.append("Tin tức bám rất sát với diễn biến thực tế của thị trường.")
        elif diff_value > 1500:
            insight_parts.append(f" Truyền thông đang đưa tin CAO HƠN thực tế khoảng {abs(diff_value):,.0f} VNĐ/kg.")
        else:
            insight_parts.append(f" Truyền thông đang đưa tin THẤP HƠN thực tế khoảng {abs(diff_value):,.0f} VNĐ/kg.")
            
    elif rob_price or ara_price: # Trường hợp chỉ có 1 trong 2 giá
        avail_type = "Robusta" if rob_price else "Arabica"
        real_price = rob_price if rob_price else ara_price
        diff_value = avg_dl - real_price
        
        insight_parts.append(f"Đối chiếu với Ground Truth của {avail_type}:")
        if abs(diff_value) <= 1500:
            insight_parts.append("Giá trên báo chí bám sát giá thực tế.")
        else:
            direction = "CAO HƠN" if diff_value > 0 else "THẤP HƠN"
            insight_parts.append(f"Báo chí đưa tin {direction} thực tế khoảng {abs(diff_value):,.0f} VNĐ/kg.")
    else:
        insight_parts.append("Chưa có dữ liệu Ground Truth của ngày này để đối chiếu độ chính xác.")

    return " ".join(insight_parts)

# ==========================================
# 5. API ENDPOINTS CHÍNH
# ==========================================
@app.get("/api/v1/coffee-prices", response_model=SearchResponse)
def search_coffee_prices(query_date: str = Query(..., description="Ngày tìm kiếm định dạng YYYY-MM-DD")):
    if not os.path.exists(NEWS_DATA_PATH):
        raise HTTPException(status_code=500, detail="Không tìm thấy file dữ liệu final_enriched_dataset.csv")

    try:
        df = pd.read_csv(NEWS_DATA_PATH)
        df = df.fillna("")
        df_filtered = df[df['date'] == query_date]

        if df_filtered.empty:
            raise HTTPException(status_code=404, detail=f"Không tìm thấy bản tin nào trong ngày {query_date}.")

        news_list = df_filtered.to_dict(orient="records")

        # Lấy CẢ 2 Ground Truth và sinh nhận định
        gt_prices = get_dual_ground_truth(query_date)
        market_insight = generate_market_insight(news_list, gt_prices)

        return {
            "market_insight": market_insight,
            "data": news_list
        }

    except HTTPException:
        raise
    except Exception as e:
        print(f"Lỗi Server: {e}")
        raise HTTPException(status_code=500, detail=f"Lỗi xử lý dữ liệu nội bộ: {str(e)}")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="127.0.0.1", port=8000, reload=True)