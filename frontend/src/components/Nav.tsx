'use client';

import Link from 'next/link';
import { usePathname } from 'next/navigation';
import { useLang } from '@/context/LangContext';

const items: { href: string; key: string }[] = [
  { href: '/', key: 'nav.dashboard' },
  { href: '/system-monitor', key: 'nav.systemMonitor' },
  { href: '/data', key: 'nav.data' },
  { href: '/stocks', key: 'nav.stocks' },
  { href: '/market', key: 'nav.market' },
  { href: '/ai-trading', key: 'nav.aiTrading' },
  { href: '/news', key: 'nav.news' },
  { href: '/research', key: 'nav.research' },
  { href: '/strategies', key: 'nav.strategies' },
  { href: '/alpha-lab', key: 'nav.alphaLab' },
  { href: '/evolution', key: 'nav.evolution' },
  { href: '/portfolio', key: 'nav.portfolio' },
  { href: '/risk', key: 'nav.risk' },
  { href: '/trade', key: 'nav.trade' },
  { href: '/reports', key: 'nav.reports' },
  { href: '/settings', key: 'nav.settings' },
];

/** 移动端底部导航：核心三视图 AI Trade / Strategy Market / Portfolio + Dashboard / Market */
const bottomNavItems: { href: string; key: string }[] = [
  { href: '/', key: 'nav.dashboard' },
  { href: '/market', key: 'nav.market' },
  { href: '/ai-trading', key: 'nav.aiTrading' },
  { href: '/strategies', key: 'nav.strategies' },
  { href: '/portfolio', key: 'nav.portfolio' },
];

export function Nav() {
  const pathname = usePathname();
  const { t, lang, setLang } = useLang();
  return (
    <>
      {/* 桌面端：顶部导航 */}
      <header className="sticky top-0 z-50 hidden border-b border-slate-700/50 bg-slate-900/95 backdrop-blur md:block">
        <div className="mx-auto flex max-w-7xl flex-wrap items-center justify-between gap-2 px-4 py-3 sm:px-6 lg:px-8">
          <Link href="/" className="text-lg font-semibold text-white">
            {t('app.title')}
          </Link>
          <nav className="flex flex-wrap items-center gap-1">
            {items.map(({ href, key }) => (
              <Link
                key={href}
                href={href}
                className={pathname === href ? 'link-nav active' : 'link-nav'}
              >
                {t(key)}
              </Link>
            ))}
            <button
              type="button"
              onClick={() => setLang(lang === 'zh' ? 'en' : 'zh')}
              className="link-nav ml-1"
              title={lang === 'zh' ? 'Switch to English' : '切换到中文'}
            >
              {t('lang.switch')}
            </button>
          </nav>
        </div>
      </header>

      {/* 移动端：底部固定导航 */}
      <nav
        className="fixed bottom-0 left-0 right-0 z-50 flex items-center justify-around border-t border-slate-700/50 bg-slate-900/95 py-2 backdrop-blur safe-area-pb md:hidden"
        aria-label="Bottom navigation"
      >
        {bottomNavItems.map(({ href, key }) => (
          <Link
            key={href}
            href={href}
            className={`flex min-w-0 flex-1 flex-col items-center gap-0.5 px-2 py-1 text-xs transition ${
              pathname === href ? 'text-fund-indigo' : 'text-slate-400 hover:text-white'
            }`}
          >
            <span className="truncate">{t(key)}</span>
          </Link>
        ))}
      </nav>
    </>
  );
}
