import React, { useState } from 'react';
import { 
  Hexagon, Search, Calendar, MapPin, TrendingUp, ExternalLink, 
  Newspaper, AlertCircle, Loader2, BarChart2, Filter
} from 'lucide-react';
import { Link, useNavigate } from 'react-router-dom';

// Schema dữ liệu chuẩn từ Backend V8.0
interface CoffeeNews {
  date: string;
  region: string;
  exact_price: string;
  target: string; // 'robusta' hoặc 'arabica'
  domain: string;
  url: string;
  content_snippet: string;
}

export default function CoffeeSearchPage() {
  const navigate = useNavigate();
  
  // State Management
  const [queryDate, setQueryDate] = useState('');
  const [results, setResults] = useState<CoffeeNews[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [hasSearched, setHasSearched] = useState(false);

  // Hàm gọi API tới FastAPI Backend
  const handleSearch = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!queryDate) return;

    setLoading(true);
    setError('');
    setHasSearched(true);

    try {
      // Endpoint từ Backend của bạn
      const response = await fetch(`http://localhost:8000/api/v1/coffee-prices?query_date=${queryDate}`);
      
      if (!response.ok) {
        if (response.status === 404) throw new Error('Ngày này chưa có dữ liệu trong hệ thống.');
        throw new Error('Lỗi kết nối máy chủ Backend.');
      }

      const data: CoffeeNews[] = await response.json();
      
      // Khử trùng lặp nhẹ tại Client để đảm bảo UI sạch sẽ
      const uniqueData = data.filter((v, i, a) => 
        a.findIndex(t => t.url === v.url && t.exact_price === v.exact_price) === i
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
    <div className="min-h-screen bg-gradient-to-br from-[#f8faff] via-[#ffffff] to-[#f3f0ff] font-sans flex flex-col">
      
      {/* --- NAVIGATION BAR --- */}
      <nav className="border-b border-slate-100 bg-white/70 backdrop-blur-md sticky top-0 z-50">
        <div className="max-w-7xl mx-auto px-8 py-4 flex items-center justify-between">
          <Link to="/" className="flex items-center gap-3">
            <Hexagon className="w-8 h-8 text-indigo-600 fill-indigo-100" />
            <span className="font-bold text-xl tracking-tight text-slate-800">
              Coffee<span className="text-indigo-600">Finance</span>
            </span>
          </Link>
          <div className="hidden md:flex items-center gap-8 font-semibold text-slate-500">
            <Link to="/" className="hover:text-indigo-600 transition-colors">Tổng quan</Link>
            <Link to="/search" className="text-indigo-600 border-b-2 border-indigo-600 pb-1">Tra cứu giá</Link>
            <Link to="/charts" className="hover:text-indigo-600 transition-colors">Thị trường</Link>
          </div>
        </div>
      </nav>

      {/* --- MAIN SEARCH SECTION --- */}
      <main className="flex-1 max-w-6xl mx-auto w-full px-6 py-10 flex flex-col gap-10">
        
        {/* Search Hero Area */}
        <div className="bg-white p-10 rounded-[2.5rem] shadow-sm border border-slate-100 relative overflow-hidden">
          <div className="absolute top-0 right-0 w-64 h-64 bg-indigo-50 rounded-full -mr-32 -mt-32 blur-3xl opacity-50" />
          
          <div className="relative z-10">
            <h1 className="text-4xl font-black text-slate-800 mb-4">Market Intelligence</h1>
            <p className="text-slate-500 mb-8 max-w-xl text-lg leading-relaxed">
              Truy xuất dữ liệu giao dịch từ hàng ngàn nguồn báo chí. Hệ thống AI tự động bóc tách vùng miền và giá thực tế.
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
              <button 
                type="submit" 
                disabled={loading}
                className="px-10 py-4 bg-indigo-600 hover:bg-indigo-700 text-white font-bold rounded-2xl shadow-lg shadow-indigo-200 transition-all flex items-center justify-center gap-2 disabled:opacity-70"
              >
                {loading ? <Loader2 className="w-5 h-5 animate-spin" /> : <Search className="w-5 h-5" />}
                Tìm kiếm
              </button>
            </form>
          </div>
        </div>

        {/* --- RESULTS DISPLAY --- */}
        {hasSearched && (
          <div className="flex flex-col gap-6">
            
            {loading && (
              <div className="flex flex-col items-center justify-center py-20 text-indigo-600">
                <Loader2 className="w-12 h-12 animate-spin mb-4" />
                <p className="font-bold text-lg animate-pulse">Cỗ máy AI đang quét kho dữ liệu...</p>
              </div>
            )}
            
            {error && !loading && (
              <div className="bg-red-50 border border-red-100 p-8 rounded-3xl flex flex-col items-center text-center">
                <AlertCircle className="w-12 h-12 text-red-500 mb-4" />
                <h3 className="text-red-800 font-bold text-xl mb-1">Hệ thống phản hồi trống</h3>
                <p className="text-red-600/80">{error}</p>
              </div>
            )}

            {!loading && !error && results.length > 0 && (
              <>
                {/* Result Header & Analytics Button */}
                <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-6 px-4">
                  <div className="flex items-center gap-4">
                    <div className="p-3 bg-indigo-100 rounded-2xl">
                      <TrendingUp className="w-6 h-6 text-indigo-600" />
                    </div>
                    <div>
                      <h2 className="text-2xl font-extrabold text-slate-800">
                        Báo cáo ngày {queryDate}
                      </h2>
                      <p className="text-slate-500 text-sm font-medium">Tìm thấy {results.length} điểm dữ liệu tin cậy</p>
                    </div>
                  </div>

                  <button 
                    onClick={() => navigate('/paperChart', { state: { results, queryDate } })}
                    className="flex items-center gap-3 bg-emerald-500 hover:bg-emerald-600 text-white px-8 py-3.5 rounded-2xl font-bold shadow-xl shadow-emerald-100 transition-all transform hover:-translate-y-1"
                  >
                    <BarChart2 className="w-5 h-5" />
                    Đối chiếu Ground Truth
                  </button>
                </div>

                {/* Listing Cards */}
                <div className="grid gap-6">
                  {results.map((item, index) => (
                    <div key={index} className="group bg-white border border-slate-100 p-6 rounded-[2rem] shadow-sm hover:shadow-xl hover:border-indigo-100 transition-all duration-300">
                      <div className="flex flex-col gap-5">
                        
                        {/* Card Header */}
                        <div className="flex items-center justify-between">
                          <div className="flex items-center gap-2">
                            <span className="px-3 py-1 bg-slate-100 text-slate-600 rounded-lg text-[10px] font-black uppercase tracking-tighter">
                              {item.domain}
                            </span>
                            <span className={`px-3 py-1 rounded-lg text-[10px] font-black uppercase tracking-tighter ${
                              item.target === 'robusta' ? 'bg-amber-100 text-amber-700' : 'bg-blue-100 text-blue-700'
                            }`}>
                              {item.target}
                            </span>
                          </div>
                          <div className="text-emerald-600 font-black text-xl tracking-tight">
                            {item.exact_price}
                          </div>
                        </div>

                        {/* Card Body */}
                        <div className="flex items-start gap-4">
                          <div className="mt-1 bg-indigo-50 p-2 rounded-lg">
                            <MapPin className="w-4 h-4 text-indigo-500" />
                          </div>
                          <div>
                            <h4 className="text-slate-800 font-bold mb-2">
                              Khu vực: {item.region || "Toàn quốc"}
                            </h4>
                            <p className="text-slate-500 text-sm leading-relaxed italic bg-slate-50 p-4 rounded-2xl border-l-4 border-indigo-200">
                              "{item.content_snippet}"
                            </p>
                          </div>
                        </div>

                        {/* Card Footer */}
                        <div className="flex justify-end pt-2">
                          <a 
                            href={item.url} 
                            target="_blank" 
                            rel="noopener noreferrer"
                            className="flex items-center gap-2 text-indigo-600 font-bold text-sm hover:underline"
                          >
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