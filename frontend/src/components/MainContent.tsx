'use client';

import { usePathname } from 'next/navigation';

interface MainContentProps {
  children: React.ReactNode;
}

/** 主内容区：股东策略页无全局侧栏，不加左侧 padding */
export function MainContent({ children }: MainContentProps) {
  const pathname = usePathname();
  const isShareholderStrategy = (pathname ?? '').startsWith('/shareholder-strategy');

  /** 与浮动侧栏对齐：left-3(0.75rem) + 宽260px + 与主区间距 1.5rem */
  const mainPl = isShareholderStrategy ? 'md:pl-6' : 'md:pl-[calc(0.75rem+260px+1.5rem)]';

  return (
    <main
      className={`min-h-screen bg-surface px-4 pb-24 pt-20 md:pr-6 md:pb-8 md:pt-20 ${mainPl}`}
    >
      {children}
    </main>
  );
}
