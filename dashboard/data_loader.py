from __future__ import annotations

from pathlib import Path
from zipfile import ZipFile

import numpy as np
import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_DATA_ZIP = PROJECT_ROOT / "data" / "04_features" / "next_day_price_label.zip"
DEFAULT_GT_DIR = PROJECT_ROOT / "data" / "06_ground_truth" / "Investing"

COFFEE_TYPES = ("robusta", "arabica")
FEATURE_VERSIONS = ("original", "generated", "selected")
FEATURE_VERSION_LABELS = {
    "original": "Đặc trưng gốc",
    "generated": "Gốc + đặc trưng LLM từ tin tức",
    "selected": "Gốc + đặc trưng được chọn",
}


def expected_csv_name(coffee_type: str, feature_version: str) -> str:
    coffee_type = normalize_coffee_type(coffee_type)
    feature_version = normalize_feature_version(feature_version)
    if feature_version == "original":
        return f"{coffee_type}_original_features.csv"
    return f"{coffee_type}_original_{feature_version}_features.csv"


def normalize_coffee_type(coffee_type: str) -> str:
    value = coffee_type.strip().lower()
    if value not in COFFEE_TYPES:
        raise ValueError(f"Unsupported coffee type: {coffee_type!r}")
    return value


def normalize_feature_version(feature_version: str) -> str:
    value = feature_version.strip().lower()
    alias = {
        "original + generated": "generated",
        "original_generated": "generated",
        "original-generated": "generated",
        "original + selected": "selected",
        "original_selected": "selected",
        "original-selected": "selected",
    }
    value = alias.get(value, value)
    if value not in FEATURE_VERSIONS:
        raise ValueError(f"Unsupported feature version: {feature_version!r}")
    return value


def list_available_datasets(zip_path: Path | str = DEFAULT_DATA_ZIP) -> dict[str, dict[str, Path]]:
    zip_path = Path(zip_path)
    if not zip_path.exists():
        raise FileNotFoundError(f"Feature zip not found: {zip_path}")

    available: dict[str, dict[str, Path]] = {coffee: {} for coffee in COFFEE_TYPES}
    with ZipFile(zip_path) as archive:
        names = {Path(name).name.lower(): Path(name) for name in archive.namelist()}

    for coffee in COFFEE_TYPES:
        for version in FEATURE_VERSIONS:
            filename = expected_csv_name(coffee, version)
            if filename.lower() in names:
                available[coffee][version] = names[filename.lower()]

    return available


def load_feature_csv(
    coffee_type: str,
    feature_version: str,
    zip_path: Path | str = DEFAULT_DATA_ZIP,
) -> pd.DataFrame:
    coffee_type = normalize_coffee_type(coffee_type)
    feature_version = normalize_feature_version(feature_version)
    zip_path = Path(zip_path)
    filename = expected_csv_name(coffee_type, feature_version)

    with ZipFile(zip_path) as archive:
        matching_name = next(
            (name for name in archive.namelist() if Path(name).name.lower() == filename.lower()),
            None,
        )
        if matching_name is None:
            raise FileNotFoundError(f"{filename} not found in {zip_path}")
        with archive.open(matching_name) as csv_file:
            df = pd.read_csv(csv_file)

    return normalize_dataset_frame(df)


def normalize_dataset_frame(df: pd.DataFrame) -> pd.DataFrame:
    if "target_price" in df.columns and "target_next_day" not in df.columns:
        df = df.rename(columns={"target_price": "target_next_day"})

    required = {"date", "Gia_Viet_Nam", "target_next_day"}
    missing = required.difference(df.columns)
    if missing:
        raise ValueError(f"Dataset missing required columns: {sorted(missing)}")

    normalized = df.copy()
    normalized["date"] = parse_dates(normalized["date"])
    for column in normalized.columns:
        if column != "date":
            normalized[column] = pd.to_numeric(normalized[column], errors="coerce")

    normalized = normalized.sort_values("date").reset_index(drop=True)
    return normalized


