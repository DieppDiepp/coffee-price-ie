import React from 'react';
import { Hexagon } from 'lucide-react'; 

export default function HomePage() {
  return (
    // Thêm flex flex-col để chia không gian màn hình hoàn hảo
    <div className="min-h-screen bg-gradient-to-br from-[#f0f4ff] via-[#fdfbfe] to-[#f3efff] font-sans overflow-hidden flex flex-col">
      
      {/* Navbar / Thanh điều hướng - Đổi thành w-full và tăng padding 2 bên */}
      <nav className="w-full flex items-center justify-between px-8 lg:px-20 py-6 relative z-10">
        <div className="flex items-center gap-3 cursor-pointer">
          <Hexagon className="w-8 h-8 text-indigo-600 fill-indigo-100" strokeWidth={1.5} />
          <span className="font-bold text-xl tracking-tight text-slate-800">
            Coffee<span className="text-indigo-600">Finance</span>
          </span>
        </div>
        
        <div className="hidden md:flex items-center gap-10 font-medium text-slate-600">
          <a href="#" className="text-indigo-600 hover:text-indigo-800 transition-colors">
            Trang chủ
          </a>
          <a href="charts" className="hover:text-indigo-600 transition-colors">
            Biểu đồ phân tích
          </a>
          <a href="search" className="hover:text-indigo-600 transition-colors">
            Tìm kiếm thông tin
          </a>
        </div>
      </nav>

      {/* Hero Section - Đổi thành w-full flex-1 để chiếm toàn bộ không gian còn lại */}
      <main className="w-full flex-1 px-8 lg:px-20 grid lg:grid-cols-2 gap-16 items-center relative z-10 pb-12">
        
        {/* Cột trái: Nội dung Text */}
        <div className="space-y-8">
          <h1 className="text-6xl lg:text-[5.5rem] font-extrabold leading-[1.05] tracking-tight">
            <span className="text-indigo-600 block mb-3">Market Analysis</span>
            <span className="text-slate-900 block">Performance Dashboard</span>
          </h1>
          
          <p className="text-lg lg:text-xl text-slate-500 max-w-xl leading-relaxed">
            Hệ thống giám sát toàn diện dữ liệu giá cà phê Robusta & Arabica. Tích hợp công cụ trích xuất tin tức và phân tích kỹ thuật tự động.
          </p>
          
          {/* <div className="pt-6">
            <button className="bg-indigo-600 hover:bg-indigo-700 text-white font-medium py-4 px-10 rounded-full text-lg shadow-[0_8px_20px_rgb(79,70,229,0.3)] transition-all transform hover:-translate-y-0.5">
              Bắt đầu
            </button>
          </div> */}
        </div>

        {/* Cột phải: Hình ảnh biểu đồ */}
        <div className="relative flex justify-end">
          <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-[120%] h-[120%] bg-white/40 blur-3xl rounded-full -z-10"></div>
          
          {/* Ảnh Placeholder tạm thời nếu bạn chưa có ảnh thật */}
          <img 
            src="/SMA.png" 
            alt="Dashboard Interface" 
            className="w-full max-w-2xl h-auto rounded-2xl drop-shadow-2xl border border-white/50 relative z-10 hover:scale-[1.02] transition-transform duration-500"
          />
        </div>

      </main>
    </div>
  );
}