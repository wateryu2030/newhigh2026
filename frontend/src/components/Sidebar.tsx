'use client';

import Link from 'next/link';
import { usePathname } from 'next/navigation';
import { useLang } from '@/context/LangContext';
import { quickNavItems, fullMenuItems } from '@/config/menu';

interface SidebarProps {
  /** 是否隐藏（如股东策略页自有侧栏） */
  hidden?: boolean;
}

/** 与 shareholder-strategy 左侧栏一致的菜单行样式 */
const navItemBase =
  'block rounded-lg px-3 py-2.5 text-sm leading-relaxed transition-colors duration-200';

/**
 * 全局桌面端侧边栏：与 /shareholder-strategy 相同「独立圆角卡片」外框
 * — 四边圆角、细边框、轻阴影、左侧与上下留白，宽度 260px
 */
export function Sidebar({ hidden }: SidebarProps) {
  const pathname = usePathname();
  const { t } = useLang();

  if (hidden) return null;

  const linkClass = (active: boolean) =>
    `${navItemBase} ${active ? 'font-semibold text-text-primary' : 'text-text-secondary'} ${active ? '' : 'hover:bg-white/5'}`;

  return (
    <aside className="sidebar-scroll fixed bottom-3 left-3 top-[calc(4rem+0.75rem)] z-40 hidden w-[260px] flex-col overflow-y-auto rounded-2xl border border-card-border bg-card-bg shadow-card md:flex">
      <div className="flex flex-col gap-4 p-4">
        {/* 快捷导航 */}
        <div>
          <h3 className="mb-2 text-sm font-semibold text-text-secondary">快捷导航</h3>
          <nav className="space-y-1">
            {quickNavItems.map((item) => {
              const active = pathname === item.path;
              return (
                <Link
                  key={item.path}
                  href={item.path}
                  className={linkClass(active)}
                >
                  {t(item.key)}
                </Link>
              );
            })}
          </nav>
        </div>

        {/* 全部菜单：与股东页侧栏相同的顶部分割线 */}
        <div className="border-t border-card-border pt-4">
          <h3 className="mb-2 text-sm font-semibold text-text-secondary">全部菜单</h3>
          <nav className="space-y-1">
            {fullMenuItems.map((item) => {
              const active = pathname === item.path;
              return (
                <Link
                  key={item.path}
                  href={item.path}
                  className={linkClass(active)}
                >
                  {t(item.key)}
                </Link>
              );
            })}
          </nav>
        </div>

        <div className="pt-2">
          <Link
            href="/ai-trading"
            className="flex w-full items-center justify-center rounded-lg bg-primary-fixed py-2.5 text-sm font-medium text-on-warm-fill transition hover:opacity-90"
          >
            启动策略
          </Link>
        </div>
      </div>
    </aside>
  );
}
