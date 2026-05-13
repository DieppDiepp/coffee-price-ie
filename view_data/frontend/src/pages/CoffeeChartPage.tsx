import React, { useEffect, useState, useMemo } from 'react';
import { 
  LineChart, Line, AreaChart, Area, ComposedChart, Bar, XAxis, YAxis, 
  CartesianGrid, Tooltip, Legend, ResponsiveContainer 
} from 'recharts';
import Plotly from 'plotly.js-dist-min';
import createPlotlyComponent from 'react-plotly.js/factory';
import Papa from 'papaparse';
import { 
  TrendingUp, Activity, BarChart2, Download, Search, Hexagon, Calendar
} from 'lucide-react';
import { Link } from 'react-router-dom';

const Plot = typeof createPlotlyComponent === 'function' 
  ? createPlotlyComponent(Plotly) 
  : (createPlotlyComponent as any).default(Plotly);

// --- HELPER: Tính toán SMA ---
const calculateSMA = (data: any[], period: number, key: string) => {
  return data.map((item, index) => {
    if (index < period - 1) return { ...item, [`SMA_${period}_${key}`]: null };
    const slice = data.slice(index - period + 1, index + 1);
    const sum = slice.reduce((acc, curr) => acc + (curr[key] || 0), 0);
    return { ...item, [`SMA_${period}_${key}`]: sum / period };
  });
};

