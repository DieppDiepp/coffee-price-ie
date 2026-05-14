export type Direction = "UP" | "DOWN";

const priceFormatter = new Intl.NumberFormat("vi-VN", {
  maximumFractionDigits: 0
});

const percentFormatter = new Intl.NumberFormat("vi-VN", {
  minimumFractionDigits: 2,
  maximumFractionDigits: 2
});

export function formatPrice(value: number | null | undefined): string {
  if (value === null || value === undefined || Number.isNaN(value)) {
    return "-";
  }
  return `${priceFormatter.format(value)} VND`;
}

export function formatCompactPrice(value: number | null | undefined): string {
  if (value === null || value === undefined || Number.isNaN(value)) {
    return "-";
  }
  if (Math.abs(value) >= 1000) {
    return `${priceFormatter.format(value / 1000)}k`;
  }
  return priceFormatter.format(value);
}

export function formatPercent(value: number | null | undefined): string {
  if (value === null || value === undefined || Number.isNaN(value)) {
    return "-";
  }
  const sign = value > 0 ? "+" : "";
  return `${sign}${percentFormatter.format(value)}%`;
}

export function formatNumber(value: number | null | undefined): string {
  if (value === null || value === undefined || Number.isNaN(value)) {
    return "-";
  }
  return priceFormatter.format(value);
}

export function directionLabel(direction: Direction | string | null | undefined): string {
  if (direction === "UP") {
    return "Tăng";
  }
  if (direction === "DOWN") {
    return "Giảm";
  }
  return "-";
}

export function sourceLabel(source: string): string {
  return source === "checkpoint" ? "Checkpoint Kaggle" : "Fallback train từ CSV";
}
