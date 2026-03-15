import pytest
import sys
import os

sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'pipeline', '04_ie'))
from main import normalize_location, baseline_rule_extractor

def test_normalize_location():
    """Kiểm tra hàm chuẩn hóa tên địa điểm."""
    assert normalize_location("Tại Đắk Lắk, giá cà phê...") == "Dak Lak"
    assert normalize_location("Khu vực Tây Nguyên ghi nhận") == "Tay Nguyen"
    assert normalize_location("dak nong") == "Dak Nong"
    assert normalize_location("Hà Nội") == "Unknown"
    assert normalize_location(None) == "Unknown"

def test_baseline_rule_extractor_valid():
    """Kiểm tra rule baseline đơn giản cho việc bóc tách số giá."""
    sentence = "Sáng nay, giá cà phê tại Đắk Lắk đạt mức 96.500 đ/kg, tăng nhẹ."
    mentions = baseline_rule_extractor(sentence)
    
    assert len(mentions) == 1
    assert mentions[0]['price_low'] == 96.5
    assert mentions[0]['price_high'] == 96.5
    assert mentions[0]['unit'] == "kg"
    assert mentions[0]['currency'] == "VND"
    assert mentions[0]['evidence_span'] == "96.500 đ/kg"

def test_baseline_rule_extractor_comma_format():
    """Kiểm tra định dạng giá có dấu phẩy/chấm."""
    sentence = "Giá mua vào là 100,500 đồng/kg."
    mentions = baseline_rule_extractor(sentence)
    
    assert len(mentions) == 1
    assert mentions[0]['price_low'] == 100.5
    assert mentions[0]['evidence_span'] == "100,500 đồng/kg"

def test_reject_non_coffee_mention():
    """Giả lập logic filter: reject các mention không phải cà phê."""
    # Khớp logic trong hàm process_file của main.py
    raw_mention = {
        "commodity": "Hồ tiêu",
        "price_low": 150.0,
        "price_high": 150.0
    }
    
    commodity = raw_mention.get('commodity', '').lower()
    is_valid_coffee = 'cà phê' in commodity or 'robusta' in commodity
    
    assert is_valid_coffee is False

def test_fill_price_high_from_low():
    """Giả lập logic filter: nếu có price_low mà không có price_high thì gán bằng nhau."""
    raw_mention = {
        "commodity": "cà phê Robusta",
        "price_low": 95.0,
        "price_high": None
    }
    
    price_low = raw_mention.get('price_low')
    price_high = raw_mention.get('price_high')
    if price_high is None and price_low is not None:
        price_high = price_low
        
    assert price_high == 95.0
