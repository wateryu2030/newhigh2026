'use client';

import { ShareholderStrategyLayout } from '@/components/shareholder-strategy/ShareholderStrategyLayout';

/**
 * 股东策略画像 - 现代量化终端风格
 * 路由：/shareholder-strategy
 *
 * 布局说明：
 * - 电脑端：左侧边栏 260px + 主内容区（控制区/KPI/表格+可视化）
 * - 移动端：左侧边栏隐藏（由全局底部导航替代），主内容垂直堆叠
 *
 * API 集成：
 * - GET /financial/shareholder-by-name?name=xxx 股东搜索
 * - GET /financial/shareholder-strategy?name=xxx 股东策略详情
 * - GET /financial/anti-quant-pool 反量化选股池
 * - GET /financial/anti-quant-stock/:code 股票详情（抽屉）
 */
export default function ShareholderStrategyPage() {
  return <ShareholderStrategyLayout />;
}
