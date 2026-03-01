# 生产级机构量化系统 — Cursor 自动执行任务（完整版）

## 目标
将当前项目升级为**生产级 A 股量化交易系统**：
- 100万–1000万资金
- 年化目标 20–40%
- 最大回撤 <15%
- 支持模拟与实盘扩展（QMT）

## 要求
1. 支持模拟交易  
2. 支持多策略组合（龙头 + 趋势 + 均值回归）  
3. 支持 AI 基金经理（择时 + 策略权重）  
4. 支持风险控制（单笔权重、回撤）  
5. 支持 TradingView 级图表  
6. 前端可下单操作  
7. 后端可扩展 QMT 接口  

---

## 任务列表

| 任务 | 内容 |
|------|------|
| 任务1 | 重构 backend 目录：engine / strategy / portfolio / ai / execution / broker / risk / data / api |
| 任务2 | 实现 TradingEngine（run_daily：信号→组合→风控→下单） |
| 任务3 | 实现策略模块：dragon.py / trend.py / mean_reversion.py，统一 generate(df, code) |
| 任务4 | 实现 PortfolioOptimizer（含 risk_parity）+ ProductionAllocator |
| 任务5 | 实现 RiskEngine.check(orders) + drawdown + position_limit |
| 任务6 | 实现 OrderManager（create + 状态机 NEW/SUBMITTED/FILLED/CANCELLED/REJECTED） |
| 任务7 | 实现 BrokerAdapter：base.send_order + sim.py + qmt 占位 |
| 任务8 | 实现 AI Fund Manager：RegimeDetector + decide_weights(regime) |
| 任务9 | 实现 API：/strategy/run, /portfolio/weights, /order, /account, /ai/decision |
| 任务10 | 实现 Trading Chart 前端：ChartEngine / IndicatorLayer / SignalOverlay / TradeOverlay |
| 任务11 | 实现 Portfolio Dashboard 前端 |
| 任务12 | 实现交易面板（下单、持仓、资金） |
| 任务13 | 实现自动交易调度：scheduler/trading_loop.py，可 cron/supervisor |

---

## 完成后自动运行

```bash
npm install
npm run dev
```

```bash
python backend/api/main.py
```

或主站：

```bash
python web_platform.py
```

---

## 目录结构（生产级）

```
backend/
  engine/          trading_engine.py, event_bus.py
  strategy/        dragon.py, trend.py, mean_reversion.py
  portfolio/       optimizer.py, allocator.py, production_allocator.py
  ai/              regime_detector.py, fund_manager.py
  execution/       order_manager.py, execution_engine.py
  broker/          base.py, sim.py, qmt.py
  risk/            risk_engine.py, drawdown.py, position_limit.py
  data/            akshare_provider.py, cache_db.py
  api/             main.py
frontend/          chart, trading, portfolio, ai
scheduler/         trading_loop.py
```

## OpenClaw 提示词（复制即用）

```
你是顶级量化工程师。

目标：把当前项目升级为生产级A股量化交易系统。

要求：
1. 支持模拟交易
2. 支持多策略组合
3. 支持AI基金经理
4. 支持风险控制
5. 支持TradingView级图表
6. 前端可以下单操作
7. 后端可扩展QMT接口

任务列表：按 docs/CURSOR_PRODUCTION_TASKS.md 任务1～13 执行。

完成后自动运行：
npm install && npm run dev
python backend/api/main.py
```
