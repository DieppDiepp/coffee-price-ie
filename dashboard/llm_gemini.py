from __future__ import annotations

import json
import os
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any


DEFAULT_GEMINI_MODEL = "gemini-2.5-flash"
PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_DOTENV_PATH = PROJECT_ROOT / ".env"


@dataclass(frozen=True)
class GeminiPrediction:
    predicted_next_price: float
    predicted_direction: str
    confidence: float
    rationale: str
    raw_response: str


@dataclass(frozen=True)
class GeminiResult:
    available: bool
    prediction: GeminiPrediction | None = None
    error: str | None = None


@dataclass(frozen=True)
class GeminiClientConfig:
    use_vertex_ai: bool
    project: str | None = None
    location: str | None = None
    api_key: str | None = None


def build_gemini_prompt_from_articles(
    coffee_type: str,
    articles: list[dict[str, Any]],
    current_price: float,
    prediction_date: str,
) -> str:
    low_bound = round(current_price * 0.85 / 1000) * 1000
    high_bound = round(current_price * 1.15 / 1000) * 1000

    if not articles:
        articles_text = "Không có bài báo nào trong khoảng thời gian này."
    else:
        from collections import defaultdict
        date_groups: dict[str, list[dict[str, Any]]] = defaultdict(list)
        for art in articles:
            date_groups[str(art.get("date", ""))].append(art)

        parts: list[str] = []
        for day_date in sorted(date_groups.keys(), reverse=True):
            parts.append(f"=== Ngày {day_date} ===")
            for i, art in enumerate(date_groups[day_date], 1):
                snippet = (art.get("content_snippet") or "").strip()
                if len(snippet) > 350:
                    snippet = snippet[:350] + "..."
                line = f"  [{i}] Nguồn: {art.get('domain', 'N/A')}"
                if snippet:
                    line += f"\n      Nội dung: {snippet}"
                price_dl = str(art.get("price_dl", "")).strip()
                price_llm = str(art.get("price_llm", "")).strip()
                if price_dl and price_dl not in ("", "0"):
                    line += f"\n      Giá DL: {price_dl} VNĐ/kg"
                if price_llm and price_llm not in ("", "0"):
                    line += f"\n      Giá LLM: {price_llm} VNĐ/kg"
                parts.append(line)
        articles_text = "\n".join(parts)

    return f"""Bạn là chuyên gia dự báo giá cà phê Việt Nam. CHỈ sử dụng thông tin từ các bài báo được cung cấp dưới đây, không dựa vào kiến thức nền tảng khác.

--- THÔNG TIN ĐẦU VÀO ---
Loại cà phê: {coffee_type}
Ngày dự báo: {prediction_date}
Giá hiện tại: {current_price:,.0f} VNĐ/kg
Khoảng giá hợp lệ (±15%): {low_bound:,.0f} – {high_bound:,.0f} VNĐ/kg

--- TIN TỨC GẦN ĐÂY (MỚI NHẤT TRƯỚC) ---
{articles_text}

--- YÊU CẦU SUY LUẬN ---
Thực hiện theo 3 bước:
Bước 1 – Nhận diện xu hướng: Tóm tắt tín hiệu giá từ các bài báo (tăng/giảm/đi ngang).
Bước 2 – Đánh giá độ chắc chắn: Các bài báo có đồng thuận không? Biến động ra sao?
Bước 3 – Đưa ra dự báo: Xác định giá trong khoảng {low_bound:,.0f}–{high_bound:,.0f} VNĐ/kg.

QUAN TRỌNG: predicted_next_price PHẢI nằm trong [{low_bound:.0f}, {high_bound:.0f}]. Nếu tin tức không đủ, giữ nguyên giá hiện tại.

Chỉ trả về JSON hợp lệ, không thêm bất kỳ nội dung nào ngoài JSON:
{{
  "predicted_next_price": <số thực trong [{low_bound:.0f}, {high_bound:.0f}]>,
  "predicted_direction": "UP" | "DOWN",
  "confidence": <số thực từ 0.0 đến 1.0>,
  "rationale": "<1-2 câu, trích dẫn tên nguồn bài báo cụ thể đã dùng>"
}}""".strip()


