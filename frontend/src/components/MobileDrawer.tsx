'use client';

import Link from 'next/link';
import { usePathname } from 'next/navigation';
import { useLang } from '@/context/LangContext';
import { menuItems } from '@/config/menu';

interface MobileDrawerProps {
  open: boolean;
  onClose: () => void;
}

/** 移动端侧滑菜单：从左侧滑出，显示全部菜单项 */
export function MobileDrawer({ open, onClose }: MobileDrawerProps) {
  const pathname = usePathname();
  const { t } = useLang();

  if (!open) return null;

  return (
    <>
      <div
        role="presentation"
        className="fixed inset-0 z-[60] bg-[color:var(--color-overlay-scrim)] backdrop-blur-sm md:hidden"
        onClick={onClose}
        onKeyDown={(e) => e.key === 'Escape' && onClose()}
        aria-hidden="true"
      />
      <aside className="fixed left-0 top-0 z-[61] flex h-full w-64 animate-fade-in flex-col border-r border-card-border bg-card-bg shadow-[4px_0_24px_rgba(0,0,0,0.4)] md:hidden">
        <div className="flex h-16 shrink-0 items-center justify-between border-b border-card-border px-4">
          <span className="text-lg font-bold text-text-primary">红山量化平台</span>
          <button
            type="button"
            onClick={onClose}
            className="rounded-lg p-2 text-text-secondary transition-colors hover:bg-card-border/50"
            aria-label="关闭菜单"
          >
            <span className="material-symbols-outlined">close</span>
          </button>
        </div>
        <nav className="sidebar-scroll min-h-0 flex-1 space-y-1 overflow-y-auto p-4">
          {menuItems.map((item) => {
            const active = pathname === item.path;
            return (
              <Link
                key={item.path}
                href={item.path}
                onClick={onClose}
                className={`flex items-center rounded-xl px-4 py-3 transition-all duration-200 ${
                  active
                    ? 'bg-card-border font-semibold text-primary-fixed'
                    : 'text-text-secondary hover:bg-card-border/50'
                }`}
              >
                {t(item.key)}
              </Link>
            );
          })}
        </nav>
      </aside>
    </>
  );
}
