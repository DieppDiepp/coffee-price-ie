import type { GeminiResponse } from "./api";

export function unavailableGeminiResult(error: unknown): GeminiResponse {
  const message = error instanceof Error ? error.message : "Không thể gọi Gemini.";
  return {
    available: false,
    predicted_price: null,
    predicted_direction: null,
    confidence: null,
    rationale: null,
    absolute_error: null,
    error_pct: null,
    direction_correct: null,
    error: message,
    prompt: null,
    input_rows: [],
    raw_output: null
  };
}
