import { useEffect, useState } from 'react';
import { useLocation, useNavigate } from 'react-router-dom';
import { AlertCircle, ArrowLeft, Loader2 } from 'lucide-react';
import {
  CartesianGrid, Cell, ErrorBar, Legend, ReferenceLine,
  ResponsiveContainer, Scatter, ScatterChart, Tooltip, XAxis, YAxis,
} from 'recharts';
import Navbar from '../components/Navbar';

const cleanPrice = (s: string): number => {
  if (!s) return 0;
  const n = String(s).replace(/[^\d]/g, '');
  return n ? parseInt(n, 10) : 0;
};

const parseCSV = (csv: string, targetDate: string): number | null => {
  // arabica CSV wraps each row in outer quotes — strip them first
  const cleanLines = csv.trim().split('\n').map(line => {
    const t = line.trim();
    return (t.startsWith('"') && t.endsWith('"')) ? t.slice(1, -1) : t;
  });
  if (cleanLines.length < 2) return null;
  const headers = cleanLines[0].toLowerCase().split(',');
  const dateIdx = headers.findIndex(h => h.includes('date'));
  const priceIdx = headers.findIndex(h => h.includes('gia_viet_nam') || h.includes('price'));
  if (dateIdx === -1 || priceIdx === -1) return null;
  for (let i = 1; i < cleanLines.length; i++) {
    const row = cleanLines[i].split(',');
    if (!row[dateIdx]) continue;
    // Normalize MM/DD/YYYY → YYYY-MM-DD (arabica format)
    const raw = row[dateIdx].trim();
    const m = raw.match(/^(\d{1,2})\/(\d{1,2})\/(\d{4})$/);
    const normalized = m ? `${m[3]}-${m[1].padStart(2, '0')}-${m[2].padStart(2, '0')}` : raw;
    if (normalized === targetDate && row[priceIdx]) {
      return Math.round(parseFloat(row[priceIdx]));
    }
  }
  return null;
};

const COLORS = ['#8b5cf6', '#ec4899', '#10b981', '#f59e0b', '#3b82f6', '#ef4444'];

const CustomTooltip = ({ active, payload }: any) => {
  if (!active || !payload?.length) return null;
  const d = payload[0].payload;
  return (
    <div className="bg-white p-5 border border-slate-200 rounded-2xl shadow-xl max-w-sm z-50">
      <p className="font-bold text-indigo-900 border-b pb-2 mb-3 text-lg">{d.domain?.toUpperCase()}</p>
      <p className="text-sm text-slate-700 mb-3"><strong>Vùng miền:</strong> {d.region}</p>
      <div className="space-y-2 bg-slate-50 p-3 rounded-xl border border-slate-100">
        <p className="text-sm text-red-600 font-bold flex justify-between">
          <span>Giá bóc tách (LLM):</span><span>{d.price_llm}</span>
        </p>
        <p className="text-sm text-blue-600 font-bold flex justify-between">
          <span>Giá bóc tách (DL):</span><span>{d.price_dl}</span>
        </p>
        <p className="text-xs text-slate-500 font-medium pt-1 border-t border-slate-200">
          Chênh lệch: {Math.abs(d.price_llm_num - d.price_dl_num).toLocaleString('vi-VN')} VNĐ
        </p>
      </div>
      <p className="text-xs text-slate-500 mt-3 italic line-clamp-4 bg-slate-100 p-3 rounded-lg">
        "{d.content_snippet}"
      </p>
    </div>
  );
};

