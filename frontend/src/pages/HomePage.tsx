import { Link } from 'react-router-dom';
import Navbar from '../components/Navbar';

const PIPELINE_STAGES = [
  {
    step: '01',
    title: 'Thu thập & Phân tích giá',
    desc: 'Dữ liệu lịch sử giá Robusta & Arabica từ sàn ICE và thị trường Việt Nam với phân tích kỹ thuật SMA, OHLC.',
    to: '/charts',
    label: 'Xem biểu đồ',
    color: 'text-blue-600',
    bg: 'bg-blue-50',
    border: 'border-blue-100',
  },
  {
    step: '02',
    title: 'Trích xuất & Phân tích IE',
    desc: 'Tìm kiếm bài báo bóc tách giá LLM & DL theo ngày. Xem scatter chart đối chiếu với ground truth Robusta & Arabica.',
    to: '/search',
    label: 'Tìm kiếm & phân tích',
    color: 'text-violet-600',
    bg: 'bg-violet-50',
    border: 'border-violet-100',
  },
  {
    step: '03',
    title: 'Dự báo giá ngày kế tiếp',
    desc: 'Mô hình ML (Lasso, Ridge, SVR, LightGBM, CatBoost) kết hợp đặc trưng LLM để dự báo. So sánh với Gemini.',
    to: '/model',
    label: 'Mở dashboard',
    color: 'text-indigo-600',
    bg: 'bg-indigo-50',
    border: 'border-indigo-100',
  },
];

export default function HomePage() {
  return (
    <div className="min-h-screen bg-gradient-to-br from-[#f0f4ff] via-[#fdfbfe] to-[#f3efff] font-sans overflow-x-hidden flex flex-col">
      <Navbar />

      <main className="w-full flex-1 px-8 lg:px-20 grid lg:grid-cols-2 gap-16 items-center pb-12">
        <div className="space-y-8">
          <h1 className="text-6xl lg:text-[5rem] font-extrabold leading-[1.05] tracking-tight">
            <span className="text-indigo-600 block mb-3">Market Analysis</span>
            <span className="text-slate-900 block">Performance Dashboard</span>
          </h1>

          <p className="text-lg lg:text-xl text-slate-500 max-w-xl leading-relaxed">
            Hệ thống giám sát toàn diện giá cà phê Robusta &amp; Arabica. Tích hợp trích xuất tin tức bằng LLM, mô hình hóa bất đồng thông tin và dự báo giá ngày kế tiếp.
          </p>

          <div className="flex flex-wrap gap-3 pt-2">
            <Link
              to="/charts"
              className="bg-indigo-600 hover:bg-indigo-700 text-white font-semibold py-3 px-8 rounded-full shadow-[0_8px_20px_rgb(79,70,229,0.3)] transition-all hover:-translate-y-0.5"
            >
              Bắt đầu phân tích
            </Link>
            <Link
              to="/model"
              className="bg-white hover:bg-slate-50 text-slate-700 font-semibold py-3 px-8 rounded-full border border-slate-200 shadow-sm transition-all hover:-translate-y-0.5"
            >
              Dashboard dự báo
            </Link>
          </div>
        </div>

        <div className="relative flex justify-end">
          <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-[120%] h-[120%] bg-white/40 blur-3xl rounded-full pointer-events-none -z-10" />
          <img
            src="/SMA.png"
            alt="Biểu đồ phân tích giá cà phê"
            className="w-full max-w-2xl h-auto rounded-2xl drop-shadow-2xl border border-white/50 relative z-10 hover:scale-[1.02] transition-transform duration-500"
          />
        </div>
      </main>

      <section className="w-full px-8 lg:px-20 pb-16">
        <p className="text-xs font-bold text-slate-400 uppercase tracking-widest mb-6">Pipeline dự án</p>
        <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
          {PIPELINE_STAGES.map((stage) => (
            <Link
              key={stage.step}
              to={stage.to}
              className={`group ${stage.bg} border ${stage.border} rounded-2xl p-5 hover:shadow-md transition-all hover:-translate-y-0.5`}
            >
              <span className={`text-xs font-black uppercase tracking-widest ${stage.color} block mb-3`}>
                Stage {stage.step}
              </span>
              <h3 className="font-bold text-slate-800 mb-2 text-sm">{stage.title}</h3>
              <p className="text-xs text-slate-500 leading-relaxed mb-4">{stage.desc}</p>
              <span className={`text-xs font-bold ${stage.color} group-hover:underline`}>
                {stage.label} →
              </span>
            </Link>
          ))}
        </div>
      </section>
    </div>
  );
}