export default function CoffeeChartPage() {
  const [rawData, setRawData] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [activeTab, setActiveTab] = useState('trend');
  const [timeRange, setTimeRange] = useState('ALL');

  useEffect(() => {
    const loadData = async () => {
      try {
        const [arabicaRes, robustaRes] = await Promise.all([
          fetch('/arabica_vnd.csv').then(res => res.text()),
          fetch('/robusta_vnd.csv').then(res => res.text())
        ]);

        const aRaw = Papa.parse(arabicaRes, { header: true, dynamicTyping: true, skipEmptyLines: true }).data;
        const rRaw = Papa.parse(robustaRes, { header: true, dynamicTyping: true, skipEmptyLines: true }).data;

        let merged = rRaw.map((r: any) => {
          const a: any = aRaw.find((item: any) => item.Date === r.Date) || {};
          return {
            date: r.Date,
            rPrice: r.Gia_Viet_Nam || r.Price,
            rOpen: r.Open, rHigh: r.High, rLow: r.Low, rVol: r['Vol.'] || 0,
            aPrice: a.Gia_Viet_Nam || a.Price,
            aOpen: a.Open, aHigh: a.High, aLow: a.Low, aVol: a['Vol.'] || 0,
            spread: (a.Gia_Viet_Nam || a.Price) - (r.Gia_Viet_Nam || r.Price)
          };
        }).filter(d => d.date).sort((a, b) => new Date(a.date).getTime() - new Date(b.date).getTime());

        [7, 14, 30].forEach(p => {
          merged = calculateSMA(merged, p, 'rPrice');
          merged = calculateSMA(merged, p, 'aPrice');
        });

        setRawData(merged);
      } catch (e) { console.error(e); } finally { setLoading(false); }
    };
    loadData();
  }, []);

  const filteredData = useMemo(() => {
    if (timeRange === 'ALL' || rawData.length === 0) return rawData;
    const lastDate = new Date(rawData[rawData.length - 1].date);
    const filterMap: any = { '1Y': 365, '6M': 180, '1M': 30, '1W': 7 };
    const cutoff = new Date(lastDate);
    cutoff.setDate(cutoff.getDate() - filterMap[timeRange]);
    return rawData.filter(d => new Date(d.date) >= cutoff);
  }, [rawData, timeRange]);

  // --- RENDER COMPONENTS (Light Theme) ---
  const renderTrendSMA = () => (
    // Thêm class [&::-webkit-scrollbar]:hidden để ẩn thanh cuộn nhưng vẫn scroll được
    <div className="space-y-6 h-full overflow-y-auto pr-2 [&::-webkit-scrollbar]:hidden" style={{ scrollbarWidth: 'none', msOverflowStyle: 'none' }}>
      
      <div className="h-[300px] bg-white border border-slate-200 p-5 rounded-2xl shadow-sm">
        <h3 className="text-slate-800 text-sm font-extrabold mb-4">1. Xu hướng Giá chung (Arabica vs Robusta)</h3>
        <ResponsiveContainer width="100%" height="90%">
          <LineChart data={filteredData}>
            <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#e2e8f0" />
            <XAxis dataKey="date" hide />
            <YAxis domain={['auto', 'auto']} tick={{fill: '#64748b', fontSize: 11}} tickFormatter={(val) => `${(val/1000).toFixed(0)}k`}/>
            <Tooltip formatter={(value: any) => `${Number(value).toLocaleString('vi-VN')} VNĐ`} />
            <Line type="monotone" dataKey="aPrice" name="Arabica" stroke="#ef4444" dot={false} strokeWidth={2} />
            <Line type="monotone" dataKey="rPrice" name="Robusta" stroke="#3b82f6" dot={false} strokeWidth={2} />
          </LineChart>
        </ResponsiveContainer>
      </div>

      <div className="h-[300px] bg-white border border-slate-200 p-5 rounded-2xl shadow-sm">
        <h3 className="text-slate-800 text-sm font-extrabold mb-4">2. Phân tích Kỹ thuật: Moving Averages (ROBUSTA)</h3>
        <ResponsiveContainer width="100%" height="90%">
          <LineChart data={filteredData}>
            <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#e2e8f0" />
            <XAxis dataKey="date" hide />
            <YAxis domain={['auto', 'auto']} tick={{fill: '#64748b', fontSize: 11}} tickFormatter={(val) => `${(val/1000).toFixed(0)}k`} />
            <Tooltip formatter={(value: any) => `${Number(value).toLocaleString('vi-VN')} VNĐ`} />
            <Line type="monotone" dataKey="rPrice" name="Giá thực" stroke="#94a3b8" dot={false} strokeDasharray="3 3" />
            <Line type="monotone" dataKey="SMA_7_rPrice" name="R-SMA 7" stroke="#f59e0b" dot={false} strokeWidth={2} />
            <Line type="monotone" dataKey="SMA_14_rPrice" name="R-SMA 14" stroke="#10b981" dot={false} strokeWidth={2} />
            <Line type="monotone" dataKey="SMA_30_rPrice" name="R-SMA 30" stroke="#8b5cf6" dot={false} strokeWidth={2} />
          </LineChart>
        </ResponsiveContainer>
      </div>

      <div className="h-[300px] bg-white border border-slate-200 p-5 rounded-2xl shadow-sm">
        <h3 className="text-slate-800 text-sm font-extrabold mb-4">3. Phân tích Kỹ thuật: Moving Averages (ARABICA)</h3>
        <ResponsiveContainer width="100%" height="90%">
          <LineChart data={filteredData}>
            <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#e2e8f0" />
            <XAxis dataKey="date" tick={{fill: '#64748b', fontSize: 11}} minTickGap={50} />
            <YAxis domain={['auto', 'auto']} tick={{fill: '#64748b', fontSize: 11}} tickFormatter={(val) => `${(val/1000).toFixed(0)}k`} />
            <Tooltip formatter={(value: any) => `${Number(value).toLocaleString('vi-VN')} VNĐ`} />
            <Line type="monotone" dataKey="aPrice" name="Giá thực" stroke="#94a3b8" dot={false} strokeDasharray="3 3" />
            <Line type="monotone" dataKey="SMA_7_aPrice" name="A-SMA 7" stroke="#f59e0b" dot={false} strokeWidth={2} />
            <Line type="monotone" dataKey="SMA_14_aPrice" name="A-SMA 14" stroke="#10b981" dot={false} strokeWidth={2} />
            <Line type="monotone" dataKey="SMA_30_aPrice" name="A-SMA 30" stroke="#8b5cf6" dot={false} strokeWidth={2} />
          </LineChart>
        </ResponsiveContainer>
      </div>
    </div>
  );

  const renderCandlestick = () => {
    if (!filteredData || filteredData.length === 0) return null;
    return (
      <div className="grid grid-rows-2 gap-4 h-full [&::-webkit-scrollbar]:hidden" style={{ overflowY: 'auto', msOverflowStyle: 'none', scrollbarWidth: 'none' }}>
        {/* Nến Robusta */}
        <div className="bg-white border border-slate-200 rounded-2xl shadow-sm p-2 h-[350px]">
          <Plot
            data={[{
              x: filteredData.map(d => d.date), open: filteredData.map(d => d.rOpen),
              high: filteredData.map(d => d.rHigh), low: filteredData.map(d => d.rLow), close: filteredData.map(d => d.rPrice),
              type: 'candlestick', name: 'Robusta', increasing: { line: { color: '#10b981' } }, decreasing: { line: { color: '#ef4444' } },
            }]}
            layout={{
              title: { text: 'Biểu đồ Nến: Robusta (VND/kg)', font: { size: 14, color: '#1e293b' } },
              margin: { t: 40, r: 40, l: 60, b: 30 }, xaxis: { rangeslider: { visible: false }, gridcolor: '#f1f5f9' },
              yaxis: { gridcolor: '#f1f5f9' }, template: 'plotly_white', paper_bgcolor: 'rgba(0,0,0,0)', plot_bgcolor: 'rgba(0,0,0,0)'
            }}
            useResizeHandler className="w-full h-full"
          />
        </div>
        {/* Nến Arabica */}
        <div className="bg-white border border-slate-200 rounded-2xl shadow-sm p-2 h-[350px]">
          <Plot
            data={[{
              x: filteredData.map(d => d.date), open: filteredData.map(d => d.aOpen),
              high: filteredData.map(d => d.aHigh), low: filteredData.map(d => d.aLow), close: filteredData.map(d => d.aPrice),
              type: 'candlestick', name: 'Arabica', increasing: { line: { color: '#10b981' } }, decreasing: { line: { color: '#ef4444' } },
            }]}
            layout={{
              title: { text: 'Biểu đồ Nến: Arabica (VND/kg)', font: { size: 14, color: '#1e293b' } },
              margin: { t: 40, r: 40, l: 60, b: 30 }, xaxis: { rangeslider: { visible: false }, gridcolor: '#f1f5f9' },
              yaxis: { gridcolor: '#f1f5f9' }, template: 'plotly_white', paper_bgcolor: 'rgba(0,0,0,0)', plot_bgcolor: 'rgba(0,0,0,0)'
            }}
            useResizeHandler className="w-full h-full"
          />
        </div>
      </div>
    );
  };

  const renderSpreadChart = () => (
    <div className="h-full w-full bg-white border border-slate-200 p-6 rounded-2xl shadow-sm flex flex-col">
      <h3 className="text-slate-800 text-lg font-extrabold mb-4">Phân tích Chênh lệch (Spread: Arabica - Robusta)</h3>
      <div className="flex-1">
        <ResponsiveContainer width="100%" height="100%">
          <AreaChart data={filteredData}>
            <defs>
              <linearGradient id="colorSpread" x1="0" y1="0" x2="0" y2="1">
                <stop offset="5%" stopColor="#8b5cf6" stopOpacity={0.3}/>
                <stop offset="95%" stopColor="#8b5cf6" stopOpacity={0}/>
              </linearGradient>
            </defs>
            <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#e2e8f0" />
            <XAxis dataKey="date" tick={{fill: '#64748b', fontSize: 12}} minTickGap={30} />
            <YAxis tickFormatter={(val) => `${(val/1000).toFixed(0)}k`} tick={{fill: '#64748b'}} />
            <Tooltip formatter={(value: any) => `${Number(value).toLocaleString('vi-VN')} VNĐ`} />
            <Legend />
            <Area type="monotone" dataKey="spread" name="Mức chênh lệch (VND/kg)" stroke="#8b5cf6" strokeWidth={2} fill="url(#colorSpread)" />
          </AreaChart>
        </ResponsiveContainer>
      </div>
    </div>
  );

  const renderVolumeAnalysis = () => (
    <div className="grid grid-rows-2 gap-6 h-full [&::-webkit-scrollbar]:hidden" style={{ overflowY: 'auto', msOverflowStyle: 'none', scrollbarWidth: 'none' }}>
      <div className="bg-white border border-slate-200 p-5 rounded-2xl shadow-sm h-[350px]">
        <h3 className="text-slate-800 text-sm font-extrabold mb-2">Giá & Khối lượng (ROBUSTA)</h3>
        <ResponsiveContainer width="100%" height="90%">
          <ComposedChart data={filteredData}>
            <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#e2e8f0" />
            <XAxis dataKey="date" hide />
            <YAxis yAxisId="left" tick={{fill: '#64748b', fontSize: 11}} tickFormatter={(val) => `${(val/1000).toFixed(0)}k`} />
            <YAxis yAxisId="right" orientation="right" tick={{fill: '#64748b', fontSize: 11}} />
            <Tooltip formatter={(value: any) => Number(value).toLocaleString('vi-VN')} />
            <Bar yAxisId="right" dataKey="rVol" fill="#cbd5e1" opacity={0.6} name="Volume" />
            <Line yAxisId="left" type="monotone" dataKey="rPrice" stroke="#3b82f6" strokeWidth={2} dot={false} name="Price" />
          </ComposedChart>
        </ResponsiveContainer>
      </div>
      <div className="bg-white border border-slate-200 p-5 rounded-2xl shadow-sm h-[350px]">
        <h3 className="text-slate-800 text-sm font-extrabold mb-2">Giá & Khối lượng (ARABICA)</h3>
        <ResponsiveContainer width="100%" height="90%">
          <ComposedChart data={filteredData}>
            <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#e2e8f0" />
            <XAxis dataKey="date" tick={{fill: '#64748b', fontSize: 11}} />
            <YAxis yAxisId="left" tick={{fill: '#64748b', fontSize: 11}} tickFormatter={(val) => `${(val/1000).toFixed(0)}k`} />
            <YAxis yAxisId="right" orientation="right" tick={{fill: '#64748b', fontSize: 11}} />
            <Tooltip formatter={(value: any) => Number(value).toLocaleString('vi-VN')} />
            <Bar yAxisId="right" dataKey="aVol" fill="#cbd5e1" opacity={0.6} name="Volume" />
            <Line yAxisId="left" type="monotone" dataKey="aPrice" stroke="#ef4444" strokeWidth={2} dot={false} name="Price" />
          </ComposedChart>
        </ResponsiveContainer>
      </div>
    </div>
  );

  if (loading) return <div className="min-h-screen flex items-center justify-center font-bold text-slate-500 text-xl bg-[#f0f4ff]">Đang đồng bộ dữ liệu tài chính...</div>;

  return (
    <div className="min-h-screen bg-gradient-to-br from-[#f0f4ff] via-[#fdfbfe] to-[#f3efff] font-sans flex flex-col">
      {/* --- HEADER NAVIGATION (Chuẩn HomePage) --- */}
      <nav className="flex items-center justify-between px-8 py-6 max-w-7xl mx-auto relative z-10 w-full">
        <Link to="/" className="flex items-center gap-3 cursor-pointer">
          <Hexagon className="w-8 h-8 text-indigo-600 fill-indigo-100" strokeWidth={1.5} />
          <span className="font-bold text-xl tracking-tight text-slate-800">
            Coffee<span className="text-indigo-600">Finance</span>
          </span>
        </Link>
        
        <div className="hidden md:flex items-center gap-10 font-medium text-slate-600">
          <Link to="/" className="hover:text-indigo-600 transition-colors">
            Trang chủ
          </Link>
          <Link to="/charts" className="text-indigo-600 border-b-2 border-indigo-600 pb-1">
            Biểu đồ phân tích
          </Link>
          <Link to="/search" className="hover:text-indigo-600 transition-colors">
            Tìm kiếm thông tin
          </Link>
        </div>
      </nav>

      {/* --- MAIN LAYOUT --- */}
      <div className="flex flex-1 overflow-hidden max-w-[1400px] w-full mx-auto px-4 pb-4">
        
        {/* SIDEBAR (Light Theme) */}
        <aside className="w-64 bg-white/60 backdrop-blur-md border border-white p-6 flex flex-col gap-3 rounded-3xl shadow-sm z-10 mr-6">
          <p className="text-xs font-bold text-slate-400 uppercase tracking-wider mb-2">Công cụ Phân tích</p>
          {[
            { id: 'trend', label: 'XU HƯỚNG & SMA', icon: TrendingUp },
            { id: 'candle', label: 'NẾN NHẬT (OHLC)', icon: BarChart2 },
            { id: 'volume', label: 'GIÁ & KHỐI LƯỢNG', icon: Activity },
            { id: 'spread', label: 'CHÊNH LỆCH GIÁ', icon: Calendar },
          ].map(tab => (
            <button 
              key={tab.id} 
              onClick={() => setActiveTab(tab.id)} 
              className={`flex items-center gap-3 px-4 py-3.5 rounded-xl text-xs font-bold transition-all ${
                activeTab === tab.id 
                  ? 'bg-indigo-600 text-white shadow-md transform scale-105' 
                  : 'text-slate-600 hover:bg-white hover:shadow-sm'
              }`}
            >
              <tab.icon size={18} /> {tab.label}
            </button>
          ))}
        </aside>

        {/* MAIN CONTENT AREA */}
        <main className="flex-1 flex flex-col gap-6 overflow-hidden relative">
          {/* Top Controls */}
          <div className="flex justify-between items-center bg-white/60 backdrop-blur-md p-6 rounded-3xl border border-white shadow-sm">
            <div>
              <h1 className="text-2xl font-black text-slate-800">
                {activeTab === 'trend' && 'Đường Trung bình Động (Moving Average)'}
                {activeTab === 'candle' && 'Phân tích Biểu đồ Nến Nhật Bản'}
                {activeTab === 'volume' && 'Tương quan Giá & Khối lượng Giao dịch'}
                {activeTab === 'spread' && 'Độ mở rộng Chênh lệch Giá (Spread)'}
              </h1>
              <div className="flex gap-2 mt-3">
                {['1W', '1M', '6M', '1Y', 'ALL'].map(r => (
                  <button 
                    key={r} 
                    onClick={() => setTimeRange(r)} 
                    className={`px-4 py-1.5 rounded-lg text-xs font-bold transition-all ${
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
            
            <div className="flex gap-3">
              <a href="/robusta_vnd.csv" download className="bg-white border border-slate-200 text-slate-700 px-4 py-2.5 rounded-xl font-bold text-xs flex items-center gap-2 hover:bg-slate-50 transition-colors shadow-sm"><Download size={16}/> ROBUSTA.CSV</a>
              <a href="/arabica_vnd.csv" download className="bg-white border border-slate-200 text-slate-700 px-4 py-2.5 rounded-xl font-bold text-xs flex items-center gap-2 hover:bg-slate-50 transition-colors shadow-sm"><Download size={16}/> ARABICA.CSV</a>
            </div>
          </div>

          {/* Chart Viewport */}
          <div className="flex-1 relative pb-4">
            {activeTab === 'trend' && renderTrendSMA()}
            {activeTab === 'candle' && renderCandlestick()}
            {activeTab === 'volume' && renderVolumeAnalysis()}
            {activeTab === 'spread' && renderSpreadChart()}
          </div>
        </main>
      </div>
    </div>
  );
}