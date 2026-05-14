import React, { useEffect, useState } from 'react';
import { useLocation, useNavigate, Link } from 'react-router-dom';
import { Hexagon, ArrowLeft, Loader2, AlertCircle } from 'lucide-react';
import {
  ScatterChart, Scatter, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ReferenceLine, ResponsiveContainer, Cell, ErrorBar
} from 'recharts';

// Hàm helper để làm sạch giá (Ví dụ: "96.800 VNĐ/kg" -> 96800)
const cleanPrice = (priceStr: string) => {
  if (!priceStr) return 0;
  const numStr = priceStr.replace(/[^\d]/g, ''); 
  return parseInt(numStr, 10);
};

// Hàm helper parse CSV thô và LÀM TRÒN SỐ
const parseCSV = (csvText: string, targetDate: string) => {
  const lines = csvText.split('\n');
  if (lines.length < 2) return null;
  const headers = lines[0].toLowerCase().split(',');
  const dateIdx = headers.findIndex(h => h.includes('date'));
  const priceIdx = headers.findIndex(h => h.includes('price'));

  if (dateIdx === -1 || priceIdx === -1) return null;

  for (let i = 1; i < lines.length; i++) {
    const row = lines[i].split(',');
    if (row[dateIdx] === targetDate && row[priceIdx]) {
      // Dùng Math.round để loại bỏ hoàn toàn phần thập phân lẻ
      return Math.round(parseFloat(row[priceIdx])); 
    }
  }
  return null;
};

// Bảng màu phân biệt các Domain báo chí
const COLORS = ['#8b5cf6', '#ec4899', '#10b981', '#f59e0b', '#3b82f6', '#ef4444'];

