# AI Hedge Fund (newhigh)

Goal:
**AI Hedge Fund Operating System（AI对冲基金操作系统）** — 不是做交易软件，而是 **生产 Alpha** 的自进化系统。

Capabilities:

- market data ingestion (market / onchain / macro 预留)
- factor generation
- strategy discovery (LLM Alpha Factory 方向)
- vectorized backtesting
- portfolio optimization (equal / risk parity / kelly / volatility targeting)
- automated execution (order manager, smart router 预留)
- **strategy evolution**: Alpha scoring, strategy pool, Darwin engine
- **AI fund manager**: strategy selector, risk controller, capital allocator
- reinforcement learning strategy evolution

System must support continuous autonomous strategy evolution.

**目标形态：** AI发现策略 / AI验证策略 / AI自动交易 / AI淘汰策略。人只负责风险限制与资金规模。

**架构图与层级：** 见 `docs/ARCHITECTURE.md`（七层 + 策略进化引擎 + AI 基金经理）。

---

# CORE STACK

Frontend
React
TypeScript
Tailwind
Chart.js
Zustand

Backend
Python
FastAPI

AI
PyTorch
StableBaselines3
Optuna

Data
ClickHouse
PostgreSQL
Redis

Infra
Kafka
Docker
Kubernetes

---

# ROOT STRUCTURE

newhigh (project root)

core
data-engine
feature-engine
strategy-engine
backtest-engine
portfolio-engine
risk-engine
execution-engine
ai-lab
evolution-engine      # 策略进化引擎：Alpha 评分、策略池、达尔文淘汰
ai-fund-manager      # AI 基金经理：策略选择、风控、资金配置
alpha-factory        # 第二阶段：策略工厂
alpha-scoring        # Alpha 评分引擎
strategy-evolution   # 遗传进化引擎
simulation-world     # 市场模拟（RL）
meta-fund-manager    # AI 基金经理大脑
scheduler
gateway
frontend
infra
docs

Each module: src/  tests/  Dockerfile  README.md

---

# DATA FLOW

Market Data
↓
Feature Engine
↓
Strategy Engine
↓
Backtest Engine
↓
Risk Engine
↓
Portfolio Engine
↓
Execution Engine
↓
Performance Feedback
↓
AI Evolution

---

# CORE MODULE REQUIREMENTS

DATA ENGINE

Responsibilities
collect market data
normalize OHLCV
stream realtime data

Sources
Binance
Yahoo Finance

Storage
ClickHouse
Tables: market_1m  market_5m  market_1h  market_1d

---

FEATURE ENGINE

Input: OHLCV
Generate: RSI  MACD  ATR  VWAP  Momentum  Volatility
Output: feature matrix

---

BACKTEST ENGINE

Library: vectorbt
Metrics: Sharpe  Sortino  MaxDrawdown  WinRate  ProfitFactor
Output: JSON result

---

STRATEGY ENGINE

Signal Types: BUY  SELL  HOLD
Base Strategies: trend_following  mean_reversion  breakout

---

PORTFOLIO ENGINE

Capital allocation: equal weight  risk parity  kelly
Functions: rebalance  position sizing

---

RISK ENGINE

Checks: max drawdown  max exposure  volatility
Example: if drawdown > 0.1  disable strategy

---

EXECUTION ENGINE

Connectors: Binance
Functions: place_order  cancel_order  fetch_positions

---

AI LAB

Modules: strategy_generator  rl_trader  hyper_optimizer
AI: LLM strategy discovery  Optuna optimization  RL training (PPO  SAC)

---

SCHEDULER

Pipeline: data_update → feature_generation → strategy_generation → backtest → risk_filter → deploy

---

FRONTEND

Pages: Dashboard  Market  Strategy Center  Backtest  Portfolio  AI Lab  Risk  Trade

---

SUCCESS CRITERIA

System must autonomously: generate strategies  run backtests  evaluate risk  alpha-score strategies  maintain strategy pool  evolve (Darwin)  allocate capital  deploy strategies  execute live trades  visualize results.

End goal: Self-evolving AI hedge fund core — **真正的 AI Alpha 工厂**.

---

# NEXT: 三大关键升级（建议）

1. **LLM Alpha Factory** — AI 策略自动生成系统设计
2. **Alpha Score 模型** — 策略评分算法（evolution-engine 已有基础）
3. **Darwin Strategy Evolution** — 策略进化/淘汰算法（evolution-engine 已有基础）
