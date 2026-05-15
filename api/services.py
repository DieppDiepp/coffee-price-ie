from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from dashboard.data_loader import (
    COFFEE_TYPES,
    FEATURE_VERSION_LABELS,
    FEATURE_VERSIONS,
    load_model_dataset,
)

_NEWS_DATA_PATH = Path(__file__).resolve().parents[1] / "data" / "html" / "final_enriched_dataset.csv"
from dashboard.llm_gemini import build_gemini_prompt_from_articles, predict_with_gemini
from dashboard.model_registry import load_checkpoint_model, normalize_key, registry_entries_for
from dashboard.modeling import (
    DatasetSplitContext as ModelingDatasetSplit,
    ModelResult,
    dataset_split_context,
    evaluate_prediction,
    feature_columns_for,
    prediction_dates_for_test_split,
    train_fallback_model,
)

from api.schemas import (
    ChartPoint,
    DatasetSplit,
    FeatureValue,
    GeminiPredictionResponse,
    GroundTruth,
    MetadataResponse,
    ModelInfo,
    ModelOption,
    Option,
    PredictionEvaluation,
    PredictionResponse,
    Selection,
    SplitRange,
    SurroundingRow,
    VersionMetric,
)


COFFEE_LABELS = {
    "robusta": "Robusta",
    "arabica": "Arabica",
}

FALLBACK_MODEL_CHOICES = (
    ("fallback_ridge", "Ridge", "ridge"),
    ("fallback_random_forest", "Random Forest", "random_forest"),
    ("fallback_svr", "SVR Linear", "svr"),
)
FALLBACK_CANDIDATE_BY_KEY = {
    key: (label, candidate)
    for key, label, candidate in FALLBACK_MODEL_CHOICES
}
FALLBACK_KEY_BY_MODEL_NAME = {
    "Ridge": "fallback_ridge",
    "Random Forest": "fallback_random_forest",
    "SVR Linear": "fallback_svr",
}


@lru_cache(maxsize=12)
def get_dataset(coffee_type: str, feature_version: str) -> pd.DataFrame:
    return load_model_dataset(coffee_type, feature_version)


@lru_cache(maxsize=12)
def get_model(coffee_type: str, feature_version: str, model_key: str = "") -> ModelResult:
    normalized_model_key = normalize_key(model_key) if model_key else ""
    if normalized_model_key == "fallback":
        normalized_model_key = recommended_fallback_key(coffee_type, feature_version)

    if normalized_model_key in FALLBACK_CANDIDATE_BY_KEY:
        fallback = train_named_fallback_model(coffee_type, feature_version, normalized_model_key)
        fallback.is_recommended = (
            normalized_model_key == recommended_fallback_key(coffee_type, feature_version)
        )
        return fallback

    checkpoint = load_checkpoint_model(
        coffee_type,
        feature_version,
        model_key=normalized_model_key or None,
    )
    if checkpoint is not None:
        return checkpoint

    if normalized_model_key:
        raise ValueError(
            f"Model {model_key!r} is not available for {coffee_type}.{feature_version}"
        )

    return get_model(
        coffee_type,
        feature_version,
        recommended_fallback_key(coffee_type, feature_version),
    )


@lru_cache(maxsize=18)
def train_named_fallback_model(
    coffee_type: str,
    feature_version: str,
    fallback_key: str,
) -> ModelResult:
    label, candidate = FALLBACK_CANDIDATE_BY_KEY[fallback_key]
    model = train_fallback_model(
        get_dataset(coffee_type, feature_version),
        candidate_names=(candidate,),
    )
    model.model_key = fallback_key
    model.model_label = label
    return model


@lru_cache(maxsize=6)
def recommended_fallback_key(coffee_type: str, feature_version: str) -> str:
    model = train_fallback_model(get_dataset(coffee_type, feature_version))
    return FALLBACK_KEY_BY_MODEL_NAME.get(model.model_name, "fallback_ridge")


@lru_cache(maxsize=6)
def fallback_model_options(coffee_type: str, feature_version: str) -> tuple[ModelOption, ...]:
    recommended_key = recommended_fallback_key(coffee_type, feature_version)
    options: list[ModelOption] = []
    for key, label, _ in FALLBACK_MODEL_CHOICES:
        option_label = f"{label} (Recommend)" if key == recommended_key else label
        options.append(
            ModelOption(
                key=key,
                label=option_label,
                model_name=label,
                source="fallback",
                is_recommended=key == recommended_key,
                metrics={},
            )
        )
    return tuple(
        sorted(
            options,
            key=lambda option: 0 if option.is_recommended else 1,
        )
    )


