from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class Option(BaseModel):
    value: str
    label: str


class ModelOption(BaseModel):
    key: str
    label: str
    model_name: str
    source: str
    is_recommended: bool = False
    metrics: dict[str, float] = Field(default_factory=dict)


class SplitRange(BaseModel):
    start_date: str
    end_date: str
    count: int


class DatasetSplit(BaseModel):
    train: SplitRange
    validation: SplitRange
    test: SplitRange
    selected_date_scope: str = "test"


class MetadataResponse(BaseModel):
    coffee_types: list[Option]
    feature_versions: list[Option]
    available_dates: dict[str, dict[str, list[str]]]
    available_models: dict[str, dict[str, list[ModelOption]]]
    dataset_split: dict[str, dict[str, DatasetSplit]]


class Selection(BaseModel):
    coffee_type: str
    coffee_label: str
    feature_version: str
    feature_version_label: str
    model_key: str | None = None
    model_label: str | None = None
    date: str
    reference_date: str | None = None


class GroundTruth(BaseModel):
    actual_next_price: float
    actual_direction: str
    actual_change: float
    actual_change_pct: float


class PredictionEvaluation(BaseModel):
    predicted_price: float
    predicted_direction: str
    direction_correct: bool
    absolute_error: float
    error_pct: float


class ModelInfo(BaseModel):
    key: str | None = None
    name: str
    source: str
    metrics: dict[str, float]
    feature_count: int
    is_recommended: bool = False


class ChartPoint(BaseModel):
    date: str
    price: float | None = None
    selected: bool = False
    target: bool = False


class SurroundingRow(BaseModel):
    date: str
    role: str
    gia_viet_nam: float | None = None
    close: float | None = None
    open: float | None = None
    high: float | None = None
    low: float | None = None
    volume: float | None = None
    change_pct: float | None = None


class FeatureValue(BaseModel):
    name: str
    value: float


class VersionMetric(BaseModel):
    version: str
    label: str
    model_name: str
    source: str
    val_rmse: float | None = None
    test_rmse: float | None = None
    test_mae: float | None = None


class PredictionResponse(BaseModel):
    selection: Selection
    dataset_split: DatasetSplit
    current_price: float
    ground_truth: GroundTruth
    ml_prediction: PredictionEvaluation
    model: ModelInfo
    chart: list[ChartPoint]
    surrounding_rows: list[SurroundingRow]
    version_comparison: list[VersionMetric]
    feature_snapshot: list[FeatureValue]


class GeminiRequest(BaseModel):
    coffee_type: str = Field(..., min_length=1)
    feature_version: str = Field(..., min_length=1)
    date: str = Field(..., min_length=1)
    model_key: str | None = None


class GeminiPredictionResponse(BaseModel):
    available: bool
    predicted_price: float | None = None
    predicted_direction: str | None = None
    confidence: float | None = None
    rationale: str | None = None
    absolute_error: float | None = None
    error_pct: float | None = None
    direction_correct: bool | None = None
    error: str | None = None
    prompt: str | None = None
    input_rows: list[dict[str, Any]] = Field(default_factory=list)
    raw_output: str | None = None
