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


def build_gemini_prompt(
    coffee_type: str,
    feature_version: str,
    history_rows: list[dict[str, Any]],
) -> str:
    history_json = json.dumps(history_rows, ensure_ascii=False, indent=2)
    return f"""
You are forecasting Vietnamese coffee prices for a demo dashboard.

Coffee type: {coffee_type}
Feature version: {feature_version}

Use only the historical rows below. Each row is known at the selected date or before.
Predict the next trading day's Gia_Viet_Nam price and direction versus the latest
Gia_Viet_Nam value in the history.

Historical rows:
{history_json}

Return only valid JSON with this exact schema:
{{
  "predicted_next_price": number,
  "predicted_direction": "UP" | "DOWN",
  "confidence": number between 0 and 1,
  "rationale": "one short sentence"
}}
""".strip()


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
