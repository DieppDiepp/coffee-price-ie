import { describe, expect, it } from "vitest";

import { unavailableGeminiResult } from "./geminiState";


describe("Gemini state helpers", () => {
  it("normalizes request failures into an unavailable result", () => {
    expect(unavailableGeminiResult(new Error("Network down"))).toMatchObject({
      available: false,
      error: "Network down",
      predicted_price: null,
      predicted_direction: null
    });
  });
});
