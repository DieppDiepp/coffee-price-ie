from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Iterable

import numpy as np
import pandas as pd
from joblib import load
from sklearn.base import clone
from sklearn.ensemble import RandomForestRegressor
from sklearn.linear_model import Ridge
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler
from sklearn.svm import SVR


TARGET_COLUMN = "target_next_day"
NON_FEATURE_COLUMNS = {
    "date",
    "target_date",
    "target_next_day",
    "current_price",
    "actual_next_price",
    "actual_direction",
    "actual_change",
    "actual_change_pct",
}
DEFAULT_CANDIDATES = ("ridge", "random_forest", "svr")


@dataclass
class ModelResult:
    model_name: str
    model: Any
    feature_columns: list[str]
    metrics: dict[str, float]
    source: str = "fallback"
    scaler: Any | None = None
    model_key: str | None = None
    model_label: str | None = None
    is_recommended: bool = False
    dataset_split: DatasetSplitContext | None = None
    fit_row_count: int | None = None

    def predict(self, row: pd.Series | pd.DataFrame) -> float:
        if isinstance(row, pd.Series):
            features = row[self.feature_columns].to_frame().T
        else:
            features = row[self.feature_columns].copy()
        features = prepare_feature_matrix(features, self.feature_columns)
        if self.scaler is not None:
            features = self.scaler.transform(features)
        prediction = self.model.predict(features)
        return float(np.asarray(prediction).reshape(-1)[0])


def feature_columns_for(df: pd.DataFrame) -> list[str]:
    columns = []
    for column in df.columns:
        if column in NON_FEATURE_COLUMNS:
            continue
        if pd.api.types.is_numeric_dtype(df[column]):
            columns.append(column)
    return columns


@dataclass(frozen=True)
class SplitWindow:
    start_date: pd.Timestamp
    end_date: pd.Timestamp
    count: int


@dataclass(frozen=True)
class DatasetSplitContext:
    train: SplitWindow
    validation: SplitWindow
    test: SplitWindow


def prepare_feature_matrix(df: pd.DataFrame, feature_columns: list[str]) -> pd.DataFrame:
    matrix = df.reindex(columns=feature_columns).copy()
    for column in feature_columns:
        matrix[column] = pd.to_numeric(matrix[column], errors="coerce")
    return matrix.replace([np.inf, -np.inf], np.nan).fillna(0.0)


def clean_training_frame(df: pd.DataFrame, feature_columns: list[str]) -> tuple[pd.DataFrame, pd.Series]:
    training = clean_training_rows(df, feature_columns)
    return training[feature_columns], training[TARGET_COLUMN]


def clean_training_rows(df: pd.DataFrame, feature_columns: list[str]) -> pd.DataFrame:
    columns = list(dict.fromkeys(["date", *feature_columns, TARGET_COLUMN]))
    training = df[columns].copy()
    for column in training.columns:
        if column == "date":
            continue
        training[column] = pd.to_numeric(training[column], errors="coerce")
    training = training.replace([np.inf, -np.inf], np.nan).dropna().reset_index(drop=True)
    if len(training) < 20:
        raise ValueError("Not enough clean rows to train fallback model")
    return training


def time_series_split_bounds(
    n_rows: int,
    train_ratio: float = 0.7,
    val_ratio: float = 0.15,
) -> tuple[int, int]:
    train_end = max(int(n_rows * train_ratio), 1)
    val_end = max(train_end + int(n_rows * val_ratio), train_end + 1)
    val_end = min(val_end, n_rows - 1)
    return train_end, val_end


def time_series_split(
    X: pd.DataFrame,
    y: pd.Series,
    train_ratio: float = 0.7,
    val_ratio: float = 0.15,
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.Series, pd.Series, pd.Series]:
    n_rows = len(X)
    train_end, val_end = time_series_split_bounds(
        n_rows,
        train_ratio=train_ratio,
        val_ratio=val_ratio,
    )

    X_train = X.iloc[:train_end]
    y_train = y.iloc[:train_end]
    X_val = X.iloc[train_end:val_end]
    y_val = y.iloc[train_end:val_end]
    X_test = X.iloc[val_end:]
    y_test = y.iloc[val_end:]

    if X_val.empty or X_test.empty:
        raise ValueError("Time-series split produced an empty validation or test set")

    return X_train, X_val, X_test, y_train, y_val, y_test


