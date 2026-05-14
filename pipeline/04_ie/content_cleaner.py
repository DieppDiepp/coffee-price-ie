"""
content_cleaner.py — Smart truncation: giữ paragraphs liên quan cà phê, loại noise.
"""
import re
from extraction_config import DEFAULT_MAX_CHARS

# ── Noise: nav menus, footer, stock tickers, weather, ads ──
RE_NOISE = re.compile(
    r"hotline|thời tiết.{0,5}\d+°|VNI:|HNX:|UPCOM|VN30:|đóng cửa|"
    r"xem thêm|bình luận|đăng nhập|đăng ký|quảng cáo|"
    r"google play|app store|trang chủ|liên hệ chúng tôi|"
    r"bản quyền|copyright|cookie|chính sách bảo mật|"
    r"youtube|facebook|twitter|instagram|tiktok|"
    r"tin cùng chuyên mục|tin liên quan|bài viết khác|đọc thêm|tags?:|"
    r"theo dõi chúng tôi|tải ứng dụng|"
    r"VOV\d|nhảy đến nội dung",
    re.IGNORECASE,
)

# ── Keyword weights ──
KW_HIGH = ["giá cà phê", "cà phê robusta", "cà phê arabica", "đồng/kg"]    # +3
KW_MED  = ["cà phê", "robusta", "arabica"]                                   # +2
KW_LOW  = ["tăng", "giảm", "ổn định", "đi ngang",
           "Đắk Lắk", "Lâm Đồng", "Tây Nguyên",
           "Gia Lai", "Đắk Nông", "thị trường", "xuất khẩu"]                # +1

RE_PRICE = re.compile(
    r"\d{2,3}[.,]\d{3}\s*(?:đồng|VNĐ|VND|đ/kg|đồng/kg)", re.IGNORECASE)    # +3


def smart_truncate(content, max_chars=DEFAULT_MAX_CHARS):
    """
    Trích paragraphs liên quan nhất đến giá cà phê.

    1. Tách thành paragraphs (>20 ký tự)
    2. Loại dòng noise (nav, footer, stock tickers)
    3. Chấm điểm keyword: HIGH=+3, MED=+2, LOW=+1, giá VND=+3
    4. Lấy top paragraphs cho đến max_chars
    """
    if not content or len(content) < 50:
        return content or ""

    paragraphs = [p.strip() for p in content.split("\n") if len(p.strip()) > 20]

    scored = []
    for para in paragraphs:
        if RE_NOISE.search(para):
            continue
        pl = para.lower()
        score = 0
        score += sum(3 for kw in KW_HIGH if kw.lower() in pl)
        score += sum(2 for kw in KW_MED  if kw.lower() in pl)
        score += sum(1 for kw in KW_LOW  if kw.lower() in pl)
        if RE_PRICE.search(para):
            score += 3
        if score > 0:
            scored.append((score, para))

    if not scored:
        # Fallback: đầu bài thường chứa thông tin chính
        return content[:max_chars]

    scored.sort(key=lambda x: -x[0])

    result, total_len = [], 0
    for _, para in scored:
        if total_len + len(para) > max_chars:
            remaining = max_chars - total_len
            if remaining > 100:
                result.append(para[:remaining])
            break
        result.append(para)
        total_len += len(para)

    return "\n".join(result)
