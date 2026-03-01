# Cursor 自动改造任务文档（机构级升级）

**目标**：将项目升级为机构级量化交易系统，包含：
1. TradingView 级图表  
2. 多策略组合系统  
3. AI 基金经理  
4. 自动交易引擎  
5. 实盘接口架构  
6. 完整前端交易面板  

---

## 任务 1：目录结构

确保以下目录存在（缺失则创建，已有则保留）：

```
backend/
  strategy/
  portfolio/
  ai/           # 已有，补充 fund_manager
  execution/    # 已有，补充 engine
  broker/       # 新建，与 trading/broker_interface 桥接
  risk/

frontend/src/
  chart/
  trading/
  portfolio/
  ai/
```

---

## 任务 2：策略模块 `backend/strategy/`

创建并实现：

- `backend/strategy/dragon_strategy.py` — 龙头突破策略（high_60、volume_ma20、rps）
- `backend/strategy/trend_strategy.py` — 趋势机构策略（ma20/ma60）
- `backend/strategy/alpha_model.py` — 因子评分（rps、momentum、fund_flow、volatility），可调用现有 `backend/ai/alpha_model`

---

## 任务 3：AI 基金经理 `backend/ai/`

- `backend/ai/fund_manager.py` — AIFundManager：`decide(market)` 返回策略权重，`detect_market_regime(market)` 判断牛熊，可复用 `market_regime`、`decision_engine`

---

## 任务 4：组合层 `backend/portfolio/`

- `backend/portfolio/optimizer.py` — PortfolioOptimizer：按 score 或风险平价分配权重
- `backend/portfolio/allocator.py` — 组合分配器：接收候选列表与权重上限，输出各标的仓位

---

## 任务 5：执行系统 `backend/execution/`

- `backend/execution/engine.py` — ExecutionEngine：`place_order(symbol, qty, side)`，内部调用现有 OrderManager / BrokerAPI

---

## 任务 6：券商适配层 `backend/broker/`

- `backend/broker/base.py` — 抽象 Broker 接口（buy/sell/cancel/query_position）
- `backend/broker/sim_adapter.py` — 模拟券商，对接现有 trading.Broker
- `backend/broker/qmt_adapter.py` — QMT 占位，便于后续实盘接入

---

## 任务 7：风控模块 `backend/risk/`

- `backend/risk/risk_engine.py` — 统一风控入口：仓位、回撤、单日亏损
- `backend/risk/position_limit.py` — 单标的/组合仓位上限
- `backend/risk/drawdown.py` — 回撤监控与熔断

---

## 任务 8：TradingView 图表前端 `frontend/src/chart/`

- `ChartEngine.ts` — 基于 lightweight-charts 的图表创建与数据绑定
- `IndicatorEngine.ts` — 指标管线（MA、MACD 等，可调后端 /api/kline?indicators=）
- `SignalOverlay.ts` — 买卖点、策略信号叠加

---

## 任务 9：交易面板前端 `frontend/src/trading/`

- `OrderPanel.tsx` — 下单、撤单
- `PositionPanel.tsx` — 持仓列表
- `AccountPanel.tsx` — 资金、可用、冻结

---

## 任务 10：AI 面板前端 `frontend/src/ai/`

- `AIDecisionPanel.tsx` — 展示 AI 组合决策、市场状态、策略权重

---

## 任务 11：API 接口

在 `api/routes.py` 或现有 Flask 路由中提供（可与 backend 新模块对接）：

- `POST /api/strategy/run` — 运行策略池，返回信号/评分
- `GET/POST /api/portfolio` — 组合权重、再平衡
- `POST /api/order` — 下单；`DELETE /api/order/<id>` — 撤单
- `GET /api/account` — 资金与账户摘要
- `GET /api/ai/decision` — AI 基金经理当前决策（权重、regime）

---

## 任务 12：回测与调度

- `backend/` 或项目根下 `backtest/`：`engine.py`、`metrics.py`（可与现有 run_backtest_db 等对接）
- `scheduler/cron.py` — 定时任务配置
- `scheduler/trading_loop.py` — 每日交易循环：拉数据 → 策略 → 组合 → 风控 → 执行

---

## 任务 13：验收与启动

- 确保可运行：`npm install && npm run dev`（前端）
- 确保可运行：`python web_platform.py` 或 `python main.py`（后端）
- 提供示例数据或 mock，使交易面板、AI 面板、图表在页面上可操作

---

## 执行顺序建议

1 → 2 → 3 → 4 → 5 → 6 → 7（后端主干）  
8 → 9 → 10（前端）  
11（API 串联）  
12 → 13（回测与调度、验收）
