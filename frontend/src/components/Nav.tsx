'use client';

import Link from 'next/link';
import { usePathname } from 'next/navigation';
import { useLang } from '@/context/LangContext';

const sideItems: { href: string; key: string; icon: string }[] = [
  { href: '/', key: 'nav.dashboard', icon: 'dashboard' },
  { href: '/alpha-lab', key: 'nav.alphaLab', icon: 'science' },
  { href: '/market', key: 'nav.market', icon: 'query_stats' },
  { href: '/ai-trading', key: 'nav.aiTrading', icon: 'memory' },
  { href: '/strategies', key: 'nav.strategies', icon: 'settings_input_component' },
  { href: '/portfolio', key: 'nav.portfolio', icon: 'account_balance' },
  { href: '/shareholder-strategy', key: 'nav.shareholderStrategy', icon: 'bar_chart' },
  { href: '/data', key: 'nav.data', icon: 'storage' },
  { href: '/system-monitor', key: 'nav.systemMonitor', icon: 'monitor_heart' },
  { href: '/news', key: 'nav.news', icon: 'newspaper' },
  { href: '/settings', key: 'nav.settings', icon: 'settings' },
];

const topItems: { href: string; key: string }[] = [
  { href: '/', key: 'nav.dashboard' },
  { href: '/alpha-lab', key: 'nav.alphaLab' },
  { href: '/market', key: 'nav.market' },
];

const bottomNavItems: { href: string; key: string; icon: string }[] = [
  { href: '/', key: 'nav.dashboard', icon: 'home' },
  { href: '/market', key: 'nav.market', icon: 'search' },
  { href: '/ai-trading', key: 'nav.aiTrading', icon: 'notifications' },
  { href: '/strategies', key: 'nav.strategies', icon: 'science' },
  { href: '/portfolio', key: 'nav.portfolio', icon: 'account_balance' },
];

export function Nav() {
  const pathname = usePathname();
  const { t, lang, setLang } = useLang();

  return (
    <>
      {/* TopNavBar - 参考 KINETIC_TERMINAL */}
      <header
        className="fixed top-0 left-0 right-0 z-50 flex h-16 items-center justify-between px-4 md:px-6"
        style={{ backgroundColor: '#0B0E14', fontFamily: 'Manrope' }}
      >
        <div className="flex items-center gap-4 md:gap-8">
          <Link href="/" className="text-lg font-bold tracking-tighter md:text-xl" style={{ color: '#FF3B30' }}>
            KINETIC_TERMINAL
          </Link>
          <nav className="hidden items-center gap-6 md:flex">
            {topItems.map(({ href, key }) => (
              <Link
                key={href}
                href={href}
                className="px-1 py-5 transition-colors"
                style={
                  pathname === href
                    ? { color: '#FF3B30', borderBottom: '2px solid #FF3B30' }
                    : { color: '#A9ABB3' }
                }
              >
                {t(key)}
              </Link>
            ))}
          </nav>
        </div>
        <div className="flex items-center gap-2 md:gap-4">
          <button
            type="button"
            onClick={() => setLang(lang === 'zh' ? 'en' : 'zh')}
            className="rounded-lg px-2 py-1.5 text-sm transition-colors hover:opacity-80"
            style={{ color: '#A9ABB3' }}
            title={lang === 'zh' ? 'Switch to English' : '切换到中文'}
          >
            {t('lang.switch')}
          </button>
        </div>
      </header>

      {/* SideNavBar - 桌面端左侧（股东策略页自有侧栏，此处隐藏避免重复） */}
      {!(pathname ?? '').startsWith('/shareholder-strategy') && (
      <aside
        className="fixed left-0 top-16 z-40 hidden h-[calc(100vh-64px)] w-64 flex-col py-8 md:flex"
        style={{ backgroundColor: '#10131A', fontFamily: 'Inter' }}
      >
        <div className="mb-8 px-6">
          <div
            className="flex items-center gap-3 rounded-xl p-3"
            style={{ backgroundColor: '#1C2028' }}
          >
            <div
              className="flex h-10 w-10 items-center justify-center rounded-lg"
              style={{ backgroundColor: '#FF3B30', color: '#FFFFFF' }}
            >
              <span className="material-symbols-outlined text-xl">terminal</span>
            </div>
            <div>
              <div className="font-semibold" style={{ color: '#ECEDF6' }}>
                QuantOps
              </div>
              <div className="text-[10px] uppercase tracking-widest" style={{ color: '#FF3B30', fontFamily: 'Space Grotesk' }}>
                Active Session
              </div>
            </div>
          </div>
        </div>
        <nav className="flex-1 space-y-2 px-4">
          {sideItems.map(({ href, key, icon }) => {
            const active = pathname === href;
            return (
              <Link
                key={href}
                href={href}
                className={`flex items-center gap-3 px-4 py-3 transition-all duration-300 ${
                  !active ? 'hover:bg-[#1C2028]/50 hover:text-[#FF6B6B]' : ''
                }`}
                style={
                  active
                    ? { color: '#FF3B30', fontWeight: 600, borderRight: '2px solid #FF3B30' }
                    : { color: '#A9ABB3' }
                }
              >
                <span className="material-symbols-outlined">{icon}</span>
                <span>{t(key)}</span>
              </Link>
            );
          })}
        </nav>
        <div className="space-y-4 px-6 pb-6">
          <Link
            href="/ai-trading"
            className="flex w-full items-center justify-center gap-2 rounded-lg py-3 font-bold transition-all hover:brightness-110"
            style={{ backgroundColor: '#FF3B30', color: '#FFFFFF' }}
          >
            <span className="material-symbols-outlined text-sm">rocket_launch</span>
            Launch Strategy
          </Link>
        </div>
      </aside>
      )}

      {/* BottomNavBar - 移动端，兼容安全区与触摸 */}
      <nav
        className="fixed bottom-0 left-0 right-0 z-50 flex items-center justify-around px-2 pt-3 md:hidden safe-area-pb"
        style={{
          backgroundColor: 'rgba(11,14,20,0.9)',
          backdropFilter: 'blur(24px)',
          WebkitBackdropFilter: 'blur(24px)',
          borderTop: '1px solid rgba(28,32,40,0.5)',
        }}
      >
        {bottomNavItems.map(({ href, key, icon }) => {
          const active = pathname === href;
          return (
            <Link
              key={href}
              href={href}
              className="flex flex-col items-center justify-center px-4 py-1.5"
              style={active ? { color: '#FF3B30', backgroundColor: '#1C2028', borderRadius: 12 } : { color: '#A9ABB3' }}
            >
              <span className="material-symbols-outlined">{icon}</span>
              <span className="mt-1 text-[10px] uppercase tracking-widest" style={{ fontFamily: 'Space Grotesk' }}>
                {t(key)}
              </span>
            </Link>
          );
        })}
      </nav>
    </>
  );
}
