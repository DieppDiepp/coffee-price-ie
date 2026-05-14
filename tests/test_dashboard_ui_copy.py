from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_streamlit_dashboard_runtime_was_removed():
    assert not (ROOT / "dashboard" / "app.py").exists()


def test_react_dashboard_uses_vietnamese_copy_and_motion():
    app_source = (ROOT / "frontend" / "src" / "App.tsx").read_text(encoding="utf-8")
    chart_source = (ROOT / "frontend" / "src" / "chartModel.ts").read_text(encoding="utf-8")
    style_source = (ROOT / "frontend" / "src" / "styles.css").read_text(encoding="utf-8")

    assert "Dashboard Mô Hình" in app_source
    assert "Hệ thống dự đoán giá cà phê ngày kế tiếp" in app_source
    assert "Dự đoán bằng ML" in app_source
    assert "Gọi Gemini dự đoán" in app_source
    assert "Ngày dự đoán" in app_source
    assert "Giá ngày trước đó" in app_source
    assert "Ground truth ngày dự đoán" in app_source
    assert "Phạm vi train" in app_source
    assert "Tập validation" in app_source
    assert "Tập test" in app_source
    assert "Dữ liệu xung quanh ngày dự đoán" in app_source
    assert ".control-deck" in style_source
    assert ".control-grid" in style_source
    assert "align-items: start;" in style_source
    assert "align-content: start;" in style_source
    assert "align-self: start;" in style_source
    assert "Giải thích Gemini" in app_source
    assert "Input Gemini" in app_source
    assert "Output Gemini" in app_source
    assert "Chú thích biểu đồ" in app_source
    assert "Giá lịch sử đến ngày trước đó" in app_source
    assert "ML dự đoán" in chart_source
    assert "Gemini dự đoán" in chart_source
    assert "Đầu vào mô hình tại ngày trước đó" in app_source
    assert "giá trị đầu vào model nhận tại ngày trước đó" in app_source
    assert "không phải mức ảnh hưởng nhân quả" in app_source
    assert "Ground truth" in app_source
    assert "@keyframes riseIn" in style_source
    assert "@keyframes chartSweep" in style_source
