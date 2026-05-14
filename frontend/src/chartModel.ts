type PredictionChartPoint = {
  date: string;
  price: number | null;
  selected: boolean;
  target: boolean;
};

type PredictionChartInput = {
  chart: PredictionChartPoint[];
  selection: {
    date: string;
  };
  ground_truth: {
    actual_next_price: number;
  };
  ml_prediction: {
    predicted_price: number;
  };
};

type GeminiChartInput = {
  available: boolean;
  predicted_price: number | null;
} | null;

export type ChartDatum = PredictionChartPoint & {
  groundTruth?: number | null;
  ml?: number | null;
  gemini?: number | null;
};

export const predictionMarkerSeries = [
  {
    key: "groundTruth",
    label: "Ground truth",
    color: "#16725f",
    offsetX: 0,
    shape: "circle"
  },
  {
    key: "ml",
    label: "ML dự đoán",
    color: "#c65f2d",
    offsetX: 0,
    shape: "diamond"
  },
  {
    key: "gemini",
    label: "Gemini dự đoán",
    color: "#6a4fd8",
    offsetX: 0,
    shape: "square"
  }
] as const;

export type PredictionMarkerEntry = {
  key: (typeof predictionMarkerSeries)[number]["key"];
  label: (typeof predictionMarkerSeries)[number]["label"];
  color: (typeof predictionMarkerSeries)[number]["color"];
  shape: (typeof predictionMarkerSeries)[number]["shape"];
  date: string;
  value: number;
};

export type PredictionMarkerGroup = {
  date: string;
  value: number;
  entries: PredictionMarkerEntry[];
};

export type PredictionMarkerDayDetails = {
  date: string;
  historyPrice: number | null;
  entries: PredictionMarkerEntry[];
};

const PREDICTION_MARKER_CLUSTER_THRESHOLD = 1000;
const PREDICTION_MARKER_ORDER = new Map(
  predictionMarkerSeries.map((item, index) => [item.key, index] as const)
);

export function buildChartData(
  prediction: PredictionChartInput | null,
  gemini: GeminiChartInput
): ChartDatum[] {
  if (!prediction) return [];

  const data = prediction.chart.map((point) => ({ ...point })) as ChartDatum[];
  const targetDate = prediction.selection.date;
  if (!targetDate) return data;

  let targetPoint = data.find((point) => point.date === targetDate);
  if (!targetPoint) {
    targetPoint = { date: targetDate, price: null, selected: false, target: true };
    data.push(targetPoint);
    data.sort((a, b) => a.date.localeCompare(b.date));
  }

  Object.assign(targetPoint, {
    groundTruth: prediction.ground_truth.actual_next_price,
    ml: prediction.ml_prediction.predicted_price,
    gemini: gemini?.available ? gemini.predicted_price : null
  });

  return data;
}

export function buildPredictionMarkerGroups(
  prediction: PredictionChartInput | null,
  gemini: GeminiChartInput
): PredictionMarkerGroup[] {
  if (!prediction) return [];

  const markerEntries: PredictionMarkerEntry[] = [
    markerEntry("groundTruth", prediction.selection.date, prediction.ground_truth.actual_next_price),
    markerEntry("ml", prediction.selection.date, prediction.ml_prediction.predicted_price),
    gemini?.available && gemini.predicted_price !== null
      ? markerEntry("gemini", prediction.selection.date, gemini.predicted_price)
      : null
  ].filter((item): item is PredictionMarkerEntry => item !== null);
  const byDate = new Map<string, PredictionMarkerEntry[]>();
  for (const entry of markerEntries) {
    const bucket = byDate.get(entry.date);
    if (bucket) {
      bucket.push(entry);
      continue;
    }
    byDate.set(entry.date, [entry]);
  }

  const groups: PredictionMarkerGroup[] = [];
  for (const [date, entries] of byDate.entries()) {
    const sorted = entries.slice().sort((left, right) => left.value - right.value);
    let currentGroup: PredictionMarkerEntry[] = [];

    for (const entry of sorted) {
      if (!currentGroup.length) {
        currentGroup = [entry];
        continue;
      }

      const currentCenter = averageValue(currentGroup);
      if (Math.abs(entry.value - currentCenter) <= PREDICTION_MARKER_CLUSTER_THRESHOLD) {
        currentGroup.push(entry);
        continue;
      }

      groups.push({
        date,
        value: averageValue(currentGroup),
        entries: currentGroup
      });
      currentGroup = [entry];
    }

    if (currentGroup.length) {
      groups.push({
        date,
        value: averageValue(currentGroup),
        entries: currentGroup
      });
    }
  }

  return groups.sort((left, right) => left.value - right.value);
}

export function buildPredictionMarkerDayDetails(
  chartData: ChartDatum[],
  markerGroups: PredictionMarkerGroup[],
  date: string
): PredictionMarkerDayDetails | null {
  const history = chartData.find((item) => item.date === date);
  const entries = markerGroups
    .filter((item) => item.date === date)
    .flatMap((item) => item.entries)
    .slice()
    .sort((left, right) => {
      return (
        (PREDICTION_MARKER_ORDER.get(left.key) ?? Number.MAX_SAFE_INTEGER) -
        (PREDICTION_MARKER_ORDER.get(right.key) ?? Number.MAX_SAFE_INTEGER)
      );
    });

  if (!history && !entries.length) {
    return null;
  }

  return {
    date,
    historyPrice: history?.price ?? null,
    entries
  };
}

function markerEntry(
  key: (typeof predictionMarkerSeries)[number]["key"],
  date: string,
  value: number
): PredictionMarkerEntry {
  const series = predictionMarkerSeries.find((item) => item.key === key);
  if (!series) {
    throw new Error(`Unknown prediction marker key: ${key}`);
  }

  return {
    key,
    label: series.label,
    color: series.color,
    shape: series.shape,
    date,
    value
  };
}

function averageValue(entries: PredictionMarkerEntry[]) {
  const total = entries.reduce((sum, entry) => sum + entry.value, 0);
  return Math.round(total / entries.length);
}
