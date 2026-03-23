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
    <nav
      className="fixed bottom-0 left-0 right-0 z-50 flex items-center justify-around px-2 pt-3 md:hidden safe-area-pb"
      style={{
        backgroundColor: 'rgba(20,23,28,0.95)',
        backdropFilter: 'blur(24px)',
        WebkitBackdropFilter: 'blur(24px)',
        borderTop: '1px solid #2A2E36',
        borderTopLeftRadius: 16,
        borderTopRightRadius: 16,
        fontFamily: 'Inter',
      }}
    >
      {mobilePrimaryItems.map((item) => {
        const active = pathname === item.path;
        return (
          <Link
            key={item.path}
            href={item.path}
            className="flex flex-col items-center justify-center px-4 py-1.5 transition-colors"
            style={
              active
                ? { color: '#FF3B30', backgroundColor: 'rgba(42,46,54,0.8)', borderRadius: 12 }
                : { color: '#94A3B8' }
            }
          >
            <span className="text-center text-xs font-medium tracking-wide">{t(item.key)}</span>
          </Link>
        );
      })}
      <button
        type="button"
        onClick={onMenuClick}
        className="flex flex-col items-center justify-center px-4 py-1.5 transition-colors"
        style={{ color: '#94A3B8' }}
        aria-label="打开菜单"
      >
        <span className="text-center text-xs font-medium tracking-wide">更多</span>
      </button>
    </nav>
  );
}
