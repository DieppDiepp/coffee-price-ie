import json

from dashboard.model_registry import load_checkpoint_model


def test_missing_checkpoint_artifact_returns_none_so_fallback_can_run(tmp_path):
    registry_path = tmp_path / "model_registry.json"
    registry_path.write_text(
        json.dumps(
            {
                "robusta.selected": {
                    "model_name": "Missing checkpoint",
                    "model_path": "missing/model.pkl",
                    "scaler_path": "missing/scaler.pkl",
                    "feature_columns": ["Gia_Viet_Nam"],
                    "metrics": {},
                }
            }
        ),
        encoding="utf-8",
    )

    assert load_checkpoint_model("robusta", "selected", registry_path) is None
