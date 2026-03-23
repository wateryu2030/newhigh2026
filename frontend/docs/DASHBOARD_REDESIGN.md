# 首页 Dashboard 改造说明

## 改造概述

首页采用与股东策略画像一致的设计 token，主内容区最大宽度 1200px、居左显示，卡片间距 `gap-4`，支持淡入动画与悬浮缩放。

## 布局规范

- **主内容宽度**：`max-w-[1200px]`，居左
- **卡片间距**：`gap-4`（16px）
- **圆角**：16px（`rounded-2xl`）
- **卡片背景**：`#14171C`，边框 `#2A2E36`

## 新增组件

| 组件 | 路径 | 说明 |
|------|------|------|
| KPICard | `components/dashboard/KPICard.tsx` | 标题、数值、涨跌色、sparkline |
| WarningBanner | `components/dashboard/WarningBanner.tsx` | 数据完整性提醒横幅 |
| MiniChart | `components/dashboard/MiniChart.tsx` | 迷你 sparkline（可选） |
| Dashboard | `components/dashboard/Dashboard.tsx` | 首页主容器 |

## 移动端断点（Tailwind）

- **md (768px 以下)**：侧边栏隐藏，底部导航显示
- **KPI 网格**：`grid-cols-2`
- **系统数据概览**：`grid-cols-2`，股票池统计 `grid-cols-2`
- **数据横幅**：占满宽度，`compact` 时文字可缩小

## 动画与交互

- **animate-fadeIn**：页面加载时卡片依次淡入（globals.css）
- **hover:scale-[1.02]**：卡片悬浮轻微缩放
- **transition-transform duration-200**：过渡动画

## API 集成

当前使用：
- `api.dashboard()` → 权益、收益率、策略等
- `api.dataStatus()` → 数据完整性
- `api.marketEmotion()` → 情绪
- `api.sniperCandidates()` → 狙击候选数
- `api.systemDataOverview()` → 系统数据概览

若后端提供 `GET /api/dashboard/overview` 单接口，可替换为：

```ts
const { data } = useQuery({
  queryKey: ['dashboard', 'overview'],
  queryFn: () => apiGet<DashboardOverviewResponse>('/dashboard/overview'),
});
```

WebSocket 或轮询可在此基础上扩展。

## 替换原有首页

`app/page.tsx` 已改为渲染 `<Dashboard />`，无需修改路由。
