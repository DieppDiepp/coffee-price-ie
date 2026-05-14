import React, { useState } from 'react';
import { 
  Hexagon, Search, Calendar, MapPin, TrendingUp, ExternalLink, 
  AlertCircle, Loader2, BarChart2, Sparkles
} from 'lucide-react';
import { Link, useNavigate } from 'react-router-dom';

interface CoffeeNews {
  date: string;
  region: string;
  price_llm: string;
  price_dl: string;
  domain: string;
  url: string;
  content_snippet: string;
}

export default function CoffeeSearchPage() {
  const navigate = useNavigate();
  
  const [queryDate, setQueryDate] = useState('');
  const [results, setResults] = useState<CoffeeNews[]>([]);
  const [marketInsight, setMarketInsight] = useState(''); // State lưu Nhận định AI
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [hasSearched, setHasSearched] = useState(false);

  const handleSearch = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!queryDate) return;

    setLoading(true);
    setError('');
    setHasSearched(true);
    setMarketInsight(''); // Reset lại insight cũ

    try {
      const response = await fetch(`http://localhost:8000/api/v1/coffee-prices?query_date=${queryDate}`);
      
      if (!response.ok) {
        if (response.status === 404) throw new Error('Ngày này chưa có dữ liệu trong hệ thống.');
        throw new Error('Lỗi kết nối máy chủ Backend.');
      }

      // ĐÂY LÀ ĐOẠN ĐÃ ĐƯỢC FIX ĐỂ KHỚP VỚI BE V8.5
      const responseData = await response.json();
      
      // 1. Lấy câu nhận định ra
      setMarketInsight(responseData.market_insight);
      
      // 2. Lấy mảng dữ liệu ra rồi mới filter
      const articleArray: CoffeeNews[] = responseData.data;

      const uniqueData = articleArray.filter((v, i, a) => 
        a.findIndex(t => t.url === v.url && t.price_llm === v.price_llm) === i
      );
      
      setResults(uniqueData);
    } catch (err: any) {
      setError(err.message);
      setResults([]);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-[#f0f4ff] via-[#fdfbfe] to-[#f3efff] font-sans flex flex-col">
      
      <nav className="w-full flex items-center justify-between px-8 lg:px-20 py-6 relative z-10">
        <Link to="/" className="flex items-center gap-3">
          <Hexagon className="w-8 h-8 text-indigo-600 fill-indigo-100" strokeWidth={1.5} />
          <span className="font-bold text-xl tracking-tight text-slate-800">Coffee<span className="text-indigo-600">Finance</span></span>
        </Link>
        <div className="hidden md:flex items-center gap-10 font-medium text-slate-600">
          <Link to="/" className="hover:text-indigo-600 transition-colors">Trang chủ</Link>
          <Link to="/charts" className="hover:text-indigo-600 transition-colors">Biểu đồ phân tích</Link>
          <Link to="/search" className="text-indigo-600">Tìm kiếm thông tin</Link>
        </div>
      </nav>

      <main className="flex-1 max-w-6xl mx-auto w-full px-6 py-10 flex flex-col gap-10">
        <div className="bg-white p-10 rounded-[2.5rem] shadow-sm border border-slate-100 relative overflow-hidden">
           <div className="absolute top-0 right-0 w-64 h-64 bg-indigo-50 rounded-full -mr-32 -mt-32 blur-3xl opacity-50" />
           <div className="relative z-10">
              <h1 className="text-4xl font-black text-slate-800 mb-4">Market Intelligence</h1>
              <p className="text-slate-500 mb-8 max-w-xl text-lg leading-relaxed">
                Truy xuất dữ liệu giao dịch từ hàng ngàn nguồn báo chí. Hệ thống AI tự động bóc tách vùng miền và so sánh giá thực tế.
              </p>
              <form onSubmit={handleSearch} className="flex flex-col md:flex-row gap-4 max-w-3xl">
                <div className="relative flex-1">
                  <Calendar className="absolute left-4 top-1/2 -translate-y-1/2 text-indigo-400 w-5 h-5" />
                  <input
                    type="date"
                    required
                    value={queryDate}
                    onChange={(e) => setQueryDate(e.target.value)}
                    className="w-full pl-12 pr-4 py-4 bg-slate-50 border border-slate-200 rounded-2xl text-slate-700 font-bold focus:ring-2 focus:ring-indigo-500 outline-none transition-all"
                  />
                </div>
                <button type="submit" disabled={loading} className="px-10 py-4 bg-indigo-600 hover:bg-indigo-700 text-white font-bold rounded-2xl transition-all flex items-center justify-center gap-2">
                  {loading ? <Loader2 className="animate-spin" /> : <><Search className="w-5 h-5"/> Tìm kiếm</>}
                </button>
              </form>
           </div>
        </div>

        {hasSearched && !loading && (
          <div className="space-y-6">
            
            {error && (
              <div className="bg-red-50 border border-red-100 p-8 rounded-3xl flex flex-col items-center text-center">
                <AlertCircle className="w-12 h-12 text-red-500 mb-4" />
                <h3 className="text-red-800 font-bold text-xl mb-1">Hệ thống phản hồi trống</h3>
                <p className="text-red-600/80">{error}</p>
              </div>
            )}

            {/* KHỐI HIỂN THỊ CÂU NHẬN ĐỊNH CỦA AI */}
            {!error && marketInsight && (
              <div className="bg-indigo-600 text-white p-8 rounded-[2rem] shadow-xl relative overflow-hidden group">
                <Sparkles className="absolute right-6 top-6 w-12 h-12 text-white/20 group-hover:scale-125 transition-transform" />
                <div className="relative z-10">
                  <h3 className="text-indigo-200 font-bold uppercase tracking-widest text-xs mb-3">Phân tích ban đầu:</h3>
                  <p className="text-xl font-medium leading-relaxed italic">"{marketInsight}"</p>
                </div>
              </div>
            )}

            {!error && results.length > 0 && (
              <>
                <div className="flex justify-between items-center px-4 mt-8">
                  <p className="text-slate-500 font-medium text-lg">Tìm thấy <span className="font-bold text-indigo-600">{results.length}</span> điểm dữ liệu</p>
                  <button 
                    onClick={() => navigate('/paperChart', { state: { results, queryDate } })}
                    className="flex items-center gap-2 bg-emerald-500 hover:bg-emerald-600 text-white px-6 py-3 rounded-xl font-bold transition-all shadow-lg shadow-emerald-200"
                  >
                    <BarChart2 className="w-5 h-5" /> Đối chiếu Ground Truth
                  </button>
                </div>

                <div className="grid gap-6">
                  {results.map((item, index) => (
                    <div key={index} className="bg-white p-6 rounded-[2rem] border border-slate-100 shadow-sm hover:shadow-md transition-all">
                      <div className="flex flex-col gap-4">
                        <span className="text-[10px] font-black uppercase text-slate-400 bg-slate-100 w-fit px-3 py-1 rounded-md">{item.domain}</span>
                        <h4 className="font-bold text-slate-800 flex items-center gap-2"><MapPin className="w-5 h-5 text-indigo-500"/> Khu vực: {item.region || "Toàn quốc"}</h4>
                        <p className="text-sm text-slate-600 italic bg-slate-50 p-4 rounded-xl border-l-4 border-indigo-200 leading-relaxed">"{item.content_snippet}"</p>
                        
                        <div className="flex flex-wrap items-center gap-8 bg-slate-50/70 p-4 rounded-2xl border border-slate-100 mt-2">
                          <div>
                            <span className="text-[10px] font-bold text-slate-400 block mb-1">GIÁ BÓC TÁCH (LLM)</span>
                            <span className="text-red-600 font-black text-xl">{item.price_llm}</span>
                          </div>
                          <div className="w-px bg-slate-200 h-10 hidden sm:block"></div>
                          <div>
                            <span className="text-[10px] font-bold text-slate-400 block mb-1">GIÁ BÓC TÁCH (DL)</span>
                            <span className="text-blue-600 font-black text-xl">{item.price_dl}</span>
                          </div>
                        </div>

                        <div className="flex justify-end pt-2">
                          <a href={item.url} target="_blank" rel="noopener noreferrer" className="flex items-center gap-2 text-indigo-600 font-bold text-sm hover:underline mt-2">
                            Xem nguồn bài viết <ExternalLink className="w-4 h-4" />
                          </a>
                        </div>
                      </div>
                    </div>
                  ))}
                </div>
              </>
            )}
          </div>
        )}
      </main>
    </div>
  );
}