import type { Direction } from "./format";

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL ?? "";

export type Option = {
  value: string;
  label: string;
};

export type DatasetSplit = {
  train: {
    start_date: string;
    end_date: string;
    count: number;
  };
  validation: {
    start_date: string;
    end_date: string;
    count: number;
  };
  test: {
    start_date: string;
    end_date: string;
    count: number;
  };
  selected_date_scope: string;
};

export type MetadataResponse = {
  coffee_types: Option[];
  feature_versions: Option[];
  available_dates: Record<string, Record<string, string[]>>;
  dataset_split: Record<string, Record<string, DatasetSplit>>;
  available_models: Record<
    string,
    Record<
      string,
      Array<{
        key: string;
        label: string;
        model_name: string;
        source: string;
        is_recommended: boolean;
        metrics: Record<string, number>;
      }>
    >
  >;
};

export type PredictionResponse = {
  selection: {
    coffee_type: string;
    coffee_label: string;
    feature_version: string;
    feature_version_label: string;
    model_key: string | null;
    model_label: string | null;
    date: string;
    reference_date: string | null;
  };
  dataset_split: DatasetSplit;
  current_price: number;
  ground_truth: {
    actual_next_price: number;
    actual_direction: Direction;
    actual_change: number;
    actual_change_pct: number;
  };
  ml_prediction: {
    predicted_price: number;
    predicted_direction: Direction;
    direction_correct: boolean;
    absolute_error: number;
    error_pct: number;
  };
  model: {
    key: string | null;
    name: string;
    source: string;
    metrics: Record<string, number>;
    feature_count: number;
    is_recommended: boolean;
  };
  chart: Array<{
    date: string;
    price: number | null;
    selected: boolean;
    target: boolean;
  }>;
  surrounding_rows: Array<{
    date: string;
    role: string;
    gia_viet_nam: number | null;
    close: number | null;
    open: number | null;
    high: number | null;
    low: number | null;
    volume: number | null;
    change_pct: number | null;
  }>;
  version_comparison: Array<{
    version: string;
    label: string;
    model_name: string;
    source: string;
    val_rmse: number | null;
    test_rmse: number | null;
    test_mae: number | null;
  }>;
  feature_snapshot: Array<{
    name: string;
    value: number;
  }>;
};

export type GeminiResponse = {
  available: boolean;
  predicted_price: number | null;
  predicted_direction: Direction | null;
  confidence: number | null;
  rationale: string | null;
  absolute_error: number | null;
  error_pct: number | null;
  direction_correct: boolean | null;
  error: string | null;
  prompt: string | null;
  input_rows: Array<Record<string, unknown>>;
  raw_output: string | null;
};

async function requestJson<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${API_BASE_URL}${path}`, {
    headers: {
      "Content-Type": "application/json",
      ...init?.headers
    },
    ...init
  });
  if (!response.ok) {
    const text = await response.text();
    throw new Error(text || `Request failed with ${response.status}`);
  }
  return response.json() as Promise<T>;
}

export function fetchMetadata(): Promise<MetadataResponse> {
  return requestJson<MetadataResponse>("/api/metadata");
}

export function fetchPrediction(
  coffeeType: string,
  featureVersion: string,
  date: string,
  modelKey?: string
): Promise<PredictionResponse> {
  const params = new URLSearchParams({
    coffee_type: coffeeType,
    feature_version: featureVersion,
    date
  });
  if (modelKey) {
    params.set("model_key", modelKey);
  }
  return requestJson<PredictionResponse>(`/api/prediction?${params.toString()}`);
}

export function fetchGeminiPrediction(
  coffeeType: string,
  featureVersion: string,
  date: string,
  modelKey?: string
): Promise<GeminiResponse> {
  return requestJson<GeminiResponse>("/api/gemini", {
    method: "POST",
    body: JSON.stringify({
      coffee_type: coffeeType,
      feature_version: featureVersion,
      date,
      model_key: modelKey
    })
  });
}