def split_training_rows(
    df: pd.DataFrame,
    feature_columns: list[str] | None = None,
    train_ratio: float = 0.7,
    val_ratio: float = 0.15,
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    columns = feature_columns or feature_columns_for(df)
    training = clean_training_rows(df, columns)
    train_end, val_end = time_series_split_bounds(
        len(training),
        train_ratio=train_ratio,
        val_ratio=val_ratio,
    )

    train_rows = training.iloc[:train_end].reset_index(drop=True)
    validation_rows = training.iloc[train_end:val_end].reset_index(drop=True)
    test_rows = training.iloc[val_end:].reset_index(drop=True)

    if validation_rows.empty or test_rows.empty:
        raise ValueError("Time-series split produced an empty validation or test set")

    return train_rows, validation_rows, test_rows


def dataset_split_context(df: pd.DataFrame) -> DatasetSplitContext:
    feature_columns = feature_columns_for(df)
    train_rows, validation_rows, test_rows = split_training_rows(df, feature_columns)
    return DatasetSplitContext(
        train=split_window(train_rows),
        validation=split_window(validation_rows),
        test=split_window(test_rows),
    )


def prediction_dates_for_test_split(df: pd.DataFrame) -> list[str]:
    feature_columns = feature_columns_for(df)
    _, _, test_rows = split_training_rows(df, feature_columns)
    return test_rows["date"].dt.strftime("%Y-%m-%d").tolist()


def split_window(rows: pd.DataFrame) -> SplitWindow:
    return SplitWindow(
        start_date=pd.Timestamp(rows.iloc[0]["date"]),
        end_date=pd.Timestamp(rows.iloc[-1]["date"]),
        count=len(rows),
    )


def train_fallback_model(
    df: pd.DataFrame,
    candidate_names: Iterable[str] = DEFAULT_CANDIDATES,
    random_state: int = 42,
) -> ModelResult:
    feature_columns = feature_columns_for(df)
    train_rows, validation_rows, test_rows = split_training_rows(df, feature_columns)
    split_context = DatasetSplitContext(
        train=split_window(train_rows),
        validation=split_window(validation_rows),
        test=split_window(test_rows),
    )
    X_train = prepare_feature_matrix(train_rows[feature_columns], feature_columns)
    y_train = train_rows[TARGET_COLUMN]
    X_val = prepare_feature_matrix(validation_rows[feature_columns], feature_columns)
    y_val = validation_rows[TARGET_COLUMN]
    X_test = prepare_feature_matrix(test_rows[feature_columns], feature_columns)
    y_test = test_rows[TARGET_COLUMN]

    best_name = ""
    best_estimator = None
    best_val_metrics: dict[str, float] | None = None

    for name in candidate_names:
        display_name, estimator = build_candidate(name, random_state=random_state)
        estimator.fit(X_train, y_train)
        val_prediction = estimator.predict(X_val)
        val_metrics = regression_metrics(y_val, val_prediction, prefix="val")
        if best_val_metrics is None or val_metrics["val_rmse"] < best_val_metrics["val_rmse"]:
            best_name = display_name
            best_estimator = estimator
            best_val_metrics = val_metrics

    if best_estimator is None or best_val_metrics is None:
        raise ValueError("No candidate model was trained")

    test_prediction = best_estimator.predict(X_test)
    metrics = {
        **best_val_metrics,
        **regression_metrics(y_test, test_prediction, prefix="test"),
    }

    return ModelResult(
        model_name=best_name,
        model=best_estimator,
        feature_columns=feature_columns,
        metrics=metrics,
        source="fallback",
        model_key="fallback",
        model_label="Fallback train từ CSV",
        dataset_split=split_context,
        fit_row_count=len(X_train),
    )


def build_candidate(name: str, random_state: int = 42) -> tuple[str, Any]:
    normalized = name.strip().lower()
    if normalized == "ridge":
        return (
            "Ridge",
            Pipeline(
                [
                    ("scaler", StandardScaler()),
                    ("model", Ridge(alpha=1.0)),
                ]
            ),
        )
    if normalized == "random_forest":
        return (
            "Random Forest",
            RandomForestRegressor(
                n_estimators=120,
                max_depth=10,
                min_samples_leaf=1,
                random_state=random_state,
                n_jobs=-1,
            ),
        )
    if normalized == "svr":
        return (
            "SVR Linear",
            Pipeline(
                [
                    ("scaler", StandardScaler()),
                    ("model", SVR(kernel="linear", C=100, epsilon=0.001)),
                ]
            ),
        )
    raise ValueError(f"Unknown fallback candidate: {name}")


def regression_metrics(y_true: pd.Series, y_pred: np.ndarray, prefix: str) -> dict[str, float]:
    mse = mean_squared_error(y_true, y_pred)
    metrics = {
        f"{prefix}_mae": float(mean_absolute_error(y_true, y_pred)),
        f"{prefix}_rmse": float(np.sqrt(mse)),
    }
    if len(y_true) >= 2:
        metrics[f"{prefix}_r2"] = float(r2_score(y_true, y_pred))
    return metrics


def checkpoint_display_name(entry: dict[str, Any], fallback_name: str) -> str:
    label = entry.get("model_label")
    if label:
        return str(label)

    name = str(entry.get("model_name", fallback_name))
    if name.startswith("Kaggle "):
        name = name.removeprefix("Kaggle ").strip()
    if name.endswith("(next-day price)"):
        name = name.removesuffix("(next-day price)").strip()
    return name or fallback_name


def load_model_result_from_registry_entry(entry: dict[str, Any], root_dir: Any) -> ModelResult:
    root = root_dir
    model_path = root / entry["model_path"]
    scaler_path = entry.get("scaler_path")
    scaler = load(root / scaler_path) if scaler_path else None
    display_name = checkpoint_display_name(entry, model_path.stem)
    return ModelResult(
        model_name=display_name,
        model=load(model_path),
        feature_columns=list(entry["feature_columns"]),
        metrics={key: float(value) for key, value in entry.get("metrics", {}).items()},
        source="checkpoint",
        scaler=scaler,
        model_key=entry.get("model_key"),
        model_label=display_name,
        is_recommended=bool(entry.get("recommended", False)),
    )


def direction_from_prices(predicted_price: float, current_price: float) -> str:
    return "UP" if float(predicted_price) > float(current_price) else "DOWN"


def evaluate_prediction(
    predicted_price: float,
    current_price: float,
    actual_next_price: float,
) -> dict[str, float | str | bool]:
    predicted_direction = direction_from_prices(predicted_price, current_price)
    actual_direction = direction_from_prices(actual_next_price, current_price)
    absolute_error = abs(float(predicted_price) - float(actual_next_price))
    error_pct = absolute_error / abs(float(actual_next_price)) * 100.0 if actual_next_price else np.nan
    return {
        "predicted_direction": predicted_direction,
        "actual_direction": actual_direction,
        "direction_correct": predicted_direction == actual_direction,
        "absolute_error": float(absolute_error),
        "error_pct": float(error_pct),
    }
