'use client';

import Link from 'next/link';
import { usePathname } from 'next/navigation';
import { useLang } from '@/context/LangContext';
import { mobilePrimaryItems } from '@/config/menu';

interface MobileBottomNavProps {
  onMenuClick: () => void;
}

/** 移动端底部导航栏：4-5 个主要入口 + 汉堡菜单打开侧滑 */
export function MobileBottomNav({ onMenuClick }: MobileBottomNavProps) {
  const pathname = usePathname();
  const { t } = useLang();

  return (
    <nav className="safe-area-pb fixed bottom-0 left-0 right-0 z-50 flex items-center justify-around rounded-t-2xl border-t border-card-border bg-[color:var(--color-nav-mobile-bg)] px-2 pt-3 backdrop-blur-xl md:hidden">
      {mobilePrimaryItems.map((item) => {
        const active = pathname === item.path;
        return (
          <Link
            key={item.path}
            href={item.path}
            className={`flex flex-col items-center justify-center rounded-xl px-4 py-1.5 transition-colors ${
              active
                ? 'bg-[color:var(--color-nav-mobile-active-bg)] text-primary-fixed'
                : 'text-text-secondary'
            }`}
          >
            <span className="text-center text-xs font-medium tracking-wide">{t(item.key)}</span>
          </Link>
        );
      })}
      <button
        type="button"
        onClick={onMenuClick}
        className="flex flex-col items-center justify-center px-4 py-1.5 text-text-secondary transition-colors"
        aria-label="打开菜单"
      >
        <span className="text-center text-xs font-medium tracking-wide">更多</span>
      </button>
    </nav>
  );
}
