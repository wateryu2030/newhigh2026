# AI Hedge Fund Operating System

Goal:
Build a self-evolving AI trading system.

Core capabilities:

1 Market data ingestion
2 Factor generation
3 Strategy generation
4 Backtesting
5 Portfolio allocation
6 Risk control
7 Trade execution
8 Strategy evolution

---

# SYSTEM ARCHITECTURE

modules:

data-engine
feature-engine
backtest-engine
strategy-engine
portfolio-engine
risk-engine
execution-engine
ai-lab
scheduler
gateway
frontend

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
Alpha Scoring
↓
Portfolio Engine
↓
Risk Engine
↓
Execution Engine
↓
Performance Feedback
↓
Strategy Evolution

---

# DATA ENGINE

Responsibilities:

fetch market data
normalize OHLCV
store time series

Sources:

Binance
Yahoo Finance

Storage:

ClickHouse

Tables:

market_1m
market_5m
market_1h
market_1d

---

# FEATURE ENGINE

Input:

OHLCV

Generate indicators:

RSI
MACD
ATR
VWAP
Momentum
Volatility

Output:

feature matrix

---

# BACKTEST ENGINE

Library:

vectorbt

Metrics:

Sharpe
Sortino
MaxDrawdown
WinRate
ProfitFactor

---

# STRATEGY ENGINE

Signal types:

BUY
SELL
HOLD

Strategies:

trend_following
mean_reversion
breakout

---

# PORTFOLIO ENGINE

Allocation methods:

equal weight
risk parity
kelly

Functions:

rebalance
position sizing

---

# RISK ENGINE

Controls:

max drawdown
max exposure
volatility filter

Example rule:

if drawdown > 0.1
disable strategy

---

# EXECUTION ENGINE

Exchange connectors:

Binance

Functions:

place_order
cancel_order
fetch_positions

---

# AI LAB

Modules:

strategy_generator
hyper_optimizer
rl_trader

Capabilities:

LLM strategy discovery
Optuna optimization
RL training

Algorithms:

PPO
SAC

---

# SCHEDULER

Autonomous workflow:

data_update
feature_generation
strategy_generation
backtest
risk_filter
deploy

---

# SUCCESS CRITERIA

System can autonomously:

generate strategies
evaluate alpha
deploy strategies
execute trades
optimize itself
