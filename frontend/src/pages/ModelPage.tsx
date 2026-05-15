import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import {
  Activity,
  Bot,
  CalendarDays,
  CheckCircle2,
  CircleDollarSign,
  Coffee,
  Database,
  LineChart as LineChartIcon,
  Loader2,
  RotateCcw,
  Sparkles,
  TrendingDown,
  TrendingUp,
  XCircle
} from "lucide-react";
import Navbar from "../components/Navbar";
import {
  CartesianGrid,
  ComposedChart,
  Line,
  ReferenceDot,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis
} from "recharts";

import {
  fetchGeminiPrediction,
  fetchMetadata,
  fetchPrediction,
  type GeminiResponse,
  type MetadataResponse,
  type PredictionResponse
} from "../api";
import {
  canRunGeminiPrediction,
  canRunMlPrediction,
  type LoadState
} from "../predictionControls";
import {
  buildChartData,
  buildPredictionMarkerDayDetails,
  buildPredictionMarkerGroups,
  predictionMarkerSeries,
  type ChartDatum,
  type PredictionMarkerDayDetails,
  type PredictionMarkerGroup
} from "../chartModel";
import {
  directionLabel,
  formatCompactPrice,
  formatNumber,
  formatPercent,
  formatPrice,
  sourceLabel
} from "../format";
import { unavailableGeminiResult } from "../geminiState";

type MarkerHoverState = {
  details: PredictionMarkerDayDetails;
  x: number;
  y: number;
  placement: "above" | "below";
};

