import pytest
from bs4 import BeautifulSoup

# Giả định chúng ta import các hàm từ pipeline.03_parser.main
# Do chưa setup thành package chuẩn, chúng ta import trực tiếp hoặc copy logic để test
import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'pipeline', '03_parser'))
from main import flatten_tables, extract_text, is_candidate

def test_flatten_tables():
    """Kiểm tra khả năng trải phẳng bảng (table flattening) thành pseudo-sentences."""
    html_with_table = """
    <html>
        <body>
            <p>Giá cà phê hôm nay</p>
            <table>
                <tr><th>Tỉnh</th><th>Giá</th><th>Biến động</th></tr>
                <tr><td>Đắk Lắk</td><td>96.000 đ/kg</td><td>Tăng 500 đ</td></tr>
                <tr><td>Gia Lai</td><td>95.500 đ/kg</td><td>Ổn định</td></tr>
            </table>
        </body>
    </html>
    """
    flattened = flatten_tables(html_with_table)
    
    assert "Tỉnh | Giá | Biến động" in flattened
    assert "Đắk Lắk | 96.000 đ/kg | Tăng 500 đ" in flattened
    assert "Giá cà phê hôm nay" in flattened

def test_extract_text_fallback():
    """Kiểm tra việc tự động chuyển sang bs4_fallback khi có table."""
    html_with_table = "<html><body><table><tr><td>Đắk Lắk</td><td>96.000</td></tr></table></body></html>"
    raw_text, parser_method, has_table = extract_text(html_with_table)
    
    assert has_table is True
    assert parser_method == "trafilatura+bs4_fallback"
    assert "Đắk Lắk | 96.000" in raw_text

def test_is_candidate_valid():
    """Kiểm tra việc lọc câu candidate chuẩn xác."""
    signals = {
        "coffee": ["cà phê", "robusta", "đắk lắk"],
        "price": ["đ/kg", "tăng"],
        "hard_negative": ["hồ tiêu", "cao su"]
    }
    
    # Câu hợp lệ
    valid, flags = is_candidate("Giá cà phê tại Đắk Lắk hôm nay là 96.000 đ/kg.", signals)
    assert valid is True
    assert len(flags) == 0
    
    # Câu thiếu giá
    valid, flags = is_candidate("Hôm nay, thu hoạch cà phê tại Đắk Lắk bắt đầu.", signals)
    assert valid is False
    
    # Câu chứa hàng hóa khác (mixed_commodity)
    valid, flags = is_candidate("Giá cà phê 96.000 đ/kg, trong khi giá hồ tiêu tăng mạnh.", signals)
    assert valid is True
    assert "mixed_commodity" in flags

def test_is_candidate_invalid_noise():
    """Kiểm tra câu hoàn toàn không liên quan."""
    signals = {
        "coffee": ["cà phê", "robusta"],
        "price": ["đ/kg", "đồng/kg"],
        "hard_negative": ["hồ tiêu", "cao su"]
    }
    
    valid, flags = is_candidate("Giá vàng hôm nay tăng mạnh lên 80 triệu đồng/lượng.", signals)
    assert valid is False
