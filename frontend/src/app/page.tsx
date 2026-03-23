'use client';

import { Dashboard } from '@/components/dashboard/Dashboard';

/**
 * 首页 Dashboard
 * 路由：/
 *
 * 布局：主内容区最大宽度 1200px，居左显示（侧边栏固定）
 * 卡片间距：gap-4
 * 移动端：md 以下 grid-cols-2
 *
 * API：api.dashboard(), api.dataStatus() 等
 * 若后端提供 GET /api/dashboard/overview，可替换为单接口
 */
export default function DashboardPage() {
  return <Dashboard />;
}