// Custom Tooltip hiển thị chi tiết khi rê chuột
const CustomTooltip = ({ active, payload }: any) => {
  if (active && payload && payload.length) {
    const data = payload[0].payload; 
    return (
      <div className="bg-white p-5 border border-slate-200 rounded-2xl shadow-xl max-w-sm z-50">
        <p className="font-bold text-indigo-900 border-b pb-2 mb-3 text-lg">{data.domain.toUpperCase()}</p>
        <p className="text-sm text-slate-700 mb-3"><strong>Vùng miền:</strong> {data.region}</p>
        
        <div className="space-y-2 bg-slate-50 p-3 rounded-xl border border-slate-100">
          <p className="text-sm text-red-600 font-bold flex justify-between">
            <span>Giá bóc tách (LLM):</span> 
            <span>{data.price_llm}</span>
          </p>
          <p className="text-sm text-blue-600 font-bold flex justify-between">
            <span>Giá bóc tách (DL):</span> 
            <span>{data.price_dl}</span>
          </p>
          <p className="text-xs text-slate-500 font-medium pt-1 border-t border-slate-200">
            Độ chênh lệch : {Math.abs(data.price_llm_num - data.price_dl_num).toLocaleString('vi-VN')} VNĐ
          </p>
        </div>

        <p className="text-xs text-slate-500 mt-3 italic line-clamp-4 bg-slate-100 p-3 rounded-lg">
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
  
  const { results, queryDate } = location.state || { results: [], queryDate: '' };

  const [groundTruth, setGroundTruth] = useState<{ robusta: number | null, arabica: number | null }>({ robusta: null, arabica: null });
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (!results.length || !queryDate) {
      setLoading(false);
      return;
    }

    const fetchGroundTruth = async () => {
      try {
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


  const chartData = results.map((item: any) => {
    const llmNum = cleanPrice(item.price_llm);
    const dlNum = cleanPrice(item.price_dl);
    return {
      ...item,
      price_llm_num: llmNum,
      price_dl_num: dlNum,
      error_y: [0, dlNum - llmNum] 
    };
  });
  
  const uniqueDomains = Array.from(new Set(chartData.map((d: any) => d.domain))) as string[];
  
  const allRawPrices = chartData.flatMap(d => [d.price_llm_num, d.price_dl_num]);
  if (groundTruth.robusta) allRawPrices.push(groundTruth.robusta);
  if (groundTruth.arabica) allRawPrices.push(groundTruth.arabica);
  
  // TÍNH TOÁN KHOẢNG GIÁ TRỤC Y
  const minPrice = Math.min(...allRawPrices) - 3000;
  const maxPrice = Math.max(...allRawPrices) + 3000;

  return (
    <div className="min-h-screen bg-gradient-to-br from-[#f0f4ff] via-[#fdfbfe] to-[#f3efff] flex flex-col font-sans">
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
          <h1 className="text-3xl font-extrabold text-slate-800 mb-2">Biểu đồ phân tích sự chênh lệch giá giữa các nguồn</h1>
          <p className="text-slate-500 font-medium">Dữ liệu ghi nhận trong ngày: <span className="text-indigo-600 font-bold">{queryDate}</span></p>
        </div>

        {loading ? (
          <div className="flex justify-center py-20"><Loader2 className="w-10 h-10 animate-spin text-indigo-600" /></div>
        ) : (
          <div className="bg-white p-8 rounded-3xl shadow-sm border border-slate-100 h-[680px]">
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
                  type="number" 
                  name="Mức Giá" 
                  domain={[minPrice, maxPrice]} 
                  // SỬA FORMAT TRỤC Y: Định dạng chuẩn 95.700
                  tickFormatter={(val) => Math.round(val).toLocaleString('vi-VN')} 
                  tick={{ fill: '#475569', fontWeight: 500 }}
                />
                
                <Tooltip content={<CustomTooltip />} cursor={{ strokeDasharray: '3 3' }} />
                <Legend verticalAlign="top" height={60} iconType="circle"/>

                {/* --- ĐƯỜNG THAM CHIẾU THỰC TẾ --- */}
                {groundTruth.robusta && (
                  <ReferenceLine 
                    y={groundTruth.robusta} 
                    stroke="#b91c1c" 
                    strokeDasharray="7 7" 
                    strokeWidth={2}
                    // SỬA LẠI FORMAT LABEL: Hiển thị chuẩn 95.700 VNĐ
                    label={{ position: 'insideTopLeft', value: `Thực tế (Robusta): ${groundTruth.robusta.toLocaleString('vi-VN')} VNĐ`, fill: '#b91c1c', fontWeight: 'bold', fontSize: 12 }} 
                  />
                )}

                {groundTruth.arabica && (
                  <ReferenceLine 
                    y={groundTruth.arabica} 
                    stroke="#1d4ed8" 
                    strokeDasharray="7 7" 
                    strokeWidth={2}
                    // SỬA LẠI FORMAT LABEL
                    label={{ position: 'insideBottomLeft', value: `Thực tế (Arabica): ${groundTruth.arabica.toLocaleString('vi-VN')} VNĐ`, fill: '#1d4ed8', fontWeight: 'bold', fontSize: 12 }} 
                  />
                )}

                {/* --- VẼ SỰ KHÁC BIỆT GIỮA 2 MÔ HÌNH --- */}
                <Scatter name="AI bóc tách (LLM)" data={chartData} dataKey="price_llm_num" fill="#ef4444" shape="circle">
                  <ErrorBar dataKey="error_y" width={2} strokeWidth={1.5} stroke="#cbd5e1" direction="y" />
                  {chartData.map((entry, index) => (
                    <Cell key={`cell-llm-${index}`} stroke={COLORS[uniqueDomains.indexOf(entry.domain) % COLORS.length]} strokeWidth={2} r={6}/>
                  ))}
                </Scatter>

                <Scatter name="AI bóc tách (DL)" data={chartData} dataKey="price_dl_num" fill="#3b82f6" shape="diamond">
                  {chartData.map((entry, index) => (
                    <Cell key={`cell-dl-${index}`} stroke={COLORS[uniqueDomains.indexOf(entry.domain) % COLORS.length]} strokeWidth={2}/>
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