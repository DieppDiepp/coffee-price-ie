from dashboard.llm_gemini import (
    GeminiClientConfig,
    GeminiPrediction,
    build_gemini_prompt,
    parse_gemini_response,
    predict_with_gemini,
    resolve_gemini_client_config,
)


def test_parse_gemini_response_accepts_json_inside_markdown_fence():
    response_text = """```json
    {
      "predicted_next_price": 93337.31,
      "predicted_direction": "DOWN",
      "confidence": 0.72,
      "rationale": "Recent price and momentum are weakening."
    }
    ```"""

    prediction = parse_gemini_response(response_text)

    assert prediction == GeminiPrediction(
        predicted_next_price=93337.31,
        predicted_direction="DOWN",
        confidence=0.72,
        rationale="Recent price and momentum are weakening.",
        raw_response=response_text,
    )


def test_parse_gemini_response_normalizes_direction_and_confidence():
    response_text = '{"predicted_next_price": 120, "predicted_direction": "up", "confidence": 90, "rationale": "trend"}'

    prediction = parse_gemini_response(response_text)

    assert prediction.predicted_direction == "UP"
    assert prediction.confidence == 0.9


def test_predict_with_gemini_returns_unavailable_without_api_key(monkeypatch):
    from dashboard import llm_gemini

    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    monkeypatch.delenv("GOOGLE_GENAI_USE_VERTEXAI", raising=False)
    monkeypatch.delenv("GOOGLE_CLOUD_PROJECT", raising=False)
    monkeypatch.delenv("GOOGLE_CLOUD_LOCATION", raising=False)
    monkeypatch.delenv("GOOGLE_VERTEX_LOCATION", raising=False)
    monkeypatch.setattr(llm_gemini, "DEFAULT_DOTENV_PATH", "missing.env")

    result = predict_with_gemini("prompt", api_key=None)

    assert result.available is False
    assert result.prediction is None
    assert "Vertex AI" in result.error


def test_resolve_gemini_client_config_prefers_vertex_ai(monkeypatch):
    from dashboard import llm_gemini

    monkeypatch.setattr(llm_gemini, "DEFAULT_DOTENV_PATH", "missing.env")
    monkeypatch.setenv("GOOGLE_GENAI_USE_VERTEXAI", "true")
    monkeypatch.setenv("GOOGLE_CLOUD_PROJECT", "igot-studio")
    monkeypatch.setenv("GOOGLE_CLOUD_LOCATION", "global")
    monkeypatch.setenv("GEMINI_API_KEY", "should-not-be-used")

    config = resolve_gemini_client_config()

    assert config == GeminiClientConfig(
        use_vertex_ai=True,
        project="igot-studio",
        location="global",
        api_key=None,
    )


def test_resolve_gemini_client_config_supports_legacy_vertex_location(monkeypatch):
    from dashboard import llm_gemini

    monkeypatch.setattr(llm_gemini, "DEFAULT_DOTENV_PATH", "missing.env")
    monkeypatch.setenv("GOOGLE_GENAI_USE_VERTEXAI", "true")
    monkeypatch.setenv("GOOGLE_CLOUD_PROJECT", "igot-studio")
    monkeypatch.delenv("GOOGLE_CLOUD_LOCATION", raising=False)
    monkeypatch.setenv("GOOGLE_VERTEX_LOCATION", "asia-southeast1")

    config = resolve_gemini_client_config()

    assert config.use_vertex_ai is True
    assert config.location == "asia-southeast1"


def test_vertex_ai_config_can_be_loaded_from_dotenv_file(monkeypatch, tmp_path):
    from dashboard import llm_gemini

    env_path = tmp_path / ".env"
    env_path.write_text(
        "\n".join(
            [
                "GOOGLE_GENAI_USE_VERTEXAI=true",
                "GOOGLE_CLOUD_PROJECT=dotenv-project",
                "GOOGLE_CLOUD_LOCATION=us-central1",
            ]
        ),
        encoding="utf-8",
    )
    monkeypatch.delenv("GOOGLE_GENAI_USE_VERTEXAI", raising=False)
    monkeypatch.delenv("GOOGLE_CLOUD_PROJECT", raising=False)
    monkeypatch.delenv("GOOGLE_CLOUD_LOCATION", raising=False)
    monkeypatch.setattr(llm_gemini, "DEFAULT_DOTENV_PATH", env_path)

    config = resolve_gemini_client_config()

    assert config.use_vertex_ai is True
    assert config.project == "dotenv-project"
    assert config.location == "us-central1"


def test_build_gemini_prompt_contains_required_json_contract():
    prompt = build_gemini_prompt(
        coffee_type="robusta",
        feature_version="original",
        history_rows=[
            {"date": "2026-03-10", "Gia_Viet_Nam": 96988.84, "Change_pct": -0.01}
        ],
    )

    assert "predicted_next_price" in prompt
    assert "predicted_direction" in prompt
    assert "JSON" in prompt
    assert "robusta" in prompt
