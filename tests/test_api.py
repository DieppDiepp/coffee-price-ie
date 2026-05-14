from fastapi.testclient import TestClient

import api.services
from api.main import app
from dashboard.llm_gemini import GeminiPrediction, GeminiResult


client = TestClient(app)


def test_metadata_endpoint_returns_dashboard_options():
    response = client.get("/api/metadata")

    assert response.status_code == 200
    payload = response.json()
    assert payload["coffee_types"][0]["value"] == "robusta"
    assert payload["coffee_types"][0]["label"] == "Robusta"
    assert {item["value"] for item in payload["feature_versions"]} == {
        "original",
        "generated",
        "selected",
    }
    assert "robusta" in payload["available_dates"]
    assert "selected" in payload["available_dates"]["robusta"]
    assert payload["available_dates"]["robusta"]["selected"]
    assert payload["available_dates"]["robusta"]["selected"][0] == "2025-10-01"
    assert payload["available_dates"]["robusta"]["selected"][-1] == "2026-03-10"
    assert "2025-09-30" not in payload["available_dates"]["robusta"]["selected"]
    split = payload["dataset_split"]["robusta"]["selected"]
    assert split["train"] == {
        "start_date": "2023-03-29",
        "end_date": "2025-04-23",
        "count": 519,
    }
    assert split["validation"] == {
        "start_date": "2025-04-24",
        "end_date": "2025-09-30",
        "count": 111,
    }
    assert split["test"] == {
        "start_date": "2025-10-01",
        "end_date": "2026-03-10",
        "count": 112,
    }
    assert split["selected_date_scope"] == "test"
    assert payload["available_models"]["robusta"]["selected"][0]["key"] == "lasso"
    assert payload["available_models"]["robusta"]["selected"][0]["is_recommended"] is True
    assert "(Recommend)" in payload["available_models"]["robusta"]["selected"][0]["label"]
    assert payload["available_models"]["robusta"]["selected"][0]["model_name"] == "Lasso"
    assert any(
        item["key"] == "ridge"
        for item in payload["available_models"]["robusta"]["selected"]
    )
    original_model_keys = [
        item["key"]
        for item in payload["available_models"]["robusta"]["original"]
    ]
    assert original_model_keys[0].startswith("fallback_")
    assert {
        "fallback_ridge",
        "fallback_random_forest",
        "fallback_svr",
    }.issubset(original_model_keys)
    assert sum(
        item["is_recommended"]
        for item in payload["available_models"]["robusta"]["original"]
    ) == 1


