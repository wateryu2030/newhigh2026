'use client';

import { useState } from 'react';
import { usePathname } from 'next/navigation';
import { TopBar } from './TopBar';
import { Sidebar } from './Sidebar';
import { MobileBottomNav } from './MobileBottomNav';
import { MobileDrawer } from './MobileDrawer';

interface LayoutProps {
  children: React.ReactNode;
}

/**
 * 红山量化平台 - 全局布局（所有路由经根 layout 包裹）
 * 桌面端：圆弧 Sidebar + MainContent；移动端：底部导航 + 侧滑菜单
 * /shareholder-strategy：隐藏全局侧栏，使用页面内 ShareholderStrategyLayout
 */
export function Layout({ children }: LayoutProps) {
  const pathname = usePathname();
  const [drawerOpen, setDrawerOpen] = useState(false);
  const isShareholderStrategy = (pathname ?? '').startsWith('/shareholder-strategy');

  return (
    <>
      <TopBar onMobileMenuClick={() => setDrawerOpen(true)} />
      <Sidebar hidden={isShareholderStrategy} />
      <MobileDrawer open={drawerOpen} onClose={() => setDrawerOpen(false)} />
      <MobileBottomNav onMenuClick={() => setDrawerOpen(true)} />
      {children}
    </>
  );
}
