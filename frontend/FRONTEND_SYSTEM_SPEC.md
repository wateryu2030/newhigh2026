# AI Hedge Fund OS — 前端系统规格

## 目标

- **把复杂 AI 系统变成直观信息**
- **让客户看到系统在赚钱、在进化**
- **手机 + 电脑统一体验（Mobile First + Desktop Pro Dashboard）**

## 技术栈

- Next.js (App Router)
- React 18
- TypeScript
- Tailwind CSS
- Zustand
- Recharts

## 信息架构

| 页面 | 电脑端 | 手机端 |
|------|--------|--------|
| Dashboard | 总资产、今日收益、Sharpe、回撤、收益曲线、策略排行、AI 生成统计 | 资产、今日收益、小曲线、Top 策略、AI 生成数 |
| Market | 多标的 K 线、Orderbook、波动率 | 标的价格、涨跌、小 K 线 |
| Strategies | 策略池表格、Alpha/Sharpe/回撤/状态 | 策略列表卡片 |
| Alpha Lab | 生成/回测/风控/上线漏斗、趋势图、Alpha 分布 | 漏斗数字、进入交易数 |
| Evolution | 代数、最优策略、进化树 | 代数、最优策略 |
| Portfolio | 总资产、资产分布、仓位列表 | 资产、仓位 |
| Risk | 回撤、VaR、敞口、风险时序 | 核心指标 |
| Trade | 实时成交列表 | 最近交易 |
| Reports | 月报、PDF 导出 | 简要 |

## 响应式断点

- Mobile: &lt; 768px
- Tablet: ≥ 768px
- Desktop: ≥ 1200px

Tailwind: `grid-cols-1 md:grid-cols-2 lg:grid-cols-4`

## UI 风格

- 深色主题
- 主色: `#0F172A` (slate-900), `#10B981` (emerald-500), `#6366F1` (indigo-500)
- 参考: Bloomberg / TradingView / Stripe

## 图表

- 收益曲线、回撤曲线、策略排名、Alpha 分布、策略进化树、资产分布、风险曲线

## API

- GET /api/dashboard
- GET /api/strategies
- GET /api/portfolio
- GET /api/risk
- GET /api/market
- GET /api/trades
- GET /api/evolution

## 目录结构

```
frontend/
  src/
    app/           # Next.js App Router
    components/
    store/
    api/
    hooks/
    utils/
```

## 核心信息（客户最关心）

1. 收益（曲线 + 数字）
2. 风险（回撤、VaR）
3. 策略数量（存活、运行）
4. AI 进化（生成数、代数、最优策略）