def test_prediction_endpoint_returns_ml_ground_truth_chart_and_versions():
    response = client.get(
        "/api/prediction",
        params={
            "coffee_type": "robusta",
            "feature_version": "selected",
            "date": "2026-03-10",
            "model_key": "ridge",
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["selection"]["coffee_type"] == "robusta"
    assert payload["selection"]["feature_version"] == "selected"
    assert payload["selection"]["model_key"] == "ridge"
    assert payload["selection"]["date"] == "2026-03-10"
    assert payload["selection"]["reference_date"] == "2026-03-09"
    assert "target_date" not in payload["selection"]
    assert payload["dataset_split"]["selected_date_scope"] == "test"
    assert payload["dataset_split"]["train"]["end_date"] == "2025-04-23"
    assert payload["dataset_split"]["test"]["start_date"] == "2025-10-01"
    assert round(payload["current_price"], 2) == 99064.17
    assert round(payload["ground_truth"]["actual_next_price"], 2) == 96988.84
    assert payload["ml_prediction"]["predicted_price"] > 0
    assert payload["ml_prediction"]["predicted_direction"] in {"UP", "DOWN"}
    assert isinstance(payload["ml_prediction"]["direction_correct"], bool)
    assert payload["model"]["source"] in {"fallback", "checkpoint"}
    assert payload["model"]["key"] == "ridge"
    assert payload["model"]["name"] == "Ridge"
    assert payload["model"]["is_recommended"] is False
    assert len(payload["chart"]) >= 10
    prediction_day_point = next(
        point for point in payload["chart"] if point["date"] == "2026-03-10"
    )
    assert prediction_day_point["price"] is None
    assert prediction_day_point["selected"] is True
    reference_day_point = next(
        point for point in payload["chart"] if point["date"] == "2026-03-09"
    )
    assert round(reference_day_point["price"], 2) == 99064.17
    assert payload["surrounding_rows"]
    assert any(
        row["role"] == "reference_day" and row["date"] == "2026-03-09"
        for row in payload["surrounding_rows"]
    )
    assert any(
        row["role"] == "prediction_day" and row["date"] == "2026-03-10"
        for row in payload["surrounding_rows"]
    )
    assert payload["version_comparison"]
    assert all(
        not item["model_name"].startswith("Kaggle ")
        for item in payload["version_comparison"]
    )
    assert payload["feature_snapshot"]


def test_prediction_endpoint_defaults_to_recommended_model():
    response = client.get(
        "/api/prediction",
        params={
            "coffee_type": "robusta",
            "feature_version": "selected",
            "date": "2026-03-10",
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["selection"]["model_key"] == "lasso"
    assert payload["model"]["key"] == "lasso"
    assert payload["model"]["is_recommended"] is True


def test_prediction_endpoint_can_select_a_fallback_candidate_model():
    response = client.get(
        "/api/prediction",
        params={
            "coffee_type": "robusta",
            "feature_version": "original",
            "date": "2026-03-10",
            "model_key": "fallback_random_forest",
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["selection"]["model_key"] == "fallback_random_forest"
    assert payload["model"]["key"] == "fallback_random_forest"
    assert payload["model"]["name"] == "Random Forest"
    assert payload["model"]["source"] == "fallback"


def test_prediction_endpoint_rejects_date_outside_test_window():
    response = client.get(
        "/api/prediction",
        params={
            "coffee_type": "robusta",
            "feature_version": "selected",
            "date": "2025-04-16",
        },
    )

    assert response.status_code == 404
    assert "test" in response.text.lower()


def test_gemini_endpoint_is_safe_when_llm_is_unavailable(monkeypatch):
    monkeypatch.setattr(
        api.services,
        "predict_with_gemini",
        lambda prompt: GeminiResult(available=False, error="Vertex AI unavailable"),
    )

    response = client.post(
        "/api/gemini",
        json={
            "coffee_type": "robusta",
            "feature_version": "selected",
            "date": "2026-03-10",
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["available"] is False
    assert "Vertex AI unavailable" in payload["error"]
    assert payload["prompt"]
    assert len(payload["input_rows"]) == 7
    assert payload["input_rows"][-1]["date"] == "2026-03-09"
    assert payload["raw_output"] is None


def test_gemini_endpoint_returns_prompt_input_rows_raw_output_and_rationale(monkeypatch):
    monkeypatch.setattr(
        api.services,
        "predict_with_gemini",
        lambda prompt: GeminiResult(
            available=True,
            prediction=GeminiPrediction(
                predicted_next_price=97000.0,
                predicted_direction="UP",
                confidence=0.73,
                rationale="Giá đang hồi phục từ vùng giảm gần nhất.",
                raw_response='{"predicted_next_price":97000,"predicted_direction":"UP","confidence":0.73,"rationale":"Giá đang hồi phục từ vùng giảm gần nhất."}',
            ),
        ),
    )

    response = client.post(
        "/api/gemini",
        json={
            "coffee_type": "robusta",
            "feature_version": "selected",
            "date": "2026-03-10",
            "model_key": "ridge",
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["available"] is True
    assert payload["prompt"]
    assert len(payload["input_rows"]) == 7
    assert payload["input_rows"][-1]["date"] == "2026-03-09"
    assert payload["raw_output"]
    assert payload["rationale"] == "Giá đang hồi phục từ vùng giảm gần nhất."
    assert payload["predicted_price"] == 97000.0


def test_gemini_endpoint_rejects_date_outside_test_window():
    response = client.post(
        "/api/gemini",
        json={
            "coffee_type": "robusta",
            "feature_version": "selected",
            "date": "2025-04-16",
        },
    )

    assert response.status_code == 404
    assert "test" in response.text.lower()
