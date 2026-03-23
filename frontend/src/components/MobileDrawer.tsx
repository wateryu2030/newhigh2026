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
      {/* 遮罩 */}
      <div
        role="presentation"
        className="fixed inset-0 z-[60] bg-black/50 backdrop-blur-sm md:hidden"
        onClick={onClose}
        onKeyDown={(e) => e.key === 'Escape' && onClose()}
        aria-hidden="true"
      />
      {/* 抽屉 */}
      <aside
        className="fixed left-0 top-0 z-[61] flex h-full w-64 animate-fade-in flex-col md:hidden"
        style={{
          backgroundColor: '#14171C',
          borderRight: '1px solid #2A2E36',
          boxShadow: '4px 0 24px rgba(0,0,0,0.4)',
          fontFamily: 'Inter',
        }}
      >
        <div className="flex h-16 shrink-0 items-center justify-between border-b px-4" style={{ borderColor: '#2A2E36' }}>
          <span className="text-lg font-bold" style={{ color: '#F1F5F9' }}>
            红山量化平台
          </span>
          <button
            type="button"
            onClick={onClose}
            className="rounded-lg p-2 transition-colors hover:bg-card-border/50"
            style={{ color: '#94A3B8' }}
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
                  active ? '' : 'hover:bg-card-border/50'
                }`}
                style={
                  active
                    ? { backgroundColor: '#2A2E36', color: '#FF3B30', fontWeight: 600 }
                    : { color: '#94A3B8' }
                }
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
