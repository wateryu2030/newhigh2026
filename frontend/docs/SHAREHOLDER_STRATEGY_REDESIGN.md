# 股东策略画像页面改造说明

## 改造概述

路径：`/shareholder-strategy`，采用现代量化终端风格（OpenClaw / Quantum Terminal），深色主题、卡片化布局、移动端适配。

## 设计规范

### 配色
- 背景色：`#0A0C10`
- 卡片背景：`#14171C`
- 边框：`#2A2E36`
- 主色（强调）：`#FF3B30`
- 正文：`#F1F5F9`，次要文字：`#94A3B8`，辅助：`#64748B`
- 上涨：`#22C55E`，下跌：`#FF3B30`

### 布局

**电脑端 (≥1024px)**：
- 左侧边栏 260px：系统状态（延迟、运行时间）、快捷导航
- 右侧主内容：上中下三层卡片
  - 顶部：搜索框 + 报告期选择 + 应用筛选 + 最后更新
  - 中部：4 个 KPI 卡片（分析股票数、候选股数、平均持股集中度、平均机构数）
  - 下部：左侧候选股票表格（可排序、点击行打开抽屉），右侧策略雷达 + 筹码热力图

**移动端 (<1024px)**：
- 左侧边栏隐藏，由全局底部导航（Dashboard / Market / AI Trading / Strategies / Portfolio）替代
- 主内容垂直排列，KPI 2x2 网格，表格横向滚动，图表上下堆叠

## 新增/调整组件

| 组件 | 路径 | 说明 |
|------|------|------|
| KPICard | `components/shareholder-strategy/KPICard.tsx` | KPI 卡片：标题、大号数值、涨跌、迷你折线图 |
| StrategyRadarChart | `components/shareholder-strategy/StrategyRadarChart.tsx` | 策略风格雷达（成长/价值/动量/高频/保守） |
| ConcentrationHeatmap | `components/shareholder-strategy/ConcentrationHeatmap.tsx` | 筹码稳定性热力图 |
| StockDrawer | `components/shareholder-strategy/StockDrawer.tsx` | 行点击右侧滑出抽屉，展示股票详情 |
| ShareholderStrategyLayout | `components/shareholder-strategy/ShareholderStrategyLayout.tsx` | 主布局编排 |

## API 集成

沿用现有 Gateway 接口，无需改后端：

- `GET /financial/shareholder-by-name?name=xxx`：股东模糊搜索
- `GET /financial/shareholder-strategy?name=xxx`：股东策略详情
- `GET /financial/anti-quant-pool`：反量化选股池
- `GET /financial/anti-quant-stock/:code`：股票详情（抽屉）

使用 `React Query` 时可在此页面内封装 `useQuery`，当前为 `useEffect` + `api.*` 直接调用。

## 断点说明

- `sm`: 640px（KPI 可 2 列）
- `md`: 768px（控制区横向排列）
- `lg`: 1024px（左侧边栏显示）
- `xl`: 1280px（下部卡片 7:5 分栏）

## 集成方式

页面路由已指向新布局：

```tsx
// app/shareholder-strategy/page.tsx
export default function ShareholderStrategyPage() {
  return <ShareholderStrategyLayout />;
}
```

无需修改路由配置，访问 `/shareholder-strategy` 即可。