def parse_dates(values: pd.Series) -> pd.Series:
    parsed = pd.to_datetime(values, errors="coerce")
    if parsed.isna().any():
        bad_values = values[parsed.isna()].head(5).tolist()
        raise ValueError(f"Could not parse date values: {bad_values}")
    return parsed


def load_model_dataset(
    coffee_type: str,
    feature_version: str,
    zip_path: Path | str = DEFAULT_DATA_ZIP,
    ground_truth_dir: Path | str = DEFAULT_GT_DIR,
) -> pd.DataFrame:
    df = load_feature_csv(coffee_type, feature_version, zip_path)
    return add_prediction_metadata(df, coffee_type, ground_truth_dir)


def add_prediction_metadata(
    df: pd.DataFrame,
    coffee_type: str,
    ground_truth_dir: Path | str = DEFAULT_GT_DIR,
) -> pd.DataFrame:
    coffee_type = normalize_coffee_type(coffee_type)
    enriched = normalize_dataset_frame(df)
    enriched["current_price"] = enriched["Gia_Viet_Nam"]
    enriched["actual_next_price"] = enriched["target_next_day"]
    enriched["target_date"] = enriched["date"].shift(-1)

    last_target_date = find_next_ground_truth_date(
        coffee_type=coffee_type,
        current_date=enriched.iloc[-1]["date"],
        actual_next_price=float(enriched.iloc[-1]["actual_next_price"]),
        ground_truth_dir=ground_truth_dir,
    )
    if last_target_date is not None:
        enriched.loc[enriched.index[-1], "target_date"] = last_target_date

    enriched["actual_direction"] = np.where(
        enriched["actual_next_price"] > enriched["current_price"],
        "UP",
        "DOWN",
    )
    enriched["actual_change"] = enriched["actual_next_price"] - enriched["current_price"]
    enriched["actual_change_pct"] = (
        enriched["actual_change"] / enriched["current_price"].replace(0, np.nan) * 100.0
    )
    return enriched


def find_next_ground_truth_date(
    coffee_type: str,
    current_date: pd.Timestamp,
    actual_next_price: float,
    ground_truth_dir: Path | str = DEFAULT_GT_DIR,
) -> pd.Timestamp | None:
    ground_truth_path = Path(ground_truth_dir) / f"{coffee_type}_clean.csv"
    if not ground_truth_path.exists():
        return None

    gt = pd.read_csv(ground_truth_path)
    if "date" not in gt.columns:
        return None
    gt["date"] = parse_dates(gt["date"])

    future = gt[gt["date"] > pd.Timestamp(current_date)].sort_values("date")
    if future.empty:
        return None

    if "Gia_Viet_Nam" in future.columns:
        future["Gia_Viet_Nam"] = pd.to_numeric(future["Gia_Viet_Nam"], errors="coerce")
        close_match = future[
            np.isclose(future["Gia_Viet_Nam"], actual_next_price, rtol=1e-6, atol=1e-6)
        ]
        if not close_match.empty:
            return pd.Timestamp(close_match.iloc[0]["date"])

    return pd.Timestamp(future.iloc[0]["date"])


def history_rows_for_prompt(
    df: pd.DataFrame,
    selected_date: pd.Timestamp,
    feature_columns: list[str],
    window: int = 7,
) -> list[dict[str, object]]:
    selected_date = pd.Timestamp(selected_date)
    prompt_columns = [
        column
        for column in ["date", "Gia_Viet_Nam", "close", "open", "high", "low", "Volume", "Change_pct"]
        if column in df.columns
    ]
    for column in feature_columns:
        if column not in prompt_columns and column not in {"target_next_day"}:
            prompt_columns.append(column)

    history = df[df["date"] <= selected_date].tail(window).copy()
    history = history[prompt_columns]
    history["date"] = history["date"].dt.strftime("%Y-%m-%d")
    return history.replace({np.nan: None}).to_dict(orient="records")