export default function PaperChartPage() {
  const location = useLocation();
  const navigate = useNavigate();
  const { results = [], queryDate = '' } = (location.state || {}) as { results: any[]; queryDate: string };

  const [groundTruth, setGroundTruth] = useState<{ robusta: number | null; arabica: number | null }>({ robusta: null, arabica: null });
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (!results.length || !queryDate) { setLoading(false); return; }
    (async () => {
      try {
        const [rText, aText] = await Promise.all([
          fetch('/robusta_vnd.csv').then(r => r.text()),
          fetch('/arabica_vnd.csv').then(r => r.text()),
        ]);
        setGroundTruth({ robusta: parseCSV(rText, queryDate), arabica: parseCSV(aText, queryDate) });
      } catch { /* keep nulls */ }
      finally { setLoading(false); }
    })();
  }, [results, queryDate]);

  if (!results.length) {
    return (
      <div className="min-h-screen bg-gradient-to-br from-[#f0f4ff] via-[#fdfbfe] to-[#f3efff] flex flex-col items-center justify-center p-6">
        <AlertCircle className="w-16 h-16 text-red-400 mb-4" />
        <h2 className="text-2xl font-bold text-slate-700 mb-2">Không có dữ liệu phân tích</h2>
        <p className="text-slate-500 mb-6">Vui lòng thực hiện tìm kiếm trước khi xem biểu đồ.</p>
        <button onClick={() => navigate('/search')} className="bg-indigo-600 text-white px-6 py-2 rounded-lg font-medium">
          Quay lại trang Tìm kiếm
        </button>
      </div>
    );
  }

  const chartData = results.map((item: any) => {
    const llm = cleanPrice(item.price_llm);
    const dl = cleanPrice(item.price_dl);
    return {
      ...item,
      region: (item.region && item.region !== '.') ? item.region : 'Toàn quốc',
      price_llm_num: llm,
      price_dl_num: dl,
      error_y: (llm > 0 && dl > 0) ? [0, dl - llm] : [0, 0],
    };
  });

  const llmData = chartData.filter((d: any) => d.price_llm_num > 0);
  const dlData = chartData.filter((d: any) => d.price_dl_num > 0);

  const uniqueDomains = Array.from(new Set(chartData.map((d: any) => d.domain))) as string[];
  const allPrices = [
    ...llmData.map((d: any) => d.price_llm_num),
    ...dlData.map((d: any) => d.price_dl_num),
  ];
  if (groundTruth.robusta) allPrices.push(groundTruth.robusta);
  if (groundTruth.arabica) allPrices.push(groundTruth.arabica);
  const minY = Math.min(...allPrices) - 3000;
  const maxY = Math.max(...allPrices) + 3000;

  return (
    <div className="min-h-screen bg-gradient-to-br from-[#f0f4ff] via-[#fdfbfe] to-[#f3efff] flex flex-col font-sans">
      <Navbar />

      <main className="flex-1 max-w-7xl mx-auto w-full px-6 pb-12 flex flex-col gap-8">
        <div className="text-center">
          <h1 className="text-3xl font-extrabold text-slate-800 mb-2">
            Biểu đồ chênh lệch giá giữa các nguồn
          </h1>
          <p className="text-slate-500 font-medium">
            Dữ liệu ghi nhận ngày:{' '}
            <span className="text-indigo-600 font-bold">{queryDate}</span>
          </p>
        </div>

        <button
          onClick={() => navigate(-1)}
          className="flex items-center gap-2 text-slate-600 hover:text-indigo-600 font-medium transition-colors w-fit"
        >
          <ArrowLeft className="w-5 h-5" /> Quay lại danh sách
        </button>

        {loading ? (
          <div className="flex justify-center py-20">
            <Loader2 className="w-10 h-10 animate-spin text-indigo-600" />
          </div>
        ) : (
          <div className="bg-white p-8 rounded-3xl shadow-sm border border-slate-100 h-[680px]">
            <ResponsiveContainer width="100%" height="100%">
              <ScatterChart margin={{ top: 30, right: 30, bottom: 20, left: 20 }}>
                <CartesianGrid strokeDasharray="3 3" vertical={false} opacity={0.4} />
                <XAxis
                  dataKey="region"
                  type="category"
                  name="Vùng miền"
                  tick={{ fill: '#475569', fontWeight: 500 }}
                  allowDuplicatedCategory
                />
                <YAxis
                  type="number"
                  name="Mức giá"
                  domain={[minY, maxY]}
                  tickFormatter={val => Math.round(val).toLocaleString('vi-VN')}
                  tick={{ fill: '#475569', fontWeight: 500 }}
                />
                <Tooltip content={<CustomTooltip />} cursor={{ strokeDasharray: '3 3' }} />
                <Legend verticalAlign="top" height={60} iconType="circle" />

                {groundTruth.robusta && (
                  <ReferenceLine
                    y={groundTruth.robusta}
                    stroke="#b91c1c"
                    strokeDasharray="7 7"
                    strokeWidth={2}
                    label={{
                      position: 'insideTopLeft',
                      value: `Thực tế Robusta: ${groundTruth.robusta.toLocaleString('vi-VN')} VNĐ`,
                      fill: '#b91c1c', fontWeight: 'bold', fontSize: 12,
                    }}
                  />
                )}
                {groundTruth.arabica && (
                  <ReferenceLine
                    y={groundTruth.arabica}
                    stroke="#1d4ed8"
                    strokeDasharray="7 7"
                    strokeWidth={2}
                    label={{
                      position: 'insideBottomLeft',
                      value: `Thực tế Arabica: ${groundTruth.arabica.toLocaleString('vi-VN')} VNĐ`,
                      fill: '#1d4ed8', fontWeight: 'bold', fontSize: 12,
                    }}
                  />
                )}

                <Scatter name="LLM" data={llmData} dataKey="price_llm_num" fill="#ef4444" shape="circle">
                  <ErrorBar dataKey="error_y" width={2} strokeWidth={1.5} stroke="#cbd5e1" direction="y" />
                  {llmData.map((_: any, i: number) => (
                    <Cell key={i} stroke={COLORS[uniqueDomains.indexOf(llmData[i].domain) % COLORS.length]} strokeWidth={2} r={6} />
                  ))}
                </Scatter>

                <Scatter name="Deep Learning" data={dlData} dataKey="price_dl_num" fill="#3b82f6" shape="diamond">
                  {dlData.map((_: any, i: number) => (
                    <Cell key={i} stroke={COLORS[uniqueDomains.indexOf(dlData[i].domain) % COLORS.length]} strokeWidth={2} />
                  ))}
                </Scatter>
              </ScatterChart>
            </ResponsiveContainer>
          </div>
        )}
      </main>
    </div>
  );
}