function ModelPage() {
  const [metadata, setMetadata] = useState<MetadataResponse | null>(null);
  const [prediction, setPrediction] = useState<PredictionResponse | null>(null);
  const [gemini, setGemini] = useState<GeminiResponse | null>(null);
  const [coffeeType, setCoffeeType] = useState("robusta");
  const [featureVersion, setFeatureVersion] = useState("generated");
  const [modelKey, setModelKey] = useState("");
  const [date, setDate] = useState("");
  const [loadState, setLoadState] = useState<LoadState>("loading");
  const [geminiLoading, setGeminiLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [markerHover, setMarkerHover] = useState<MarkerHoverState | null>(null);
  const chartStageRef = useRef<HTMLDivElement | null>(null);

  useEffect(() => {
    let cancelled = false;
    fetchMetadata()
      .then((data) => {
        if (cancelled) return;
        setMetadata(data);
        const defaultDates = data.available_dates.robusta?.selected ?? [];
        setDate(defaultDates[defaultDates.length - 1] ?? "");
        setLoadState("idle");
      })
      .catch((err: Error) => {
        if (cancelled) return;
        setError(err.message);
        setLoadState("error");
      });
    return () => {
      cancelled = true;
    };
  }, []);

  const availableDates = useMemo(() => {
    return metadata?.available_dates[coffeeType]?.[featureVersion] ?? [];
  }, [coffeeType, featureVersion, metadata]);

  const availableModels = useMemo(() => {
    return metadata?.available_models[coffeeType]?.[featureVersion] ?? [];
  }, [coffeeType, featureVersion, metadata]);

  const activeSplit = useMemo(() => {
    return prediction?.dataset_split ?? metadata?.dataset_split[coffeeType]?.[featureVersion] ?? null;
  }, [coffeeType, featureVersion, metadata, prediction]);

  useEffect(() => {
    if (!availableDates.length) return;
    if (!date || !availableDates.includes(date)) {
      setDate(availableDates[availableDates.length - 1]);
    }
  }, [availableDates, date]);

  useEffect(() => {
    if (!availableModels.length) return;
    if (!modelKey || !availableModels.some((item) => item.key === modelKey)) {
      setModelKey(availableModels[0].key);
    }
  }, [availableModels, modelKey]);

  useEffect(() => {
    setGemini(null);
    setPrediction(null);
    setError(null);
    setMarkerHover(null);
  }, [coffeeType, featureVersion, date, modelKey]);

  const chartData = useMemo(() => buildChartData(prediction, gemini), [gemini, prediction]);
  const predictionMarkerGroups = useMemo(
    () => buildPredictionMarkerGroups(prediction, gemini),
    [gemini, prediction]
  );

  const surroundingRows = prediction?.surrounding_rows ?? [];

  const selectedCoffeeLabel = metadata?.coffee_types.find((item) => item.value === coffeeType)?.label ?? "Robusta";
  const selectedVersionLabel =
    metadata?.feature_versions.find((item) => item.value === featureVersion)?.label ?? "Gốc + đặc trưng được chọn";
  const selectedModelOption = availableModels.find((item) => item.key === modelKey);
  const selectedModelLabel =
    selectedModelOption?.label ??
    prediction?.selection.model_label ??
    "Đang chọn model";
  const selectedModelMetrics = prediction?.model.metrics ?? selectedModelOption?.metrics ?? {};
  const canPredictWithMl = canRunMlPrediction(date, modelKey, availableDates, availableModels);
  const canPredictWithGemini = canRunGeminiPrediction(Boolean(prediction), loadState, geminiLoading);
  const mlDirectionTone = prediction?.ml_prediction.direction_correct ? "good" : "bad";
  const geminiDirectionTone = gemini?.direction_correct ? "good" : "bad";
  const parsedGeminiOutput = useMemo(() => {
    if (!gemini) return null;
    return {
      predicted_next_price: gemini.predicted_price,
      predicted_direction: gemini.predicted_direction,
      confidence: gemini.confidence,
      rationale: gemini.rationale
    };
  }, [gemini]);

  const handlePredictionMarkerHover = useCallback(
    (group: PredictionMarkerGroup, cx?: number, cy?: number) => {
      if (typeof cx !== "number" || typeof cy !== "number") {
        return;
      }

      const details = buildPredictionMarkerDayDetails(chartData, predictionMarkerGroups, group.date);
      if (!details) {
        return;
      }

      const stageWidth = chartStageRef.current?.clientWidth ?? 0;
      const popoverWidth = 264;
      const edgePadding = 16;
      const minX = edgePadding + popoverWidth / 2;
      const maxX = stageWidth - edgePadding - popoverWidth / 2;
      const x =
        stageWidth > popoverWidth + edgePadding * 2
          ? Math.max(minX, Math.min(maxX, cx))
          : cx;

      setMarkerHover({
        details,
        x,
        y: cy,
        placement: cy < 120 ? "below" : "above"
      });
    },
    [chartData, predictionMarkerGroups]
  );

  const clearPredictionMarkerHover = useCallback(() => {
    setMarkerHover(null);
  }, []);

  async function handleMlPrediction() {
    if (!canPredictWithMl) return;
    setLoadState("loading");
    setError(null);
    setGemini(null);
    setPrediction(null);
    try {
      const data = await fetchPrediction(coffeeType, featureVersion, date, modelKey);
      setPrediction(data);
      setLoadState("idle");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Không thể dự đoán bằng ML");
      setLoadState("error");
    }
  }

  async function handleGemini() {
    if (!canPredictWithGemini) return;
    setGeminiLoading(true);
    setGemini(null);
    try {
      const result = await fetchGeminiPrediction(coffeeType, featureVersion, date, modelKey);
      setGemini(result);
    } catch (err) {
      setGemini(unavailableGeminiResult(err));
    } finally {
      setGeminiLoading(false);
    }
  }

  return (
    <div className="app-shell">
      <div className="ambient ambient-left" />
      <div className="ambient ambient-right" />
      <div className="grain-layer" />

      <Navbar />

      <main className="content">
        <section className="hero">
          <div className="hero-copy">
            <div className="eyebrow">Dashboard Mô Hình</div>
            <h1>Hệ thống dự đoán giá cà phê ngày kế tiếp</h1>
          </div>

          <div className="hero-body">
            <p className="hero-description">
              Theo dõi đầu ra của mô hình ML và Gemini, so sánh trực tiếp với ground truth,
              đồng thời minh bạch phạm vi train, validation, test và dữ liệu đầu vào dùng để dự đoán.
            </p>

            <div className="hero-side">
              <div className="live-chip">
                <span />
                Giám sát mô hình
              </div>
              <div className="hero-note">
                <small>Trạng thái phiên dự đoán</small>
                <strong>{prediction ? "Đã có kết quả ML" : "Đang chờ kích hoạt"}</strong>
                <p>
                  {prediction
                    ? `${sourceLabel(prediction.model.source)} · ${prediction.model.name}`
                    : "Chọn cấu hình trong tập test, sau đó kích hoạt dự đoán để mở phiên đánh giá."}
                </p>
              </div>
            </div>
          </div>

          <div className="context-strip">
            <ContextChip icon={<Coffee size={14} />} label="Loại cà phê" value={selectedCoffeeLabel} />
            <ContextChip icon={<RotateCcw size={14} />} label="Bộ đặc trưng" value={selectedVersionLabel} />
            <ContextChip icon={<Database size={14} />} label="Model" value={selectedModelLabel} />
            <ContextChip icon={<CalendarDays size={14} />} label="Ngày dự đoán" value={date || "-"} />
          </div>
        </section>

        <section className="control-deck">
          <div className="control-grid">
            <div className="control-group">
              <label htmlFor="coffee-type">Loại cà phê</label>
              <select id="coffee-type" value={coffeeType} onChange={(event) => setCoffeeType(event.target.value)}>
                {metadata?.coffee_types.map((option) => (
                  <option key={option.value} value={option.value}>
                    {option.label}
                  </option>
                ))}
              </select>
            </div>

            <div className="control-group">
              <label htmlFor="feature-version">Phiên bản đặc trưng</label>
              <select id="feature-version" value={featureVersion} onChange={(event) => setFeatureVersion(event.target.value)}>
                {metadata?.feature_versions.map((option) => (
                  <option key={option.value} value={option.value}>
                    {option.label}
                  </option>
                ))}
              </select>
            </div>

            <div className="control-group">
              <label htmlFor="model-key">Model ML</label>
              <select id="model-key" value={modelKey} onChange={(event) => setModelKey(event.target.value)}>
                {availableModels.map((option) => (
                  <option key={option.key} value={option.key}>
                    {option.label}
                  </option>
                ))}
              </select>
            </div>

            <div className="control-group">
              <label htmlFor="prediction-date">Ngày dự đoán</label>
              <select id="prediction-date" value={date} onChange={(event) => setDate(event.target.value)}>
                {availableDates.map((item) => (
                  <option key={item} value={item}>
                    {item}
                  </option>
                ))}
              </select>
            </div>
          </div>

          <div className="command-card">
            <div className="action-stack">
              <button className="primary-action" onClick={handleMlPrediction} disabled={!canPredictWithMl || loadState === "loading"}>
                {loadState === "loading" ? <Loader2 className="spin" size={18} /> : <Activity size={18} />}
                Dự đoán bằng ML
              </button>

              <button className="secondary-action" onClick={handleGemini} disabled={!canPredictWithGemini}>
                {geminiLoading ? <Loader2 className="spin" size={18} /> : <Sparkles size={18} />}
                Gọi Gemini dự đoán
              </button>
            </div>

            <div className="command-status">
              <span>Trạng thái</span>
              <strong>{prediction ? "ML đã chạy, sẵn sàng gọi Gemini" : "Chưa có kết quả ML"}</strong>
              <small>
                {prediction
                  ? "Gemini có thể được gọi để đối chiếu cùng một ngày thuộc tập test."
                  : "Kết quả ML chỉ hiện sau khi bấm nút dự đoán, và ngày chọn luôn được khóa trong tập test."}
              </small>
            </div>
          </div>
        </section>

        {error ? <div className="error-banner">{error}</div> : null}

        <section className="duel-stage">
          <div className="stage-rail">
            <MiniStat
              icon={<CircleDollarSign size={16} />}
              label="Giá ngày trước đó"
              value={formatPrice(prediction?.current_price)}
              note={prediction?.selection.reference_date ?? "Chưa có dữ liệu"}
            />
            <MiniStat
              icon={<Database size={16} />}
              label="Ground truth ngày dự đoán"
              value={formatPrice(prediction?.ground_truth.actual_next_price)}
              note={prediction?.selection.date ?? "Sẽ hiện sau khi chạy"}
              tone={prediction?.ground_truth.actual_direction === "UP" ? "up" : "down"}
            />
            <MiniStat
              icon={<Activity size={16} />}
              label="Model đang chọn"
              value={prediction?.model.name ?? selectedModelLabel}
              note={prediction ? sourceLabel(prediction.model.source) : "Sẵn sàng chạy"}
            />
          </div>

          <div className="duel-grid">
            <DuelCard
              accent="ml"
              title="Mô hình ML"
              subtitle={prediction ? prediction.model.name : selectedModelLabel}
              badge={prediction ? (prediction.ml_prediction.direction_correct ? "Đúng hướng" : "Sai hướng") : "Chưa chạy"}
              value={prediction ? formatPrice(prediction.ml_prediction.predicted_price) : "Chờ kích hoạt"}
              status={prediction ? directionLabel(prediction.ml_prediction.predicted_direction) : "Bấm Dự đoán bằng ML"}
              detailA={prediction ? `Sai số ${formatPrice(prediction.ml_prediction.absolute_error)}` : "Kết quả dự báo sẽ hiện tại đây"}
              detailB={prediction ? `Độ lệch ${formatPercent(prediction.ml_prediction.error_pct)}` : "Dựa trên model và bộ đặc trưng đã chọn"}
              tone={prediction ? mlDirectionTone : "neutral"}
            />

            <TruthCore
              ready={Boolean(prediction)}
              currentPrice={formatPrice(prediction?.current_price)}
              actualPrice={formatPrice(prediction?.ground_truth.actual_next_price)}
              actualDirection={prediction ? directionLabel(prediction.ground_truth.actual_direction) : "-"}
              actualChange={formatPercent(prediction?.ground_truth.actual_change_pct)}
              referenceDate={prediction?.selection.reference_date ?? "-"}
              predictionDate={prediction?.selection.date ?? "-"}
            />

            <DuelCard
              accent="gemini"
              title="Gemini"
              subtitle="Suy luận LLM"
              badge={gemini?.available ? (gemini.direction_correct ? "Đúng hướng" : "Sai hướng") : prediction ? "Sẵn sàng gọi" : "Chờ ML"}
              value={gemini?.available ? formatPrice(gemini.predicted_price) : prediction ? "Chờ gọi Gemini" : "Khóa cho đến khi ML chạy"}
              status={gemini?.available ? directionLabel(gemini.predicted_direction) : prediction ? "Sẵn sàng phân tích" : "Đang chờ kết quả ML"}
              detailA={gemini?.available ? `Tin cậy ${formatPercent((gemini.confidence ?? 0) * 100)}` : gemini?.error ?? "Gemini sẽ xuất hiện sau khi anh bấm gọi"}
              detailB={gemini?.available ? `Sai số ${formatPrice(gemini.absolute_error)}` : "Dùng cùng cấu hình đầu vào với ML"}
              tone={gemini?.available ? geminiDirectionTone : "neutral"}
            />
          </div>
        </section>

        <Panel
          title="Phạm vi train, validation và test"
          icon={<Database size={18} />}
          action={activeSplit ? `Ngày đang chọn thuộc ${activeSplit.selected_date_scope.toUpperCase()}` : "Đang nạp split"}
        >
          {activeSplit ? (
            <div className="split-layout">
              <div className="split-banner">
                <strong>Ngày dự đoán hiện tại chỉ được chọn trong tập test.</strong>
                <span>
                  Model không được train trên ngày đang dự đoán. Các khoảng dữ liệu bên dưới được suy ra
                  theo đúng split thời gian 70/15/15 của từng bộ dữ liệu.
                </span>
              </div>

              <div className="split-grid">
                <SplitCard
                  title="Phạm vi train"
                  dateRange={`${activeSplit.train.start_date} -> ${activeSplit.train.end_date}`}
                  count={activeSplit.train.count}
                  tone="train"
                />
                <SplitCard
                  title="Tập validation"
                  dateRange={`${activeSplit.validation.start_date} -> ${activeSplit.validation.end_date}`}
                  count={activeSplit.validation.count}
                  tone="validation"
                />
                <SplitCard
                  title="Tập test"
                  dateRange={`${activeSplit.test.start_date} -> ${activeSplit.test.end_date}`}
                  count={activeSplit.test.count}
                  tone="test"
                />
              </div>
            </div>
          ) : (
            <EmptyPanelState text="Không lấy được thông tin split dữ liệu." />
          )}
        </Panel>

        <Panel
          title="Quỹ đạo giá quanh ngày dự đoán"
          icon={<LineChartIcon size={18} />}
          action={prediction?.selection.date ? `Ground truth: ${prediction.selection.date}` : "Chờ kết quả ML"}
          className="chart-panel"
        >
          <div className="chart-wrap">
            {loadState === "loading" ? (
              <LoadingBlock />
            ) : !prediction ? (
              <EmptyPredictionBlock />
            ) : (
              <>
                <div className="chart-legend" aria-label="Chú thích biểu đồ">
                  <div className="chart-legend__title">Chú thích biểu đồ</div>
                  <div className="chart-legend__items">
                    <LegendLineItem label="Giá lịch sử đến ngày trước đó" color="#3f76b5" />
                    {predictionMarkerSeries.map((series) => (
                      <LegendMarkerItem
                        key={series.key}
                        label={series.label}
                        color={series.color}
                        shape={series.shape}
                      />
                    ))}
                  </div>
                </div>

                <div className="chart-stage" ref={chartStageRef} onMouseLeave={clearPredictionMarkerHover}>
                  <ResponsiveContainer width="100%" height="100%">
                    <ComposedChart data={chartData} margin={{ top: 16, right: 18, bottom: 8, left: 8 }}>
                      <CartesianGrid stroke="rgba(71, 85, 105, 0.14)" vertical={false} />
                      <XAxis dataKey="date" tick={{ fill: "#64748b", fontSize: 12 }} tickMargin={12} minTickGap={36} />
                      <YAxis
                        tick={{ fill: "#64748b", fontSize: 12 }}
                        tickFormatter={(value) => formatCompactPrice(Number(value))}
                        width={62}
                        domain={["dataMin - 1200", "dataMax + 1200"]}
                      />
                      <Tooltip content={<ChartTooltip chartData={chartData} markerGroups={predictionMarkerGroups} />} />
                      <Line
                        type="monotone"
                        dataKey="price"
                        name="Giá lịch sử đến ngày trước đó"
                        stroke="#4f46e5"
                        strokeWidth={3}
                        dot={false}
                        activeDot={{ r: 6, fill: "#4f46e5" }}
                        isAnimationActive
                      />
                      {predictionMarkerGroups.map((group) => (
                        <ReferenceDot
                          key={`${group.date}-${group.value}-${group.entries.map((item) => item.key).join("-")}`}
                          x={group.date}
                          y={group.value}
                          ifOverflow="extendDomain"
                          isFront
                          r={0}
                          fill="transparent"
                          stroke="transparent"
                          shape={(props: { cx?: number; cy?: number }) => (
                            <PredictionMarker
                              {...props}
                              payload={group}
                              onHover={handlePredictionMarkerHover}
                              onLeave={clearPredictionMarkerHover}
                            />
                          )}
                        />
                      ))}
                    </ComposedChart>
                  </ResponsiveContainer>

                  {markerHover ? <PredictionMarkerPopover hover={markerHover} /> : null}
                </div>
              </>
            )}
          </div>
        </Panel>

        <Panel
          title="Dữ liệu xung quanh ngày dự đoán"
          icon={<Database size={18} />}
          action={
            prediction?.selection.reference_date
              ? `${prediction.selection.reference_date} -> ${prediction.selection.date}`
              : "Chờ kết quả ML"
          }
        >
          {surroundingRows.length ? (
            <div className="surrounding-table-wrap">
              <table className="surrounding-table">
                <thead>
                  <tr>
                    <th>Ngày</th>
                    <th>Vai trò</th>
                    <th>Giá VN</th>
                    <th>Close</th>
                    <th>Open</th>
                    <th>High</th>
                    <th>Low</th>
                    <th>Volume</th>
                    <th>% thay đổi</th>
                  </tr>
                </thead>
                <tbody>
                  {surroundingRows.map((row) => (
                    <tr key={row.date} className={row.role}>
                      <td>{row.date}</td>
                      <td>
                        <StatusPill
                          label={rowRoleLabel(row.role)}
                          tone={row.role === "prediction_day" ? "good" : row.role === "reference_day" ? "neutral" : "neutral"}
                        />
                      </td>
                      <td>{formatPrice(row.gia_viet_nam)}</td>
                      <td>{formatNumber(row.close)}</td>
                      <td>{formatNumber(row.open)}</td>
                      <td>{formatNumber(row.high)}</td>
                      <td>{formatNumber(row.low)}</td>
                      <td>{formatNumber(row.volume)}</td>
                      <td>{row.change_pct === null || row.change_pct === undefined ? "-" : formatPercent(row.change_pct * 100)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          ) : (
            <EmptyPanelState text="Bảng dữ liệu xung quanh ngày dự đoán sẽ xuất hiện sau khi chạy ML." />
          )}
        </Panel>

        <section className="intel-grid">
          <Panel
            title="Đánh giá nhanh"
            icon={prediction?.ml_prediction.direction_correct ? <TrendingUp size={18} /> : <TrendingDown size={18} />}
          >
            {prediction ? (
              <div className="verdict-shell">
                <div className="verdict-stack">
                  <StatusBadge
                    correct={prediction.ml_prediction.direction_correct}
                    label={`ML ${prediction.ml_prediction.direction_correct ? "đúng hướng" : "sai hướng"}`}
                  />
                  {gemini?.available ? (
                    <StatusBadge
                      correct={Boolean(gemini.direction_correct)}
                      label={`Gemini ${gemini.direction_correct ? "đúng hướng" : "sai hướng"}`}
                    />
                  ) : (
                    <StatusPill label={gemini?.error ?? "Gemini chưa được gọi"} tone="neutral" />
                  )}
                </div>
                <p className="verdict-copy">
                  {prediction.ml_prediction.direction_correct
                    ? "ML đang bám đúng hướng ground truth trên cấu hình này."
                    : "ML đang lệch hướng so với ground truth, cần đối chiếu thêm với Gemini và các bộ đặc trưng còn lại."}
                </p>
                {gemini?.rationale ? <p className="rationale">{gemini.rationale}</p> : null}
              </div>
            ) : (
              <EmptyPanelState text="Phần đánh giá nhanh sẽ hiện sau khi có kết quả ML." />
            )}
          </Panel>

          <Panel title="Giải thích Gemini" icon={<Bot size={18} />} className="wide-panel">
            <div className="gemini-panel">
              <div className="gemini-status">
                <strong>
                  {gemini
                    ? gemini.available
                      ? "Đã nhận phản hồi từ Gemini"
                      : "Gemini không khả dụng cho lần gọi này"
                    : prediction
                      ? "Chưa gọi Gemini"
                      : "Chờ kết quả ML"}
                </strong>
                <p>
                  {gemini
                    ? "Panel này cho thấy Gemini đã nhận input gì, prompt đầy đủ ra sao, raw output thế nào và hệ thống parse lại thành kết quả gì."
                    : prediction
                      ? "Sau khi bấm gọi Gemini, web sẽ hiển thị đầy đủ Input Gemini, Prompt Gemini, Output Gemini và suy luận đã trả về."
                      : "Cần chạy ML trước để khóa ngày trong tập test và chuẩn bị ngữ cảnh cho Gemini."}
                </p>
              </div>

              <details className="technical-block" open={Boolean(gemini)}>
                <summary>Input Gemini</summary>
                <div className="technical-block__body">
                  <CodeBlock
                    value={
                      gemini
                        ? JSON.stringify(gemini.input_rows, null, 2)
                        : "Chưa có input Gemini. Hãy chạy ML và gọi Gemini để xem các bài báo được gửi đi."
                    }
                  />
                </div>
              </details>

              <details className="technical-block">
                <summary>Prompt Gemini</summary>
                <div className="technical-block__body">
                  <CodeBlock
                    value={
                      gemini?.prompt ??
                      "Chưa có prompt Gemini cho cấu hình hiện tại. Prompt sẽ xuất hiện sau khi gọi Gemini."
                    }
                  />
                </div>
              </details>

              <details className="technical-block">
                <summary>Output Gemini</summary>
                <div className="technical-block__body technical-output">
                  <div>
                    <small>Raw output</small>
                    <CodeBlock value={gemini?.raw_output ?? "Chưa có raw output từ Gemini."} />
                  </div>
                  <div>
                    <small>Parsed output</small>
                    <CodeBlock
                      value={
                        gemini
                          ? JSON.stringify(parsedGeminiOutput, null, 2)
                          : "Chưa có parsed output từ Gemini."
                      }
                    />
                  </div>
                </div>
              </details>

              <div className="rationale-card">
                <small>Suy luận của Gemini</small>
                <p>{gemini?.rationale ?? "Chưa có suy luận vì Gemini chưa được gọi hoặc chưa phản hồi thành công."}</p>
              </div>
            </div>
          </Panel>

        </section>
      </main>
    </div>
  );
}

function Panel({
  title,
  icon,
  action,
  children,
  className
}: {
  title: string;
  icon: React.ReactNode;
  action?: string;
  children: React.ReactNode;
  className?: string;
}) {
  return (
    <section className={`panel ${className ?? ""}`.trim()}>
      <header>
        <div>
          {icon}
          <h2>{title}</h2>
        </div>
        {action ? <span>{action}</span> : null}
      </header>
      {children}
    </section>
  );
}

function ContextChip({
  icon,
  label,
  value
}: {
  icon: React.ReactNode;
  label: string;
  value: string;
}) {
  return (
    <div className="context-chip">
      <div className="context-chip__icon">{icon}</div>
      <div>
        <small>{label}</small>
        <strong>{value}</strong>
      </div>
    </div>
  );
}

function MiniStat({
  icon,
  label,
  value,
  note,
  tone = "neutral"
}: {
  icon: React.ReactNode;
  label: string;
  value: string;
  note: string;
  tone?: "up" | "down" | "neutral";
}) {
  return (
    <article className={`mini-stat ${tone}`}>
      <div className="mini-stat__icon">{icon}</div>
      <div>
        <span>{label}</span>
        <strong>{value}</strong>
        <small>{note}</small>
      </div>
    </article>
  );
}

function DuelCard({
  accent,
  title,
  subtitle,
  badge,
  value,
  status,
  detailA,
  detailB,
  tone
}: {
  accent: "ml" | "gemini";
  title: string;
  subtitle: string;
  badge: string;
  value: string;
  status: string;
  detailA: string;
  detailB: string;
  tone: "good" | "bad" | "neutral";
}) {
  return (
    <article className={`duel-card ${accent}`}>
      <div className="duel-card__head">
        <div>
          <small>{title}</small>
          <strong>{subtitle}</strong>
        </div>
        <StatusPill label={badge} tone={tone} />
      </div>
      <div className="duel-card__value">{value}</div>
      <div className="duel-card__status">{status}</div>
      <div className="duel-card__details">
        <span>{detailA}</span>
        <span>{detailB}</span>
      </div>
    </article>
  );
}

function TruthCore({
  ready,
  currentPrice,
  actualPrice,
  actualDirection,
  actualChange,
  referenceDate,
  predictionDate
}: {
  ready: boolean;
  currentPrice: string;
  actualPrice: string;
  actualDirection: string;
  actualChange: string;
  referenceDate: string;
  predictionDate: string;
}) {
  return (
    <article className={`truth-core ${ready ? "ready" : ""}`}>
      <small>Ground truth</small>
      <strong>{ready ? actualPrice : "Chưa có kết quả"}</strong>
      <p>{ready ? `Hướng ${actualDirection} · ${actualChange}` : "Giá thực tế của ngày dự đoán sẽ là mốc đối chiếu cho toàn bộ màn hình."}</p>
      <dl>
        <div><dt>Ngày trước đó</dt><dd>{ready ? referenceDate : "-"}</dd></div>
        <div><dt>Ngày dự đoán</dt><dd>{ready ? predictionDate : "-"}</dd></div>
      </dl>
    </article>
  );
}

function SplitCard({
  title,
  dateRange,
  count,
  tone
}: {
  title: string;
  dateRange: string;
  count: number;
  tone: "train" | "validation" | "test";
}) {
  return (
    <article className={`split-card ${tone}`}>
      <small>{title}</small>
      <strong>{dateRange}</strong>
      <span>{count} dòng dữ liệu</span>
    </article>
  );
}

function StatusPill({
  label,
  tone
}: {
  label: string;
  tone: "good" | "bad" | "neutral";
}) {
  return <span className={`status-pill ${tone}`}>{label}</span>;
}

function StatusBadge({ correct, label }: { correct: boolean; label: string }) {
  return (
    <span className={`status-badge ${correct ? "ok" : "bad"}`}>
      {correct ? <CheckCircle2 size={18} /> : <XCircle size={18} />}
      {label}
    </span>
  );
}

function LoadingBlock() {
  return (
    <div className="loading-block">
      <Loader2 className="spin" size={28} />
      <span>Đang chạy dự đoán ML và nạp lại ngữ cảnh đánh giá...</span>
    </div>
  );
}

function EmptyPredictionBlock() {
  return (
    <div className="loading-block">
      <Activity size={28} />
      <span>Chọn cấu hình rồi bấm Dự đoán bằng ML để xem kết quả trên ngày thuộc tập test.</span>
    </div>
  );
}

function EmptyPanelState({ text }: { text: string }) {
  return <div className="empty-panel">{text}</div>;
}

function LegendLineItem({ label, color }: { label: string; color: string }) {
  return (
    <div className="chart-legend__item">
      <span className="chart-legend__sample chart-legend__sample--line" style={{ "--legend-color": color } as React.CSSProperties} />
      <span>{label}</span>
    </div>
  );
}

function LegendMarkerItem({
  label,
  color,
  shape
}: {
  label: string;
  color: string;
  shape: "circle" | "diamond" | "square";
}) {
  return (
    <div className="chart-legend__item">
      <span
        className={`chart-legend__sample chart-legend__sample--marker ${shape}`}
        style={{ "--legend-color": color } as React.CSSProperties}
      >
        <i />
      </span>
      <span>{label}</span>
    </div>
  );
}

function PredictionMarker({
  cx,
  cy,
  payload,
  onHover,
  onLeave
}: {
  cx?: number;
  cy?: number;
  payload?: PredictionMarkerGroup;
  onHover?: (group: PredictionMarkerGroup, cx?: number, cy?: number) => void;
  onLeave?: () => void;
}) {
  if (typeof cx !== "number" || typeof cy !== "number" || !payload?.entries.length) {
    return null;
  }

  const handleHover = () => {
    onHover?.(payload, cx, cy);
  };

  if (payload.entries.length > 1) {
    const width = Math.max(36, payload.entries.length * 13 + 16);
    const startX = -((payload.entries.length - 1) * 13) / 2;

    return (
      <g
        transform={`translate(${cx}, ${cy})`}
        onMouseEnter={handleHover}
        onMouseMove={handleHover}
        onMouseLeave={onLeave}
        style={{ cursor: "pointer" }}
      >
        <circle r={18} fill="transparent" />
        <g style={{ filter: "drop-shadow(0 8px 16px rgba(61, 45, 28, 0.16))" }}>
          <rect
            x={-width / 2}
            y={-13}
            width={width}
            height={26}
            rx={13}
            fill="rgba(255, 252, 247, 0.98)"
            stroke="rgba(95, 83, 71, 0.28)"
            strokeWidth={1.5}
          />
          {payload.entries.map((entry, index) => {
            const outer = markerShape(5.5, entry.shape);
            const inner = markerShape(4, entry.shape);
            const core = markerShape(2.05, entry.shape);
            return (
              <g key={entry.key} transform={`translate(${startX + index * 13}, 0)`}>
                <path d={outer} fill="rgba(255, 252, 247, 0.98)" />
                <path d={inner} fill="rgba(255, 252, 247, 0.98)" stroke={entry.color} strokeWidth={2.3} />
                <path d={core} fill={entry.color} />
              </g>
            );
          })}
        </g>
      </g>
    );
  }

  const entry = payload.entries[0];
  const outer = markerShape(11, entry.shape);
  const inner = markerShape(8, entry.shape);
  const core = markerShape(4.25, entry.shape);

  return (
    <g
      transform={`translate(${cx}, ${cy})`}
      onMouseEnter={handleHover}
      onMouseMove={handleHover}
      onMouseLeave={onLeave}
      style={{ cursor: "pointer" }}
    >
      <circle r={16} fill="transparent" />
      <path d={outer} fill="rgba(255, 252, 247, 0.98)" />
      <path d={inner} fill="rgba(255, 252, 247, 0.98)" stroke={entry.color} strokeWidth={3} />
      <path d={core} fill={entry.color} />
    </g>
  );
}

function markerShape(size: number, shape: "circle" | "diamond" | "square") {
  if (shape === "circle") {
    return `M 0 ${-size} A ${size} ${size} 0 1 0 0 ${size} A ${size} ${size} 0 1 0 0 ${-size}`;
  }
  if (shape === "diamond") {
    return `M 0 ${-size} L ${size} 0 L 0 ${size} L ${-size} 0 Z`;
  }
  return `M ${-size} ${-size} L ${size} ${-size} L ${size} ${size} L ${-size} ${size} Z`;
}

function CodeBlock({ value }: { value: string }) {
  return <pre className="code-block">{value}</pre>;
}

function rowRoleLabel(role: string) {
  if (role === "reference_day") {
    return "Ngày trước đó";
  }
  if (role === "prediction_day") {
    return "Ngày dự đoán";
  }
  return "Lân cận";
}

function PredictionMarkerPopover({ hover }: { hover: MarkerHoverState }) {
  return (
    <div
      className={`chart-marker-popover chart-marker-popover--${hover.placement}`}
      style={{ left: `${hover.x}px`, top: `${hover.y}px` }}
    >
      <div className="chart-tooltip">
        <PredictionDayTooltipBody details={hover.details} />
      </div>
    </div>
  );
}

function PredictionDayTooltipBody({ details }: { details: PredictionMarkerDayDetails }) {
  return (
    <>
      <strong>{details.date}</strong>
      {details.historyPrice !== null && details.historyPrice !== undefined ? (
        <span className="chart-tooltip__row">
          <i
            className="chart-tooltip__swatch"
            style={{ "--tooltip-color": "#3f76b5" } as React.CSSProperties}
          />
          Giá lịch sử đến ngày trước đó: {formatPrice(details.historyPrice)}
        </span>
      ) : null}
      {details.entries.map((item) => (
        <span key={item.key} className="chart-tooltip__row">
          <i
            className={`chart-tooltip__swatch ${item.shape}`}
            style={{ "--tooltip-color": item.color } as React.CSSProperties}
          />
          {item.label}: {formatPrice(item.value)}
        </span>
      ))}
    </>
  );
}

function ChartTooltip({
  active,
  label,
  chartData,
  markerGroups
}: {
  active?: boolean;
  label?: string;
  chartData: ChartDatum[];
  markerGroups: PredictionMarkerGroup[];
}) {
  if (!active || !label) return null;
  const details = buildPredictionMarkerDayDetails(chartData, markerGroups, label);
  if (!details) return null;

  return (
    <div className="chart-tooltip">
      <PredictionDayTooltipBody details={details} />
    </div>
  );
}

export default ModelPage;
