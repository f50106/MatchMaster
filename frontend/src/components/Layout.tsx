import { Outlet, Link } from 'react-router-dom';
import { useI18n } from '../i18n';
import type { Locale } from '../i18n/locales';

/** MatchMaster M-circle logo — white background, indigo M, indigo border */
function MCircleLogo({ size = 32 }: { size?: number }) {
  return (
    <svg
      xmlns="http://www.w3.org/2000/svg"
      width={size}
      height={size}
      viewBox="0 0 64 64"
      aria-label="MatchMaster logo"
    >
      <circle cx="32" cy="32" r="30" fill="white" stroke="#c7d2fe" strokeWidth="2.5" />
      <text
        x="32"
        y="45"
        fontFamily="Arial Black, Arial, sans-serif"
        fontSize="36"
        fontWeight="900"
        fill="#3730a3"
        textAnchor="middle"
        dominantBaseline="auto"
      >
        M
      </text>
    </svg>
  );
}


export default function Layout() {
  const { locale, t, setLocale } = useI18n();

  return (
    <div className="h-screen flex flex-col overflow-hidden">
      <header className="bg-indigo-600 text-white shadow-md flex-shrink-0">
        <div className="max-w-7xl mx-auto px-4 py-3 flex items-center justify-between">
          <Link to="/" className="flex items-center gap-2 text-xl font-bold tracking-tight">
            <MCircleLogo size={34} />
            MatchMaster
          </Link>
          <div className="flex items-center gap-3">
            <span className="text-indigo-200 text-sm hidden sm:inline">{t.appSubtitle}</span>
            <select
              value={locale}
              onChange={(e) => setLocale(e.target.value as Locale)}
              className="bg-indigo-500 text-white text-sm rounded px-2 py-1 border border-indigo-400 focus:outline-none focus:ring-2 focus:ring-indigo-300 cursor-pointer"
            >
              <option value="zh">中文</option>
              <option value="en">English</option>
            </select>
          </div>
        </div>
      </header>
      <main className="flex-1 overflow-y-auto [scrollbar-gutter:stable]">
        <div className="min-h-full flex flex-col">
          <div className="max-w-5xl mx-auto w-full flex-1 px-6 py-6">
            <Outlet />
          </div>
          <footer className="text-center text-xs text-gray-400 py-3">
            {t.footerVersion}
          </footer>
        </div>
      </main>
    </div>
  );
}


