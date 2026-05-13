from fastapi import FastAPI, HTTPException, Query
from pydantic import BaseModel
import pandas as pd
from typing import List, Optional
from fastapi.middleware.cors import CORSMiddleware

# Khởi tạo ứng dụng FastAPI
app = FastAPI(
    title="Coffee Finance API",
    description="Hệ thống tra cứu giá cà phê nội địa dựa trên tin tức (News-driven Pricing)",
    version="1.0.0"
)
origins = [
    "http://localhost:5173",     # Địa chỉ Frontend React/Vite của bạn
    "http://127.0.0.1:5173",     # Đề phòng trường hợp gọi bằng IP local
    "http://localhost:3000",     # Dự phòng
]

# 3. Kích hoạt Middleware cấp quyền
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],         # Cho phép TẤT CẢ các domain gọi API
    allow_credentials=True,
    allow_methods=["*"],         # Cho phép TẤT CẢ các method (GET, POST, OPTIONS...)
    allow_headers=["*"],         # Cho phép TẤT CẢ các headers
)

# Biến toàn cục lưu trữ dữ liệu
df_coffee = pd.DataFrame()

# Khai báo Schema (Cấu trúc dữ liệu trả về) giúp API rõ ràng và chuẩn mực
class CoffeePriceRecord(BaseModel):
    date: str
    region: str
    exact_price: str
    target: str
    domain: str
    url: str
    content_snippet: str

# Sự kiện chạy khi khởi động server: Load Data vào RAM để truy vấn siêu tốc
@app.on_event("startup")
def load_data():
    global df_coffee
    try:
        # Nhớ thay đổi tên file cho khớp với file thực tế của bạn
        file_path = "../../data/html/coffee_master_dataset.csv" 
        df_coffee = pd.read_csv(file_path)
        
        # Đảm bảo cột date ở định dạng chuỗi YYYY-MM-DD để dễ so sánh
        df_coffee['date'] = pd.to_datetime(df_coffee['date']).dt.strftime('%Y-%m-%d')
        
        # Điền các giá trị NaN bằng chuỗi rỗng để tránh lỗi parse JSON
        df_coffee = df_coffee.fillna("")
        print(f"Đã load thành công {len(df_coffee)} bản ghi vào hệ thống!")
    except Exception as e:
        print(f"Lỗi khi load dữ liệu: {e}")

# API Endpoint: Tra cứu giá cà phê theo ngày
@app.get("/api/v1/coffee-prices", response_model=List[CoffeePriceRecord])
def get_prices_by_date(
    query_date: str = Query(..., description="Ngày cần tra cứu theo định dạng YYYY-MM-DD. VD: 2023-10-21")
):
    global df_coffee
    
    if df_coffee.empty:
        raise HTTPException(status_code=500, detail="Dữ liệu chưa được tải vào hệ thống.")
    
    # Lọc dữ liệu theo ngày người dùng nhập
    filtered_data = df_coffee[df_coffee['date'] == query_date]
    
    # Nếu không tìm thấy dữ liệu trong ngày đó
    if filtered_data.empty:
        raise HTTPException(
            status_code=404, 
            detail=f"Không tìm thấy dữ liệu báo cáo giá cà phê cho ngày {query_date}"
        )
    
    # Chuyển đổi Dataframe đã lọc thành danh sách các Dictionary
    # orient="records" biến mỗi dòng thành 1 object JSON
    results = filtered_data.to_dict(orient="records")
    
    return results