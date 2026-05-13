import React, { useEffect, useState } from 'react';
import { useLocation, useNavigate, Link } from 'react-router-dom';
import { Hexagon, ArrowLeft, Loader2, AlertCircle } from 'lucide-react';
import {
  ScatterChart, Scatter, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ReferenceLine, ResponsiveContainer, Cell
} from 'recharts';

// Hàm helper để làm sạch giá (Ví dụ: "96.800 VNĐ/kg" -> 96800)
const cleanPrice = (priceStr: string) => {
  if (!priceStr) return 0;
  const numStr = priceStr.replace(/[^\d]/g, ''); // Xóa mọi ký tự không phải số
  return parseInt(numStr, 10);
};

// Hàm helper parse CSV thô
const parseCSV = (csvText: string, targetDate: string) => {
  const lines = csvText.split('\n');
  const headers = lines[0].toLowerCase().split(',');
  const dateIdx = headers.findIndex(h => h.includes('date'));
  const priceIdx = headers.findIndex(h => h.includes('price'));

  for (let i = 1; i < lines.length; i++) {
    const row = lines[i].split(',');
    if (row[dateIdx] === targetDate && row[priceIdx]) {
      return parseFloat(row[priceIdx]);
    }
  }
  return null;
};

const COLORS = ['#ef4444', '#3b82f6', '#10b981', '#f59e0b', '#8b5cf6', '#ec4899'];

// Custom Tooltip cho biểu đồ
const CustomTooltip = ({ active, payload }: any) => {
  if (active && payload && payload.length) {
    const data = payload[0].payload;
    return (
      <div className="bg-white p-4 border border-slate-200 rounded-xl shadow-xl max-w-xs z-50">
        <p className="font-bold text-indigo-800 border-b pb-2 mb-2">{data.domain}</p>
        <p className="text-sm text-slate-700"><strong>Vùng:</strong> {data.region}</p>
        <p className="text-sm text-red-600 font-bold"><strong>Giá bóc tách:</strong> {data.exact_price}</p>
        <p className="text-xs text-slate-500 mt-2 italic line-clamp-4 bg-slate-50 p-2 rounded">
          "{data.content_snippet}"
        </p>
      </div>
    );
  }
  return null;
};

