import { describe, expect, it } from "vitest";

import { directionLabel, formatPercent, formatPrice } from "./format";


describe("format helpers", () => {
  it("formats VND prices for Vietnamese dashboard cards", () => {
    expect(formatPrice(93337)).toBe("93.337 VND");
    expect(formatPrice(null)).toBe("-");
  });

  it("formats percentages with sign and two decimals", () => {
    expect(formatPercent(4.104)).toBe("+4,10%");
    expect(formatPercent(-3.756)).toBe("-3,76%");
    expect(formatPercent(null)).toBe("-");
  });

  it("maps direction values to Vietnamese labels", () => {
    expect(directionLabel("UP")).toBe("Tăng");
    expect(directionLabel("DOWN")).toBe("Giảm");
    expect(directionLabel(null)).toBe("-");
  });
});
