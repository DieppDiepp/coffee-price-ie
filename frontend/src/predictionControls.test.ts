import { describe, expect, it } from "vitest";

import { canRunGeminiPrediction, canRunMlPrediction } from "./predictionControls";

describe("prediction controls", () => {
  it("enables ML prediction only when date and model are valid", () => {
    const dates = ["2026-03-09", "2026-03-10"];
    const models = [{ key: "lasso" }, { key: "ridge" }];

    expect(canRunMlPrediction("", "lasso", dates, models)).toBe(false);
    expect(canRunMlPrediction("2026-03-10", "", dates, models)).toBe(false);
    expect(canRunMlPrediction("2026-03-11", "lasso", dates, models)).toBe(false);
    expect(canRunMlPrediction("2026-03-10", "svr", dates, models)).toBe(false);
    expect(canRunMlPrediction("2026-03-10", "lasso", dates, models)).toBe(true);
  });

  it("enables Gemini only after an ML prediction is available", () => {
    expect(canRunGeminiPrediction(false, "idle", false)).toBe(false);
    expect(canRunGeminiPrediction(true, "loading", false)).toBe(false);
    expect(canRunGeminiPrediction(true, "idle", true)).toBe(false);
    expect(canRunGeminiPrediction(true, "idle", false)).toBe(true);
  });
});