@lru_cache(maxsize=12)
def checkpoint_model_options(coffee_type: str, feature_version: str) -> tuple[ModelOption, ...]:
    options: list[ModelOption] = []
    for key, _ in registry_entries_for(coffee_type, feature_version):
        checkpoint = load_checkpoint_model(coffee_type, feature_version, model_key=key)
        if checkpoint is None:
            continue
        options.append(model_option_from_result(checkpoint))
    return tuple(options)


@lru_cache(maxsize=12)
def model_options_for(coffee_type: str, feature_version: str) -> tuple[ModelOption, ...]:
    checkpoint_options = checkpoint_model_options(coffee_type, feature_version)
    if checkpoint_options:
        return checkpoint_options
    return fallback_model_options(coffee_type, feature_version)


@lru_cache(maxsize=2)
def get_version_metrics(coffee_type: str) -> tuple[VersionMetric, ...]:
    metrics: list[VersionMetric] = []
    for version in FEATURE_VERSIONS:
        model = get_model(coffee_type, version)
        metrics.append(
            VersionMetric(
                version=version,
                label=FEATURE_VERSION_LABELS[version],
                model_name=model.model_name,
                source=model.source,
                val_rmse=finite_or_none(model.metrics.get("val_rmse")),
                test_rmse=finite_or_none(model.metrics.get("test_rmse")),
                test_mae=finite_or_none(model.metrics.get("test_mae")),
            )
        )
    return tuple(metrics)


def metadata_response() -> MetadataResponse:
    available_dates: dict[str, dict[str, list[str]]] = {}
    available_models: dict[str, dict[str, list[ModelOption]]] = {}
    dataset_split: dict[str, dict[str, DatasetSplit]] = {}
    for coffee_type in COFFEE_TYPES:
        available_dates[coffee_type] = {}
        available_models[coffee_type] = {}
        dataset_split[coffee_type] = {}
        for version in FEATURE_VERSIONS:
            df = get_dataset(coffee_type, version)
            available_dates[coffee_type][version] = prediction_dates_for_test_split(df)
            available_models[coffee_type][version] = list(model_options_for(coffee_type, version))
            dataset_split[coffee_type][version] = split_schema_from_context(
                dataset_split_context(df)
            )

    return MetadataResponse(
        coffee_types=[
            Option(value=value, label=COFFEE_LABELS[value])
            for value in COFFEE_TYPES
        ],
        feature_versions=[
            Option(value=value, label=FEATURE_VERSION_LABELS[value])
            for value in FEATURE_VERSIONS
        ],
        available_dates=available_dates,
        available_models=available_models,
        dataset_split=dataset_split,
    )


def prediction_response(
    coffee_type: str,
    feature_version: str,
    date: str,
    model_key: str | None = None,
) -> PredictionResponse:
    df, source_row, _, selected_date = validated_prediction_context(
        coffee_type,
        feature_version,
        date,
    )
    model = get_model(coffee_type, feature_version, model_key or "")
    predicted_price = model.predict(source_row)
    evaluation = evaluate_prediction(
        predicted_price=predicted_price,
        current_price=float(source_row["current_price"]),
        actual_next_price=float(source_row["actual_next_price"]),
    )

    return PredictionResponse(
        selection=Selection(
            coffee_type=coffee_type,
            coffee_label=COFFEE_LABELS[coffee_type],
            feature_version=feature_version,
            feature_version_label=FEATURE_VERSION_LABELS[feature_version],
            model_key=model.model_key,
            model_label=model.model_label or model.model_name,
            date=selected_date.strftime("%Y-%m-%d"),
            reference_date=format_date(source_row.get("date")),
        ),
        dataset_split=get_dataset_split_schema(coffee_type, feature_version),
        current_price=float(source_row["current_price"]),
        ground_truth=GroundTruth(
            actual_next_price=float(source_row["actual_next_price"]),
            actual_direction=str(source_row["actual_direction"]),
            actual_change=float(source_row["actual_change"]),
            actual_change_pct=float(source_row["actual_change_pct"]),
        ),
        ml_prediction=PredictionEvaluation(
            predicted_price=float(predicted_price),
            predicted_direction=str(evaluation["predicted_direction"]),
            direction_correct=bool(evaluation["direction_correct"]),
            absolute_error=float(evaluation["absolute_error"]),
            error_pct=float(evaluation["error_pct"]),
        ),
        model=ModelInfo(
            key=model.model_key,
            name=model.model_name,
            source=model.source,
            metrics={key: float(value) for key, value in model.metrics.items() if np.isfinite(value)},
            feature_count=len(model.feature_columns),
            is_recommended=model.is_recommended,
        ),
        chart=chart_points(df, selected_date),
        surrounding_rows=surrounding_rows(
            df,
            selected_date=selected_date,
            reference_date=pd.Timestamp(source_row["date"]),
        ),
        version_comparison=list(get_version_metrics(coffee_type)),
        feature_snapshot=feature_snapshot(source_row, model.feature_columns),
    )


