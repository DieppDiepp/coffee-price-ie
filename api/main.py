from __future__ import annotations

import re
from pathlib import Path

import pandas as pd
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware

from api.schemas import GeminiRequest
from api.services import (
    gemini_prediction_response,
    metadata_response,
    prediction_response,
)
from dashboard.data_loader import COFFEE_TYPES, FEATURE_VERSIONS

_PROJECT_ROOT = Path(__file__).resolve().parents[1]
_NEWS_DATA_PATH = _PROJECT_ROOT / "data" / "html" / "final_enriched_dataset.csv"
_ROBUSTA_GT_PATH = _PROJECT_ROOT / "data" / "06_ground_truth" / "Investing" / "robusta.csv"
_ARABICA_GT_PATH = _PROJECT_ROOT / "data" / "06_ground_truth" / "Investing" / "arabica.csv"


def _clean_price(price_str: str) -> int:
    try:
        return int(re.sub(r"[^\d]", "", str(price_str))) or 0
    except Exception:
        return 0


def _fetch_gt_price(file_path: Path, query_date: str) -> int | None:
    if not file_path.exists():
        return None
    try:
        df = pd.read_csv(file_path)
        df["Date"] = pd.to_datetime(df["Date"]).dt.strftime("%Y-%m-%d")
        row = df[df["Date"] == query_date]
        if not row.empty:
            price_col = "Gia_Viet_Nam" if "Gia_Viet_Nam" in df.columns else "Price"
            return int(round(float(row.iloc[0][price_col])))
    except Exception:
        pass
    return None


def _market_insight(news_data: list, gt: dict) -> str:
    dl_prices = [_clean_price(item["price_dl"]) for item in news_data if _clean_price(item["price_dl"]) > 0]
    llm_prices = [_clean_price(item["price_llm"]) for item in news_data if _clean_price(item["price_llm"]) > 0]
    if not dl_prices or not llm_prices:
        return "Dữ liệu giá bóc tách không đủ để phân tích thống kê."

    avg_dl = sum(dl_prices) / len(dl_prices)
    avg_llm = sum(llm_prices) / len(llm_prices)
    parts: list[str] = []

    ai_diff = abs(avg_llm - avg_dl)
    if ai_diff > 3000:
        parts.append(f"Các mô hình AI bất đồng lớn (lệch trung bình {ai_diff:,.0f} VNĐ).")
    elif ai_diff > 1000:
        parts.append(f"Hai mô hình AI có chênh lệch nhẹ (lệch trung bình {ai_diff:,.0f} VNĐ).")
    else:
        parts.append("Hai mô hình AI bóc tách đồng thuận cao.")

    rob, ara = gt.get("robusta"), gt.get("arabica")
    if rob and ara:
        diff_rob, diff_ara = abs(avg_dl - rob), abs(avg_dl - ara)
        closest = "Robusta" if diff_rob < diff_ara else "Arabica"
        real = rob if diff_rob < diff_ara else ara
        diff_val = avg_dl - real
        parts.append(f"Báo chí đang tập trung về cà phê {closest} (Giá thực tế: {real:,.0f} VNĐ).")
        if abs(diff_val) <= 1500:
            parts.append("Tin tức bám sát thực tế thị trường.")
        elif diff_val > 0:
            parts.append(f"Truyền thông đưa tin CAO HƠN thực tế khoảng {abs(diff_val):,.0f} VNĐ/kg.")
        else:
            parts.append(f"Truyền thông đưa tin THẤP HƠN thực tế khoảng {abs(diff_val):,.0f} VNĐ/kg.")
    else:
        parts.append("Chưa có đủ dữ liệu Ground Truth để đối chiếu.")

    return " ".join(parts)


app = FastAPI(
    title="Coffee Model Dashboard API",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/api/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/api/metadata")
def get_metadata():
    try:
        return metadata_response()
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@app.get("/api/prediction")
def get_prediction(
    coffee_type: str = Query(..., pattern="^(robusta|arabica)$"),
    feature_version: str = Query(..., pattern="^(v1|v2|v3_1|v3_2|v4_1|v4_2|v5)$"),
    date: str = Query(...),
    model_key: str | None = Query(None),
):
    if coffee_type not in COFFEE_TYPES or feature_version not in FEATURE_VERSIONS:
        raise HTTPException(status_code=400, detail="Unsupported coffee type or feature version")
    try:
        return prediction_response(coffee_type, feature_version, date, model_key)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@app.get("/api/v1/coffee-prices")
def get_coffee_prices(query_date: str = Query(..., description="YYYY-MM-DD")):
    if not _NEWS_DATA_PATH.exists():
        raise HTTPException(
            status_code=503,
            detail=(
                "File dữ liệu final_enriched_dataset.csv chưa có. "
                f"Hãy đặt file vào: {_NEWS_DATA_PATH}"
            ),
        )
    try:
        df = pd.read_csv(_NEWS_DATA_PATH).fillna("")
        df_day = df[df["date"] == query_date]
        if df_day.empty:
            raise HTTPException(status_code=404, detail=f"Không tìm thấy bản tin nào trong ngày {query_date}.")
        news_list = df_day.to_dict(orient="records")
        gt = {
            "robusta": _fetch_gt_price(_ROBUSTA_GT_PATH, query_date),
            "arabica": _fetch_gt_price(_ARABICA_GT_PATH, query_date),
        }
        return {"market_insight": _market_insight(news_list, gt), "data": news_list}
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@app.post("/api/gemini")
def post_gemini(request: GeminiRequest):
    if request.coffee_type not in COFFEE_TYPES or request.feature_version not in FEATURE_VERSIONS:
        raise HTTPException(status_code=400, detail="Unsupported coffee type or feature version")
    try:
        return gemini_prediction_response(
            request.coffee_type,
            request.feature_version,
            request.date,
            request.model_key,
        )
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc
