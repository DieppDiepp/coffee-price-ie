import { useEffect, useMemo, useState } from 'react';
import {
  AreaChart, Area, ComposedChart, Bar, LineChart, Line,
  XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer,
} from 'recharts';
import Plotly from 'plotly.js-dist-min';
import createPlotlyComponent from 'react-plotly.js/factory';
import Papa from 'papaparse';
import { Activity, BarChart2, Calendar, Download, TrendingUp } from 'lucide-react';
import Navbar from '../components/Navbar';

const Plot = (createPlotlyComponent as any)(Plotly) as React.ComponentType<any>;

const SMA = (data: any[], period: number, key: string) =>
  data.map((item, i) => {
    if (i < period - 1) return { ...item, [`SMA_${period}_${key}`]: null };
    const avg = data.slice(i - period + 1, i + 1).reduce((s, d) => s + (d[key] || 0), 0) / period;
    return { ...item, [`SMA_${period}_${key}`]: avg };
  });

const parseVol = (v: any): number => {
  if (!v) return 0;
  const s = String(v).trim();
  if (s.endsWith('K') || s.endsWith('k')) return parseFloat(s) * 1000;
  if (s.endsWith('M') || s.endsWith('m')) return parseFloat(s) * 1_000_000;
  return parseFloat(s) || 0;
};

const fmtVND = (val: any) => `${Number(val).toLocaleString('vi-VN')} VNĐ`;
const fmtK = (val: any) => `${(Number(val) / 1000).toFixed(0)}k`;

export default function CoffeeChartPage() {
  const [rawData, setRawData] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [activeTab, setActiveTab] = useState('trend');
  const [timeRange, setTimeRange] = useState('ALL');

  useEffect(() => {
    (async () => {
      try {
        const [aRes, rRes] = await Promise.all([
          fetch('/arabica_vnd.csv').then(r => r.text()),
          fetch('/robusta_vnd.csv').then(r => r.text()),
        ]);
        const aRaw = Papa.parse(aRes, { header: true, dynamicTyping: true, skipEmptyLines: true }).data as any[];
        const rRaw = Papa.parse(rRes, { header: true, dynamicTyping: true, skipEmptyLines: true }).data as any[];

        const aMap = new Map(aRaw.map((row: any) => [row.Date, row]));
        let merged: any[] = rRaw.map(r => {
          const a: any = aMap.get(r.Date) || {};
          return {
            date: r.Date,
            rPrice: r.Price,
            rOpen: r.Open, rHigh: r.High, rLow: r.Low,
            rVol: parseVol(r['Vol.']),
            aPrice: a.Price,
            aOpen: a.Open, aHigh: a.High, aLow: a.Low,
            aVol: parseVol(a['Vol.']),
            spread: (a.Price != null && r.Price != null) ? a.Price - r.Price : null,
          };
        }).filter(d => d.date).sort((a, b) => new Date(a.date).getTime() - new Date(b.date).getTime());

        for (const p of [7, 14, 30]) {
          merged = SMA(merged, p, 'rPrice');
          merged = SMA(merged, p, 'aPrice');
        }
        setRawData(merged);
      } catch (e) {
        console.error(e);
      } finally {
        setLoading(false);
      }
    })();
  }, []);

  const filteredData = useMemo(() => {
    if (timeRange === 'ALL' || !rawData.length) return rawData;
    const last = new Date(rawData.at(-1)!.date);
    const days: Record<string, number> = { '1W': 7, '1M': 30, '6M': 180, '1Y': 365 };
    const cutoff = new Date(last);
    cutoff.setDate(cutoff.getDate() - (days[timeRange] ?? 365));
    return rawData.filter(d => new Date(d.date) >= cutoff);
  }, [rawData, timeRange]);

  const TABS = [
    { id: 'trend', label: 'XU HƯỚNG & SMA', icon: TrendingUp },
    { id: 'candle', label: 'NẾN NHẬT (OHLC)', icon: BarChart2 },
    { id: 'volume', label: 'GIÁ & KHỐI LƯỢNG', icon: Activity },
    { id: 'spread', label: 'CHÊNH LỆCH GIÁ', icon: Calendar },
  ];

  const RANGES = ['1W', '1M', '6M', '1Y', 'ALL'];

  const renderTrendSMA = () => (
    <div className="space-y-6 h-full overflow-y-auto pr-2 [&::-webkit-scrollbar]:hidden" style={{ scrollbarWidth: 'none' }}>
      {[
        { title: '1. Xu hướng giá chung (Arabica vs Robusta)', keys: [{ k: 'aPrice', n: 'Arabica', c: '#ef4444' }, { k: 'rPrice', n: 'Robusta', c: '#3b82f6' }] },
        { title: '2. Moving Averages — ROBUSTA', keys: [{ k: 'rPrice', n: 'Giá thực', c: '#94a3b8', dash: '3 3' }, { k: 'SMA_7_rPrice', n: 'SMA 7', c: '#f59e0b' }, { k: 'SMA_14_rPrice', n: 'SMA 14', c: '#10b981' }, { k: 'SMA_30_rPrice', n: 'SMA 30', c: '#8b5cf6' }] },
        { title: '3. Moving Averages — ARABICA', keys: [{ k: 'aPrice', n: 'Giá thực', c: '#94a3b8', dash: '3 3' }, { k: 'SMA_7_aPrice', n: 'SMA 7', c: '#f59e0b' }, { k: 'SMA_14_aPrice', n: 'SMA 14', c: '#10b981' }, { k: 'SMA_30_aPrice', n: 'SMA 30', c: '#8b5cf6' }] },
      ].map(({ title, keys }, idx) => (
        <div key={idx} className="h-[300px] bg-white border border-slate-200 p-5 rounded-2xl shadow-sm">
          <h3 className="text-slate-800 text-sm font-extrabold mb-4">{title}</h3>
          <ResponsiveContainer width="100%" height="90%">
            <LineChart data={filteredData}>
              <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#e2e8f0" />
              <XAxis dataKey="date" hide={idx < 2} tick={{ fill: '#64748b', fontSize: 11 }} minTickGap={50} />
              <YAxis domain={['auto', 'auto']} tick={{ fill: '#64748b', fontSize: 11 }} tickFormatter={fmtK} />
              <Tooltip formatter={(v: any) => fmtVND(v)} />
              <Legend />
              {keys.map(({ k, n, c, dash }) => (
                <Line key={k} type="monotone" dataKey={k} name={n} stroke={c} dot={false} strokeWidth={2} strokeDasharray={dash} />
              ))}
            </LineChart>
          </ResponsiveContainer>
        </div>
      ))}
    </div>
  );

  const renderCandlestick = () => (
    <div className="grid grid-rows-2 gap-4 h-full overflow-y-auto [&::-webkit-scrollbar]:hidden" style={{ scrollbarWidth: 'none' }}>
      {[
        { title: 'Biểu đồ nến: Robusta (VNĐ/kg)', open: 'rOpen', high: 'rHigh', low: 'rLow', close: 'rPrice' },
        { title: 'Biểu đồ nến: Arabica (VNĐ/kg)', open: 'aOpen', high: 'aHigh', low: 'aLow', close: 'aPrice' },
      ].map(({ title, open, high, low, close }) => (
        <div key={title} className="bg-white border border-slate-200 rounded-2xl shadow-sm p-2 h-[350px]">
          <Plot
            data={[{
              x: filteredData.map(d => d.date),
              open: filteredData.map(d => d[open]),
              high: filteredData.map(d => d[high]),
              low: filteredData.map(d => d[low]),
              close: filteredData.map(d => d[close]),
              type: 'candlestick',
              increasing: { line: { color: '#10b981' } },
              decreasing: { line: { color: '#ef4444' } },
            }]}
            layout={{
              title: { text: title, font: { size: 13, color: '#1e293b' } },
              margin: { t: 40, r: 30, l: 55, b: 30 },
              xaxis: { rangeslider: { visible: false }, gridcolor: '#f1f5f9' },
              yaxis: { gridcolor: '#f1f5f9' },
              template: 'plotly_white',
              paper_bgcolor: 'rgba(0,0,0,0)',
              plot_bgcolor: 'rgba(0,0,0,0)',
            }}
            useResizeHandler
            className="w-full h-full"
          />
        </div>
      ))}
    </div>
  );

  const renderSpread = () => (
    <div className="h-full w-full bg-white border border-slate-200 p-6 rounded-2xl shadow-sm flex flex-col">
      <h3 className="text-slate-800 text-lg font-extrabold mb-4">Phân tích Chênh lệch (Spread: Arabica - Robusta)</h3>
      <div className="flex-1">
        <ResponsiveContainer width="100%" height="100%">
          <AreaChart data={filteredData}>
            <defs>
              <linearGradient id="spreadGrad" x1="0" y1="0" x2="0" y2="1">
                <stop offset="5%" stopColor="#8b5cf6" stopOpacity={0.3} />
                <stop offset="95%" stopColor="#8b5cf6" stopOpacity={0} />
              </linearGradient>
            </defs>
            <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#e2e8f0" />
            <XAxis dataKey="date" tick={{ fill: '#64748b', fontSize: 12 }} minTickGap={30} />
            <YAxis tickFormatter={fmtK} tick={{ fill: '#64748b' }} />
            <Tooltip formatter={(v: any) => fmtVND(v)} />
            <Legend />
            <Area type="monotone" dataKey="spread" name="Mức chênh lệch (VND/kg)" stroke="#8b5cf6" strokeWidth={2} fill="url(#spreadGrad)" connectNulls />
          </AreaChart>
        </ResponsiveContainer>
      </div>
    </div>
  );

  const renderVolume = () => (
    <div className="grid grid-rows-2 gap-6 h-full overflow-y-auto [&::-webkit-scrollbar]:hidden" style={{ scrollbarWidth: 'none' }}>
      {[
        { title: 'Giá & Khối lượng — ROBUSTA', priceKey: 'rPrice', volKey: 'rVol', color: '#3b82f6' },
        { title: 'Giá & Khối lượng — ARABICA', priceKey: 'aPrice', volKey: 'aVol', color: '#ef4444' },
      ].map(({ title, priceKey, volKey, color }, idx) => (
        <div key={title} className="bg-white border border-slate-200 p-5 rounded-2xl shadow-sm h-[350px]">
          <h3 className="text-slate-800 text-sm font-extrabold mb-2">{title}</h3>
          <ResponsiveContainer width="100%" height="90%">
            <ComposedChart data={filteredData}>
              <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#e2e8f0" />
              <XAxis dataKey="date" hide={idx === 0} tick={{ fill: '#64748b', fontSize: 11 }} />
              <YAxis yAxisId="left" tick={{ fill: '#64748b', fontSize: 11 }} tickFormatter={fmtK} />
              <YAxis yAxisId="right" orientation="right" tick={{ fill: '#64748b', fontSize: 11 }} />
              <Tooltip formatter={(v: any) => Number(v).toLocaleString('vi-VN')} />
              <Bar yAxisId="right" dataKey={volKey} fill="#cbd5e1" opacity={0.6} name="Volume" />
              <Line yAxisId="left" type="monotone" dataKey={priceKey} stroke={color} strokeWidth={2} dot={false} name="Price" />
            </ComposedChart>
          </ResponsiveContainer>
        </div>
      ))}
    </div>
  );

  if (loading) {
    return (
      <div className="min-h-screen bg-gradient-to-br from-[#f0f4ff] via-[#fdfbfe] to-[#f3efff] flex items-center justify-center text-slate-500 font-bold text-xl">
        Đang tải dữ liệu tài chính...
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gradient-to-br from-[#f0f4ff] via-[#fdfbfe] to-[#f3efff] font-sans flex flex-col">
      <Navbar />

      <div className="flex flex-1 overflow-hidden max-w-[1400px] w-full mx-auto px-4 pb-4">
        <aside className="w-60 bg-white/60 backdrop-blur-md border border-white p-5 flex flex-col gap-3 rounded-3xl shadow-sm z-10 mr-6 shrink-0">
          <p className="text-xs font-bold text-slate-400 uppercase tracking-wider mb-2">Công cụ phân tích</p>
          {TABS.map(({ id, label, icon: Icon }) => (
            <button
              key={id}
              onClick={() => setActiveTab(id)}
              className={`flex items-center gap-3 px-4 py-3 rounded-xl text-xs font-bold transition-all ${
                activeTab === id
                  ? 'bg-indigo-600 text-white shadow-md scale-105'
                  : 'text-slate-600 hover:bg-white hover:shadow-sm'
              }`}
            >
              <Icon size={16} /> {label}
            </button>
          ))}
        </aside>

        <main className="flex-1 flex flex-col gap-4 overflow-hidden">
          <div className="flex justify-between items-center bg-white/60 backdrop-blur-md p-5 rounded-3xl border border-white shadow-sm">
            <div>
              <h1 className="text-xl font-black text-slate-800">
                {TABS.find(t => t.id === activeTab)?.label}
              </h1>
              <div className="flex gap-2 mt-3">
                {RANGES.map(r => (
                  <button
                    key={r}
                    onClick={() => setTimeRange(r)}
                    className={`px-3 py-1.5 rounded-lg text-xs font-bold transition-all ${
                      timeRange === r
                        ? 'bg-indigo-100 text-indigo-700 border-2 border-indigo-200'
                        : 'bg-white text-slate-500 border border-slate-200 hover:border-indigo-300'
                    }`}
                  >
                    {r}
                  </button>
                ))}
              </div>
            </div>
            <div className="flex gap-2">
              <a href="/robusta_vnd.csv" download className="bg-white border border-slate-200 text-slate-700 px-3 py-2 rounded-xl font-bold text-xs flex items-center gap-1.5 hover:bg-slate-50 shadow-sm">
                <Download size={14} /> ROBUSTA
              </a>
              <a href="/arabica_vnd.csv" download className="bg-white border border-slate-200 text-slate-700 px-3 py-2 rounded-xl font-bold text-xs flex items-center gap-1.5 hover:bg-slate-50 shadow-sm">
                <Download size={14} /> ARABICA
              </a>
            </div>
          </div>

          <div className="flex-1 overflow-hidden pb-4">
            {activeTab === 'trend' && renderTrendSMA()}
            {activeTab === 'candle' && renderCandlestick()}
            {activeTab === 'volume' && renderVolume()}
            {activeTab === 'spread' && renderSpread()}
          </div>
        </main>
      </div>
    </div>
  );
}