def load_articles_for_gemini(reference_date: str, window_days: int = 7) -> list[dict[str, Any]]:
    if not _NEWS_DATA_PATH.exists():
        return []
    try:
        df = pd.read_csv(_NEWS_DATA_PATH).fillna("")
        df["_date"] = pd.to_datetime(df["date"], errors="coerce")
        end = pd.Timestamp(reference_date)
        start = end - pd.Timedelta(days=window_days)
        mask = (df["_date"] >= start) & (df["_date"] <= end)
        subset = df[mask].drop(columns=["_date"]).sort_values("date")
        return subset.to_dict(orient="records")[:20]
    except Exception:
        return []


def gemini_prediction_response(
    coffee_type: str,
    feature_version: str,
    date: str,
    model_key: str | None = None,
) -> GeminiPredictionResponse:
    df, source_row, _, selected_date = validated_prediction_context(
        coffee_type,
        feature_version,
        date,
    )
    reference_date_str = pd.Timestamp(source_row["date"]).strftime("%Y-%m-%d")
    articles = load_articles_for_gemini(reference_date_str, window_days=0)
    current_price = float(source_row["current_price"])
    prompt = build_gemini_prompt_from_articles(
        coffee_type=COFFEE_LABELS[coffee_type],
        articles=articles,
        current_price=current_price,
        prediction_date=date,
    )
    result = predict_with_gemini(prompt)
    if not result.available or result.prediction is None:
        return GeminiPredictionResponse(
            available=False,
            error=result.error,
            prompt=prompt,
            input_rows=articles,
            raw_output=None,
        )

    prediction = result.prediction
    evaluation = evaluate_prediction(
        predicted_price=prediction.predicted_next_price,
        current_price=current_price,
        actual_next_price=float(source_row["actual_next_price"]),
    )
    return GeminiPredictionResponse(
        available=True,
        predicted_price=prediction.predicted_next_price,
        predicted_direction=prediction.predicted_direction,
        confidence=prediction.confidence,
        rationale=prediction.rationale,
        absolute_error=float(evaluation["absolute_error"]),
        error_pct=float(evaluation["error_pct"]),
        direction_correct=bool(evaluation["direction_correct"]),
        prompt=prompt,
        input_rows=articles,
        raw_output=prediction.raw_response,
    )


def chart_points(df: pd.DataFrame, selected_date: pd.Timestamp, window: int = 28) -> list[ChartPoint]:
    selected_index = int(df.index[df["date"] == selected_date][0])
    start = max(selected_index - window, 0)
    stop = selected_index
    subset = df.iloc[start : stop + 1]
    points: list[ChartPoint] = []
    for _, item in subset.iterrows():
        item_date = pd.Timestamp(item["date"])
        price = finite_or_none(item.get("current_price"))
        if item_date >= selected_date:
            price = None
        points.append(
            ChartPoint(
                date=item_date.strftime("%Y-%m-%d"),
                price=price,
                selected=item_date == selected_date,
                target=item_date == selected_date,
            )
        )
    return points


def feature_snapshot(row: pd.Series, feature_columns: list[str], limit: int = 12) -> list[FeatureValue]:
    fallback_columns = feature_columns_for(pd.DataFrame([row]))
    columns = feature_columns or fallback_columns
    values: list[tuple[str, float]] = []
    for column in columns:
        value = row.get(column)
        if value is None:
            continue
        try:
            numeric = float(value)
        except (TypeError, ValueError):
            continue
        if np.isfinite(numeric):
            values.append((column, numeric))
    values.sort(key=lambda item: abs(item[1]), reverse=True)
    return [FeatureValue(name=name, value=value) for name, value in values[:limit]]