export default function PaperChartPage() {
  const location = useLocation();
  const navigate = useNavigate();
  
  // Lấy dữ liệu từ Router State
  const { results, queryDate } = location.state || { results: [], queryDate: '' };

  const [groundTruth, setGroundTruth] = useState<{ robusta: number | null, arabica: number | null }>({ robusta: null, arabica: null });
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    // Chặn user nếu truy cập trực tiếp URL mà không qua trang Search
    if (!results.length || !queryDate) {
      setLoading(false);
      return;
    }

    const fetchGroundTruth = async () => {
      try {
        // Đọc 2 file CSV từ thư mục public
        const [resRobusta, resArabica] = await Promise.all([
          fetch('/robusta_vnd.csv').then(res => res.text()),
          fetch('/arabica_vnd.csv').then(res => res.text())
        ]);

        const robustaPrice = parseCSV(resRobusta, queryDate);
        const arabicaPrice = parseCSV(resArabica, queryDate);

        setGroundTruth({ robusta: robustaPrice, arabica: arabicaPrice });
      } catch (error) {
        console.error("Lỗi khi đọc file CSV:", error);
      } finally {
        setLoading(false);
      }
    };

    fetchGroundTruth();
  }, [results, queryDate]);

  if (!results.length) {
    return (
      <div className="min-h-screen bg-slate-50 flex flex-col items-center justify-center p-6">
        <AlertCircle className="w-16 h-16 text-red-400 mb-4" />
        <h2 className="text-2xl font-bold text-slate-700 mb-2">Không có dữ liệu phân tích</h2>
        <p className="text-slate-500 mb-6">Vui lòng thực hiện tìm kiếm trước khi xem biểu đồ.</p>
        <button onClick={() => navigate('/search')} className="bg-indigo-600 text-white px-6 py-2 rounded-lg font-medium">
          Quay lại trang Tìm kiếm
        </button>
      </div>
    );
  }

  // Tiền xử lý dữ liệu để vẽ
  const chartData = results.map((item: any) => ({
    ...item,
    price_num: cleanPrice(item.exact_price)
  }));

  const robustaData = chartData.filter((d: any) => d.target.toLowerCase() === 'robusta');
  const arabicaData = chartData.filter((d: any) => d.target.toLowerCase() === 'arabica');
  
  const uniqueDomains = Array.from(new Set(chartData.map((d: any) => d.domain))) as string[];
  const minPrice = Math.min(...chartData.map((d: any) => d.price_num)) - 2000;
  const maxPrice = Math.max(...chartData.map((d: any) => d.price_num)) + 2000;

  return (
    <div className="min-h-screen bg-gradient-to-br from-[#f0f4ff] via-[#fdfbfe] to-[#f3efff] flex flex-col font-sans">
      {/* Header mini */}
      <nav className="flex items-center justify-between px-8 py-6 max-w-7xl mx-auto w-full">
        <button onClick={() => navigate(-1)} className="flex items-center gap-2 text-slate-600 hover:text-indigo-600 font-medium transition-colors">
          <ArrowLeft className="w-5 h-5" /> Quay lại danh sách
        </button>
        <Link to="/" className="flex items-center gap-2">
          <Hexagon className="w-6 h-6 text-indigo-600 fill-indigo-100" />
          <span className="font-bold text-lg text-slate-800">CoffeeFinance</span>
        </Link>
      </nav>

      <main className="flex-1 max-w-7xl mx-auto w-full px-6 pb-12 flex flex-col gap-8">
        <div className="text-center">
          <h1 className="text-3xl font-extrabold text-slate-800 mb-2">Phân Tích Độ Lệch Giá Truyền Thông</h1>
          <p className="text-slate-500 font-medium">Dữ liệu ghi nhận trong ngày: <span className="text-indigo-600 font-bold">{queryDate}</span></p>
        </div>

        {loading ? (
          <div className="flex justify-center py-20"><Loader2 className="w-10 h-10 animate-spin text-indigo-600" /></div>
        ) : (
          <div className="bg-white p-8 rounded-3xl shadow-sm border border-slate-100 h-[650px]">
            <ResponsiveContainer width="100%" height="100%">
              <ScatterChart margin={{ top: 30, right: 30, bottom: 20, left: 20 }}>
                <CartesianGrid strokeDasharray="3 3" vertical={false} opacity={0.4} />
                <XAxis 
                  dataKey="region" 
                  type="category" 
                  name="Vùng Miền" 
                  tick={{ fill: '#475569', fontWeight: 500 }}
                  allowDuplicatedCategory={true} 
                />
                <YAxis 
                  dataKey="price_num" 
                  type="number" 
                  name="Mức Giá" 
                  domain={[minPrice, maxPrice]} 
                  tickFormatter={(val) => `${(val / 1000)}k`} 
                  tick={{ fill: '#475569', fontWeight: 500 }}
                />
                <Tooltip content={<CustomTooltip />} cursor={{ strokeDasharray: '3 3' }} />
                <Legend verticalAlign="top" height={50} />

                {/* Render Đường Baseline Robusta */}
                {groundTruth.robusta && (
                  <ReferenceLine 
                    y={groundTruth.robusta} 
                    stroke="#ef4444" 
                    strokeDasharray="5 5" 
                    strokeWidth={2}
                    label={{ position: 'insideTopLeft', value: `Ground Truth (Robusta): ${groundTruth.robusta.toLocaleString('vi-VN')} VNĐ`, fill: '#ef4444', fontWeight: 'bold' }} 
                  />
                )}

                {/* Render Đường Baseline Arabica */}
                {groundTruth.arabica && (
                  <ReferenceLine 
                    y={groundTruth.arabica} 
                    stroke="#3b82f6" 
                    strokeDasharray="5 5" 
                    strokeWidth={2}
                    label={{ position: 'insideBottomLeft', value: `Ground Truth (Arabica): ${groundTruth.arabica.toLocaleString('vi-VN')} VNĐ`, fill: '#3b82f6', fontWeight: 'bold' }} 
                  />
                )}

                {/* Render Điểm dữ liệu (Robusta) */}
                <Scatter name="Tin tức Robusta" data={robustaData} shape="circle">
                  {robustaData.map((entry: any, index: number) => (
                    <Cell key={`cell-rob-${index}`} fill={COLORS[uniqueDomains.indexOf(entry.domain) % COLORS.length]} />
                  ))}
                </Scatter>

                {/* Render Điểm dữ liệu (Arabica) - Dùng hình thoi (diamond) để phân biệt */}
                <Scatter name="Tin tức Arabica" data={arabicaData} shape="diamond">
                  {arabicaData.map((entry: any, index: number) => (
                    <Cell key={`cell-ara-${index}`} fill={COLORS[uniqueDomains.indexOf(entry.domain) % COLORS.length]} />
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