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
      <header className="fixed left-0 right-0 top-0 z-50 flex h-16 items-center justify-between bg-surface px-4 font-headline md:px-6">
        <div className="flex items-center gap-4 md:gap-8">
          <Link href="/" className="text-lg font-bold tracking-tighter text-primary-fixed md:text-xl">
            KINETIC_TERMINAL
          </Link>
          <nav className="hidden items-center gap-6 md:flex">
            {topItems.map(({ href, key }) => {
              const active = pathname === href;
              return (
                <Link
                  key={href}
                  href={href}
                  className={`px-1 py-5 transition-colors ${
                    active
                      ? 'border-b-2 border-primary-fixed text-primary-fixed'
                      : 'text-on-surface-variant'
                  }`}
                >
                  {t(key)}
                </Link>
              );
            })}
          </nav>
        </div>
        <div className="flex items-center gap-2 md:gap-4">
          <button
            type="button"
            onClick={() => setLang(lang === 'zh' ? 'en' : 'zh')}
            className="rounded-lg px-2 py-1.5 text-sm text-on-surface-variant transition-colors hover:opacity-80"
            title={lang === 'zh' ? 'Switch to English' : '切换到中文'}
          >
            {t('lang.switch')}
          </button>
        </div>
      </header>

      {!(pathname ?? '').startsWith('/shareholder-strategy') && (
        <aside className="fixed left-0 top-16 z-40 hidden h-[calc(100vh-64px)] w-64 flex-col bg-surface-container-low py-8 md:flex">
          <div className="mb-8 px-6">
            <div className="flex items-center gap-3 rounded-xl bg-surface-container-high p-3">
              <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-primary-fixed text-on-warm-fill">
                <span className="material-symbols-outlined text-xl">terminal</span>
              </div>
              <div>
                <div className="font-semibold text-on-surface">QuantOps</div>
                <div className="font-label text-[10px] uppercase tracking-widest text-primary-fixed">
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
                    active
                      ? 'border-r-2 border-primary-fixed font-semibold text-primary-fixed'
                      : 'text-on-surface-variant hover:bg-surface-container-high/50 hover:text-primary'
                  }`}
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
              className="flex w-full items-center justify-center gap-2 rounded-lg bg-primary-fixed py-3 font-bold text-on-warm-fill transition-all hover:brightness-110"
            >
              <span className="material-symbols-outlined text-sm">rocket_launch</span>
              Launch Strategy
            </Link>
          </div>
        </aside>
      )}

      <nav className="safe-area-pb fixed bottom-0 left-0 right-0 z-50 flex items-center justify-around border-t border-card-border/50 bg-[color:var(--color-nav-mobile-bg)] px-2 pt-3 backdrop-blur-xl md:hidden">
        {bottomNavItems.map(({ href, key, icon }) => {
          const active = pathname === href;
          return (
            <Link
              key={href}
              href={href}
              className={`flex flex-col items-center justify-center rounded-xl px-4 py-1.5 ${
                active
                  ? 'bg-surface-container-high text-primary-fixed'
                  : 'text-on-surface-variant'
              }`}
            >
              <span className="material-symbols-outlined">{icon}</span>
              <span className="font-label mt-1 text-[10px] uppercase tracking-widest">{t(key)}</span>
            </Link>
          );
        })}
      </nav>
    </>
  );
}
