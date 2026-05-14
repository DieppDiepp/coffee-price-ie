from pathlib import Path

import pandas as pd

from dashboard.data_loader import (
    FEATURE_VERSIONS,
    add_prediction_metadata,
    list_available_datasets,
    load_model_dataset,
)


ROOT = Path(__file__).resolve().parents[1]
ZIP_PATH = ROOT / "data" / "04_features" / "next_day_price_label.zip"
GT_DIR = ROOT / "data" / "06_ground_truth" / "Investing"


def test_list_available_datasets_reads_all_coffee_feature_versions():
    datasets = list_available_datasets(ZIP_PATH)

    assert set(datasets.keys()) == {"arabica", "robusta"}
    assert set(datasets["arabica"].keys()) == set(FEATURE_VERSIONS)
    assert set(datasets["robusta"].keys()) == set(FEATURE_VERSIONS)
    assert datasets["robusta"]["original"].name == "robusta_original_features.csv"
    assert datasets["arabica"]["generated"].name == "arabica_original_generated_features.csv"


def test_load_model_dataset_normalizes_dates_and_prediction_metadata():
    df = load_model_dataset("robusta", "original", ZIP_PATH, GT_DIR)

    assert not df.empty
    assert pd.api.types.is_datetime64_any_dtype(df["date"])
    assert pd.api.types.is_datetime64_any_dtype(df["target_date"])
    assert df["date"].is_monotonic_increasing
    assert {"current_price", "actual_next_price", "actual_direction"}.issubset(df.columns)
    assert df.iloc[0]["actual_next_price"] == df.iloc[0]["target_next_day"]
    assert df.iloc[0]["target_date"] == df.iloc[1]["date"]


def test_add_prediction_metadata_uses_ground_truth_for_last_target_date():
    df = load_model_dataset("robusta", "original", ZIP_PATH, GT_DIR)
    last = df.iloc[-1]

    assert last["date"] == pd.Timestamp("2026-03-10")
    assert last["target_date"] == pd.Timestamp("2026-03-11")
    assert last["actual_next_price"] == last["target_next_day"]
    assert last["actual_direction"] == "DOWN"


def test_add_prediction_metadata_marks_up_and_down_from_target_price():
    raw = pd.DataFrame(
        {
            "date": pd.to_datetime(["2024-01-01", "2024-01-02"]),
            "Gia_Viet_Nam": [100.0, 110.0],
            "target_next_day": [110.0, 105.0],
        }
    )

    enriched = add_prediction_metadata(raw, "robusta", GT_DIR)

    assert enriched.loc[0, "actual_direction"] == "UP"
    assert enriched.loc[1, "actual_direction"] == "DOWN"
