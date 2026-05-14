import { describe, expect, test } from "vitest";

import {
  buildChartData,
  buildPredictionMarkerDayDetails,
  buildPredictionMarkerGroups,
  predictionMarkerSeries
} from "./chartModel";

describe("buildChartData", () => {
  test("adds all prediction markers at the selected prediction day", () => {
    const chartData = buildChartData(
      {
        chart: [
          { date: "2026-03-01", price: 98000, selected: false, target: false },
          { date: "2026-03-02", price: null, selected: true, target: true }
        ],
        selection: {
          date: "2026-03-02"
        },
        ground_truth: {
          actual_next_price: 96500
        },
        ml_prediction: {
          predicted_price: 97100
        }
      },
      {
        available: true,
        predicted_price: 96800
      }
    );

    expect(chartData).toHaveLength(2);
    expect(chartData[1]).toMatchObject({
      date: "2026-03-02",
      groundTruth: 96500,
      ml: 97100,
      gemini: 96800
    });
  });

  test("keeps gemini marker empty when gemini is unavailable", () => {
    const chartData = buildChartData(
      {
        chart: [{ date: "2026-03-02", price: null, selected: true, target: true }],
        selection: {
          date: "2026-03-02"
        },
        ground_truth: {
          actual_next_price: 96500
        },
        ml_prediction: {
          predicted_price: 97100
        }
      },
      {
        available: false,
        predicted_price: null
      }
    );

    expect(chartData[0].gemini).toBeNull();
  });
});

describe("predictionMarkerSeries", () => {
  test("keeps prediction markers on the same day line and differentiates by shape", () => {
    expect(predictionMarkerSeries.map((item) => item.key)).toEqual([
      "groundTruth",
      "ml",
      "gemini"
    ]);
    expect(new Set(predictionMarkerSeries.map((item) => item.label)).size).toBe(3);
    expect(new Set(predictionMarkerSeries.map((item) => item.color)).size).toBe(3);
    expect(new Set(predictionMarkerSeries.map((item) => item.offsetX))).toEqual(new Set([0]));
    expect(new Set(predictionMarkerSeries.map((item) => item.shape)).size).toBe(3);
  });
});

describe("buildPredictionMarkerGroups", () => {
  test("clusters markers that land on the exact same day and price", () => {
    const groups = buildPredictionMarkerGroups(
      {
        chart: [{ date: "2026-03-02", price: null, selected: true, target: true }],
        selection: {
          date: "2026-03-02"
        },
        ground_truth: {
          actual_next_price: 96500
        },
        ml_prediction: {
          predicted_price: 97100
        }
      },
      {
        available: true,
        predicted_price: 97100
      }
    );

    expect(groups).toHaveLength(1);
    const clusteredPrediction = groups[0];
    expect(clusteredPrediction?.entries.map((item) => item.key)).toEqual([
      "groundTruth",
      "ml",
      "gemini"
    ]);
    expect(new Set(groups.map((item) => item.date))).toEqual(new Set(["2026-03-02"]));
  });

  test("clusters markers that are too close to distinguish on the same day", () => {
    const groups = buildPredictionMarkerGroups(
      {
        chart: [{ date: "2026-03-10", price: null, selected: true, target: true }],
        selection: {
          date: "2026-03-10"
        },
        ground_truth: {
          actual_next_price: 96988
        },
        ml_prediction: {
          predicted_price: 99077
        }
      },
      {
        available: true,
        predicted_price: 99115
      }
    );

    expect(groups).toHaveLength(2);
    const clusteredPrediction = groups.find((item) => item.entries.length === 2);
    expect(clusteredPrediction?.entries.map((item) => item.key)).toEqual([
      "ml",
      "gemini"
    ]);
    expect(clusteredPrediction?.value).toBe(99096);
  });
});

describe("buildPredictionMarkerDayDetails", () => {
  test("returns all prediction sources for the hovered day even when they are split into multiple groups", () => {
    const prediction = {
      chart: [
        { date: "2026-03-09", price: 99064, selected: false, target: false },
        { date: "2026-03-10", price: null, selected: true, target: true }
      ],
      selection: {
        date: "2026-03-10"
      },
      ground_truth: {
        actual_next_price: 96988
      },
      ml_prediction: {
        predicted_price: 99077
      }
    };
    const gemini = {
      available: true,
      predicted_price: 99115
    };

    const chartData = buildChartData(prediction, gemini);
    const markerGroups = buildPredictionMarkerGroups(prediction, gemini);
    const details = buildPredictionMarkerDayDetails(chartData, markerGroups, "2026-03-10");

    expect(details).toMatchObject({
      date: "2026-03-10",
      historyPrice: null
    });
    expect(details?.entries.map((item) => item.key)).toEqual([
      "groundTruth",
      "ml",
      "gemini"
    ]);
  });
});
