import { Hexagon } from 'lucide-react';
import { Link, useLocation } from 'react-router-dom';

const NAV_LINKS = [
  { to: '/', label: 'Trang chủ' },
  { to: '/charts', label: 'Biểu đồ phân tích' },
  { to: '/search', label: 'Tìm kiếm thông tin' },
  { to: '/model', label: 'Dự báo ML' },
];

export default function Navbar() {
  const { pathname } = useLocation();

  return (
    <nav className="w-full flex items-center justify-between px-8 lg:px-20 py-6 relative z-30">
      <Link to="/" className="flex items-center gap-3 cursor-pointer">
        <Hexagon className="w-8 h-8 text-indigo-600 fill-indigo-100" strokeWidth={1.5} />
        <span className="font-bold text-xl tracking-tight text-slate-800">
          Coffee<span className="text-indigo-600">Finance</span>
        </span>
      </Link>

      <div className="hidden md:flex items-center gap-10 font-medium text-slate-600">
        {NAV_LINKS.map(({ to, label }) => (
          <Link
            key={to}
            to={to}
            className={
              pathname === to
                ? 'text-indigo-600 border-b-2 border-indigo-600 pb-0.5'
                : 'hover:text-indigo-600 transition-colors'
            }
          >
            {label}
          </Link>
        ))}
      </div>
    </nav>
  );
}
