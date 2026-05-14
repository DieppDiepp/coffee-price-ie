from pathlib import Path

import numpy as np
import pandas as pd

from dashboard.data_loader import load_model_dataset
from dashboard.modeling import (
    dataset_split_context,
    direction_from_prices,
    evaluate_prediction,
    prediction_dates_for_test_split,
    train_fallback_model,
)


ROOT = Path(__file__).resolve().parents[1]
ZIP_PATH = ROOT / "data" / "04_features" / "next_day_price_label.zip"
GT_DIR = ROOT / "data" / "06_ground_truth" / "Investing"


def test_train_fallback_model_returns_numeric_prediction_and_metrics():
    df = load_model_dataset("robusta", "original", ZIP_PATH, GT_DIR)

    result = train_fallback_model(df, candidate_names=("ridge",))
    prediction = result.predict(df.iloc[-1])

    assert result.source == "fallback"
    assert result.model_name == "Ridge"
    assert np.isfinite(prediction)
    assert result.feature_columns
    assert {"val_rmse", "test_rmse", "test_mae"}.issubset(result.metrics)
    assert result.metrics["test_rmse"] >= 0
    assert result.dataset_split is not None
    assert result.fit_row_count == result.dataset_split.train.count
    assert result.fit_row_count < (
        result.dataset_split.train.count
        + result.dataset_split.validation.count
        + result.dataset_split.test.count
    )


def test_dataset_split_context_returns_temporal_train_validation_test_ranges():
    df = load_model_dataset("robusta", "original", ZIP_PATH, GT_DIR)

    split = dataset_split_context(df)

    assert split.train.start_date == pd.Timestamp("2023-03-29")
    assert split.train.end_date == pd.Timestamp("2025-04-23")
    assert split.train.count == 519
    assert split.validation.start_date == pd.Timestamp("2025-04-24")
    assert split.validation.end_date == pd.Timestamp("2025-09-30")
    assert split.validation.count == 111
    assert split.test.start_date == pd.Timestamp("2025-10-01")
    assert split.test.end_date == pd.Timestamp("2026-03-10")
    assert split.test.count == 112


def test_test_dates_for_prediction_only_returns_test_dates():
    df = load_model_dataset("robusta", "original", ZIP_PATH, GT_DIR)

    dates = prediction_dates_for_test_split(df)

    assert dates[0] == "2025-10-01"
    assert dates[-1] == "2026-03-10"
    assert "2025-09-30" not in dates
    assert "2025-04-23" not in dates


def test_direction_and_prediction_evaluation_are_based_on_current_price():
    assert direction_from_prices(101.0, 100.0) == "UP"
    assert direction_from_prices(99.0, 100.0) == "DOWN"

    evaluation = evaluate_prediction(
        predicted_price=110.0,
        current_price=100.0,
        actual_next_price=108.0,
    )

    assert evaluation["predicted_direction"] == "UP"
    assert evaluation["actual_direction"] == "UP"
    assert evaluation["direction_correct"] is True
    assert evaluation["absolute_error"] == 2.0
    assert round(evaluation["error_pct"], 4) == round(2.0 / 108.0 * 100.0, 4)
