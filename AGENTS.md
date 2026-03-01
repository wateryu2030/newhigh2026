# 生产级机构量化系统 — Cursor / OpenClaw 执行指南

## 目标
将项目升级为**生产级 A 股量化交易系统**（可真实落地、可扩展到千万资金、支持实盘）：
- A 股波段交易，100万–1000万资金
- 年化目标 20–40%，最大回撤 <15%
- TradingView 级图表 + 多策略组合 + AI 基金经理
- 自动交易系统 + 风控 + 订单状态机
- 完整前端交易面板

## 任务文档（按序执行）
1. **生产级任务清单**：`docs/CURSOR_PRODUCTION_TASKS.md` — 13 项生产级任务，TradingEngine 闭环、策略/组合/风控/订单/API/前端/调度。
2. **机构级任务**：`docs/CURSOR_UPGRADE_TASKS.md` — 原 13 项机构级任务。
3. **规则与架构**：`.cursor/rules/INSTITUTIONAL_UPGRADE.md` — 目录约定、代码规范。
4. **OpenClaw 提示词**：`docs/OPENCLAW_PROMPT.md` 或 `docs/CURSOR_PRODUCTION_TASKS.md` 末尾 — 复制到 OpenClaw 作为自动执行描述。

## 已实现模块（可直接用）
- **Backend**  
  - `backend/strategy/`：DragonLeaderStrategy、TrendInstitutionStrategy、AlphaFactorModel  
  - `backend/portfolio/`：PortfolioOptimizer、PortfolioAllocator  
  - `backend/ai/fund_manager.py`：AIFundManager  
  - `backend/execution/engine.py`：ExecutionEngine  
  - `backend/broker/`：BrokerBase、SimBrokerAdapter、QMTBrokerAdapter（占位）  
  - `backend/risk/`：RiskEngine、PositionLimit、DrawdownMonitor  
- **API**（Flask `/api`）：`/strategy/run`、`/portfolio/weights`、`/order`、`/account`、`/ai/decision`  
- **Frontend**：`chart/`（ChartEngine、IndicatorEngine、SignalOverlay）、`trading/`（OrderPanel、PositionPanel、AccountPanel）、`ai/AIDecisionPanel`，页面 `/institutional`  
- **调度与回测**：`scheduler/cron.py`、`scheduler/trading_loop.py`，`backtest/engine.py`、`backtest/metrics.py`  

## 启动方式
```bash
# 前端
cd frontend && npm install && npm run dev

# 后端（需在项目根目录，且 PYTHONPATH 含项目根）
python web_platform.py
# 或
.venv/bin/python web_platform.py
```

## 私募级扩展（已实现）
- **Kelly 与波动率约束**：`backend/portfolio/kelly.py`；`PortfolioOptimizer.kelly_weights()`。
- **私募级风控**：VaR、集中度、熔断 — `backend/risk/var_engine.py`、`concentration.py`、`circuit_breaker.py`；`RiskEngine` 已集成。
- **AI 择时**：LSTM/Transformer 骨架 — `backend/ai/timing_model.py`（规则择时可用，LSTM/Transformer 占位）。
- **RL 仓位模型**：`backend/ai/rl_position_model.py`；`AIFundManager.get_position_scale(state)` 可缩放总仓位。
- **QMT 实盘**：`backend/broker/qmt.py` + `config/broker.example.yaml`，配置驱动，实盘时实现 TODO 调用。
详见 **`docs/PRIVATE_FUND_SPEC.md`**。

## 优先级
P0 交易闭环 → P1 策略组合 → P2 AI 基金经理 → P3 图表系统。