def parse_gemini_response(response_text: str) -> GeminiPrediction:
    payload = extract_json_payload(response_text)
    data = json.loads(payload)

    predicted_next_price = float(data["predicted_next_price"])
    predicted_direction = str(data["predicted_direction"]).strip().upper()
    if predicted_direction not in {"UP", "DOWN"}:
        raise ValueError(f"Invalid predicted_direction: {predicted_direction!r}")

    confidence = float(data.get("confidence", 0.0))
    if confidence > 1.0:
        confidence = confidence / 100.0
    confidence = min(max(confidence, 0.0), 1.0)

    rationale = str(data.get("rationale", "")).strip()
    return GeminiPrediction(
        predicted_next_price=predicted_next_price,
        predicted_direction=predicted_direction,
        confidence=confidence,
        rationale=rationale,
        raw_response=response_text,
    )


def extract_json_payload(response_text: str) -> str:
    fenced = re.search(r"```(?:json)?\s*(.*?)\s*```", response_text, flags=re.IGNORECASE | re.DOTALL)
    if fenced:
        return fenced.group(1).strip()

    object_match = re.search(r"\{.*\}", response_text, flags=re.DOTALL)
    if object_match:
        return object_match.group(0).strip()

    return response_text.strip()


def predict_with_gemini(
    prompt: str,
    api_key: str | None = None,
    model: str = DEFAULT_GEMINI_MODEL,
) -> GeminiResult:
    config = resolve_gemini_client_config(api_key=api_key)
    if not config.use_vertex_ai and not config.api_key:
        return GeminiResult(
            available=False,
            error=(
                "Missing Vertex AI configuration. Set GOOGLE_GENAI_USE_VERTEXAI=true, "
                "GOOGLE_CLOUD_PROJECT, GOOGLE_CLOUD_LOCATION and login with gcloud ADC. "
                "Alternatively set GEMINI_API_KEY for the Gemini Developer API."
            ),
        )
    if config.use_vertex_ai and (not config.project or not config.location):
        return GeminiResult(
            available=False,
            error="Missing GOOGLE_CLOUD_PROJECT or GOOGLE_CLOUD_LOCATION for Vertex AI Gemini.",
        )

    try:
        from google import genai

        if config.use_vertex_ai:
            client = genai.Client(
                vertexai=True,
                project=config.project,
                location=config.location,
            )
        else:
            client = genai.Client(api_key=config.api_key)
        response = client.models.generate_content(model=model, contents=prompt)
        prediction = parse_gemini_response(response.text or "")
        return GeminiResult(available=True, prediction=prediction)
    except Exception as exc:  # pragma: no cover - network and SDK failures vary.
        return GeminiResult(available=False, error=f"Gemini request failed: {exc}")


def resolve_gemini_client_config(api_key: str | None = None) -> GeminiClientConfig:
    load_environment()
    use_vertex_ai = env_flag("GOOGLE_GENAI_USE_VERTEXAI")
    if use_vertex_ai:
        return GeminiClientConfig(
            use_vertex_ai=True,
            project=os.getenv("GOOGLE_CLOUD_PROJECT"),
            location=os.getenv("GOOGLE_CLOUD_LOCATION") or os.getenv("GOOGLE_VERTEX_LOCATION"),
            api_key=None,
        )

    resolved_api_key = api_key or os.getenv("GEMINI_API_KEY")
    return GeminiClientConfig(
        use_vertex_ai=False,
        api_key=resolved_api_key,
    )


def env_flag(name: str) -> bool:
    return os.getenv(name, "").strip().lower() in {"1", "true", "yes", "on"}


def load_environment(dotenv_path: Path | str | None = None) -> None:
    try:
        from dotenv import load_dotenv
    except ImportError:  # pragma: no cover - dependency is declared.
        return

    dotenv_path = dotenv_path or DEFAULT_DOTENV_PATH
    load_dotenv(dotenv_path=dotenv_path, override=False)
