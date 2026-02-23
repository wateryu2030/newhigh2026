# 前端组件结构说明（TradingView 风格）

## 技术栈

- **React 18** + **TypeScript**
- **Ant Design 5**（暗色主题）
- **TradingView Lightweight Charts**（K 线）
- **ECharts**（收益曲线、月度热力图）
- **Vite** 构建，开发代理 `/api` → `http://127.0.0.1:5050`

## 主题与性能

- 背景色：`#0b0f17`（专业金融暗色）
- 容器/卡片：`#111827`
- 主色：`#10b981`（绿），危险色：`#ef4444`（红）
- 数据加载目标：< 300ms（接口从 DuckDB 读取）

---

## 页面与路由

| 路径 | 组件 | 说明 |
|------|------|------|
| `/trading` | `TradingDecision` | 交易决策中心（三栏：股票列表 / K 线 / 右侧面板） |
| `/strategy-lab` | `StrategyLab` | 策略实验室（回测表单、收益曲线、交易列表） |
| `/scanner` | `MarketScanner` | 市场扫描器（突破 / 强势 / AI 推荐 Tab） |

---

## 组件结构

```
src/
├── main.tsx                 # 入口，ConfigProvider(antd 主题)
├── App.tsx                  # 路由：/trading, /strategy-lab, /scanner
├── theme.ts                 # Ant Design token（#0b0f17 等）
├── index.css                # 全局背景/字体
├── types/
│   └── index.ts             # KlineBar, Signal, AiScore, BacktestResult, ScanItem
├── api/
│   └── client.ts            # api.kline, api.signals, api.aiScore, api.backtest, api.scan, api.stocks
├── components/
│   ├── MainLayout.tsx       # 顶部导航 + Outlet，菜单：交易决策 / 策略实验室 / 市场扫描器
│   ├── KLineChart.tsx       # TradingView Lightweight Candlestick + 成交量 + 买卖点 Marker
│   ├── SignalMarkers.tsx    # 买卖点列表（BUY/SELL、止损、目标位、原因）
│   └── SignalMarkers.module.css
└── pages/
    ├── TradingDecision.tsx  # 左：股票列表+搜索；中：K 线图；右：AI 评分 + SignalMarkers
    ├── StrategyLab.tsx      # 回测表单 + 收益曲线(ECharts) + 月度图 + 交易表
    └── MarketScanner.tsx    # Tabs：突破股票 / 强势股 / AI 推荐，Table 展示
```

---

## 数据流与接口

- **K 线**：`GET /api/kline?symbol=&start=&end=` → DuckDB `daily_bars`
- **买卖点**：`GET /api/signals?symbol=` → 策略 `generate_signals` 结果
- **AI 评分**：`GET /api/ai_score?symbol=` → 模型评分 + suggestion/position_pct/risk_level
- **回测**：`POST /api/backtest` body `{ strategy, symbol, start, end }` → 收益曲线、回撤、夏普、交易列表
- **扫描**：`GET /api/scan?mode=breakout|strong|ai` → 突破/强势/AI 推荐列表
- **股票列表**：`GET /api/stocks` → DuckDB `stocks`

---

## 使用方式

```bash
# 安装依赖
cd frontend && npm install

# 开发（需先启动后端 python web_platform.py，端口 5050）
npm run dev   # http://localhost:5173，/api 代理到 5050

# 构建
npm run build
```

---

## UI 截图说明

- **交易决策中心**：左侧股票列表可搜索、点击选股；中间为 TradingView K 线 + 成交量，叠加 BUY/SELL 箭头；右侧为 AI 评分、建议仓位、风险等级及买卖点列表（含止损/目标位）。
- **策略实验室**：顶部为策略/标的/日期表单与「运行回测」按钮；下方为总收益、最大回撤、夏普比率卡片，ECharts 收益曲线与交易列表。
- **市场扫描器**：Tab 切换「突破股票」「强势股」「AI 推荐」，表格展示标的、信号、价格、买点概率等。

（实际截图需在本地运行 `npm run dev` 后于浏览器中打开并截取。）