def surrounding_rows(
    df: pd.DataFrame,
    selected_date: pd.Timestamp,
    reference_date: pd.Timestamp | None = None,
    total_rows: int = 7,
) -> list[SurroundingRow]:
    if df.empty:
        return []

    selected_index = int(df.index[df["date"] == selected_date][0])
    total = max(1, min(total_rows, len(df)))
    half_window = total // 2
    start = selected_index - half_window
    end = start + total
    if start < 0:
        end = min(len(df), end - start)
        start = 0
    if end > len(df):
        start = max(0, start - (end - len(df)))
        end = len(df)

    subset = df.iloc[start:end]
    reference_ts = pd.Timestamp(reference_date) if reference_date is not None else None
    rows: list[SurroundingRow] = []
    for _, item in subset.iterrows():
        item_date = pd.Timestamp(item["date"])
        role = "context"
        if reference_ts is not None and item_date == reference_ts:
            role = "reference_day"
        if item_date == selected_date:
            role = "prediction_day"
        rows.append(
            SurroundingRow(
                date=format_date(item_date) or "",
                role=role,
                gia_viet_nam=finite_or_none(item.get("Gia_Viet_Nam")),
                close=finite_or_none(item.get("close")),
                open=finite_or_none(item.get("open")),
                high=finite_or_none(item.get("high")),
                low=finite_or_none(item.get("low")),
                volume=finite_or_none(item.get("Volume")),
                change_pct=finite_or_none(item.get("Change_pct")),
            )
        )
    return rows


def model_option_from_result(model: ModelResult) -> ModelOption:
    label = model.model_label or model.model_name
    if model.is_recommended and "(Recommend)" not in label:
        label = f"{label} (Recommend)"
    return ModelOption(
        key=model.model_key or "default",
        label=label,
        model_name=model.model_name,
        source=model.source,
        is_recommended=model.is_recommended,
        metrics={key: float(value) for key, value in model.metrics.items() if np.isfinite(value)},
    )


def finite_or_none(value: Any) -> float | None:
    if value is None:
        return None
    try:
        numeric = float(value)
    except (TypeError, ValueError):
        return None
    return numeric if np.isfinite(numeric) else None


def format_date(value: Any) -> str | None:
    if value is None or pd.isna(value):
        return None
    return pd.Timestamp(value).strftime("%Y-%m-%d")


@lru_cache(maxsize=12)
def get_dataset_split_schema(coffee_type: str, feature_version: str) -> DatasetSplit:
    df = get_dataset(coffee_type, feature_version)
    return split_schema_from_context(dataset_split_context(df))


@lru_cache(maxsize=12)
def get_test_date_lookup(coffee_type: str, feature_version: str) -> frozenset[str]:
    df = get_dataset(coffee_type, feature_version)
    return frozenset(prediction_dates_for_test_split(df))


def validated_prediction_context(
    coffee_type: str,
    feature_version: str,
    date: str,
) -> tuple[pd.DataFrame, pd.Series, pd.Series, pd.Timestamp]:
    if date not in get_test_date_lookup(coffee_type, feature_version):
        raise ValueError(
            f"Date {date!r} is not available in the test set for {coffee_type}.{feature_version}"
        )

    df = get_dataset(coffee_type, feature_version)
    selected_date = pd.Timestamp(date)
    target_matching = df[df["date"] == selected_date]
    if target_matching.empty:
        raise ValueError(f"No ground-truth row found for date {date!r}")

    source_matching = df[df["target_date"] == selected_date]
    if source_matching.empty:
        raise ValueError(f"No source row found for prediction date {date!r}")

    return df, source_matching.iloc[0], target_matching.iloc[0], selected_date


def split_schema_from_context(context: ModelingDatasetSplit) -> DatasetSplit:
    return DatasetSplit(
        train=split_range_schema(context.train),
        validation=split_range_schema(context.validation),
        test=split_range_schema(context.test),
        selected_date_scope="test",
    )


def split_range_schema(window: Any) -> SplitRange:
    return SplitRange(
        start_date=format_date(window.start_date) or "",
        end_date=format_date(window.end_date) or "",
        count=int(window.count),
    )
