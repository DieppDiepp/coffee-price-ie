export type LoadState = "idle" | "loading" | "error";

export type ModelChoice = {
  key: string;
};

export function canRunMlPrediction(
  date: string,
  modelKey: string,
  availableDates: string[],
  availableModels: ModelChoice[]
) {
  return Boolean(date && modelKey) && availableDates.includes(date) && availableModels.some((item) => item.key === modelKey);
}

export function canRunGeminiPrediction(
  hasPrediction: boolean,
  loadState: LoadState,
  geminiLoading: boolean
) {
  return hasPrediction && loadState === "idle" && !geminiLoading;
}
