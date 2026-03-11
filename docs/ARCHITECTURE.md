# AI对冲基金终极架构图 / AI Hedge Fund Ultimate Architecture

**目标不是做交易软件，而是做 AI Hedge Fund Operating System（AI对冲基金操作系统）。**  
核心是 **生产 Alpha**，不是「做交易」。

---

## 七层系统 (7-Layer System)

```
用户层           User Terminal (Web / Mobile Dashboard)
策略管理层       Strategy Control + Portfolio Control
AI研究层         AI Strategy Lab (Generator / Optimizer / RL)
量化交易层       Strategy Engine + Risk Engine + Execution Engine
数据层           Data Engine (Market / Onchain / Macro) + Feature Engineering
基础设施层       ClickHouse / Postgres / Redis / Kafka / K8s
进化控制层       Strategy Evolution Engine + AI Fund Manager
```

---

## 用户层 → API Gateway

```
                   ┌─────────────────────────────┐
                   │        USER TERMINAL        │
                   │   Web / Mobile Dashboard    │
                   └──────────────┬──────────────┘
                                  │
                           API Gateway  (gateway)
                                  │
        ┌─────────────────────────┴─────────────────────────┐
        │                                                   │
 Strategy Control                                    Portfolio Control
 策略管理系统 (strategy-engine + evolution)              投资组合系统 (portfolio-engine)
        │                                                   │
        └───────────────┬───────────────────────┬───────────┘
                        │                       │
                 Strategy Engine           Risk Engine
                 策略执行 (strategy-engine)   风控 (risk-engine)
                        │                       │
                        └───────────────┬───────┘
                                        │
                                 Execution Engine  (execution-engine)
                                   交易执行
                                        │
                                   Broker API
                              Binance / IB / CME
```

---

## AI研究与策略进化系统（核心）

```
                         ┌───────────────────────┐
                         │  AI STRATEGY LAB       │  (ai-lab)
                         │  AI策略研究中心        │
                         └───────────┬───────────┘
                                     │
        ┌────────────────────────────┼────────────────────────────┐
        │                            │                            │
Strategy Generator           Hyper Optimizer                RL Trader
策略生成 (strategy_generator)  参数优化 (optuna_optimizer)  强化学习 (rl_trader)
        │                            │                            │
        └───────────────┬────────────┴────────────┬──────────────┘
                        │                         │
                 Backtest Engine             Feature Engine
                   回测 (backtest-engine)      因子 (feature-engine)
                        │                         │
                        └───────────────┬─────────┘
                                        │
                                   Market Data  (data-engine)
```

---

## 策略进化引擎（真正核心）— 与普通量化的区别

```
                    ┌────────────────────────────┐
                    │ STRATEGY EVOLUTION ENGINE   │  (evolution-engine)
                    │ 策略进化引擎                │
                    └───────────────┬────────────┘
                                    │
                    ┌───────────────┼───────────────┐
                    │                               │
          Alpha Scoring Engine             Strategy Darwin Engine
          Alpha评分 (alpha_scoring)        策略达尔文淘汰 (darwin_engine)
                    │                               │
                    └───────────────┬───────────────┘
                                    │
                            Strategy Pool  (strategy_pool)
                             策略池
```

**策略生命周期：**

```
AI生成策略 (ai-lab)
      ↓
回测 (backtest-engine)
      ↓
风险评估 (risk-engine)
      ↓
Alpha评分 (evolution-engine)
      ↓
进入策略池 (strategy_pool)
      ↓
真实交易 (execution-engine)
      ↓
持续评估
      ↓
淘汰或进化 (darwin_engine)
```

---

## 数据系统

```
                   ┌───────────────────────────┐
                   │        DATA ENGINE        │  (data-engine)
                   │        数据引擎            │
                   └────────────┬──────────────┘
                                │
        ┌───────────────┬───────────────┬───────────────┐
        │               │               │
   Market Data      Onchain Data     Macro Data
   行情 (Binance等)  链上 (预留)       宏观 (预留)
        │
        └───────────────┬───────────────┐
                        │
                Feature Engineering  (feature-engine)
                   因子工程
```

**存储：** ClickHouse 行情 | Postgres 系统 | Redis 缓存 | Parquet 研究数据

---

## 交易执行系统

```
                    ┌─────────────────────┐
                    │ EXECUTION ENGINE    │  (execution-engine)
                    │ 交易执行引擎         │
                    └──────────┬──────────┘
                               │
                      Order Manager  (order_manager)
                       订单管理
                               │
                    Smart Order Router  (预留)
                        智能路由
                               │
                       Exchange APIs
                 Binance / IB / Coinbase
```

---

## 投资组合系统

```
                    ┌─────────────────────┐
                    │ PORTFOLIO ENGINE    │  (portfolio-engine)
                    │ 投资组合引擎         │
                    └──────────┬──────────┘
                               │
                     Position Manager  仓位管理
                               │
                    Allocation Engine  资金分配
```

**资金分配算法：** equal weight | risk parity | kelly criterion | volatility targeting

---

## 风控系统

```
                    ┌─────────────────────┐
                    │   RISK ENGINE       │  (risk-engine)
                    │   风控系统           │
                    └──────────┬──────────┘
                               │
             ┌─────────────────┼─────────────────┐
             │                 │                 │
        Drawdown Control   Exposure Limit   Volatility Limit
         回撤控制           仓位限制          波动控制
```

---

## AI基金经理控制系统（进化控制层）

```
                     ┌─────────────────────┐
                     │ AI FUND MANAGER     │  (ai-fund-manager)
                     │ AI基金经理           │
                     └──────────┬──────────┘
                                │
        ┌───────────────────────┼────────────────────────┐
        │                       │                        │
 Strategy Selector       Risk Controller        Capital Allocator
 策略选择                风险控制                资金配置
```

AI 自动：挑选策略、调整资金、关闭策略、启动新策略。

---

## 最终 AI 交易闭环

```
数据采集 (data-engine)
   ↓
因子生成 (feature-engine)
   ↓
AI生成策略 (ai-lab)
   ↓
回测验证 (backtest-engine)
   ↓
Alpha评分 (evolution-engine)
   ↓
策略进入池 (evolution-engine strategy_pool)
   ↓
组合分配 (portfolio-engine)
   ↓
自动交易 (execution-engine)
   ↓
收益反馈
   ↓
策略进化 (evolution-engine darwin)
```

**即：自进化 AI 对冲基金系统。**

---

## 模块与层级映射

| 层级 | 模块 | 说明 |
|------|------|------|
| 用户层 | frontend, gateway | Web/Mobile + API |
| 策略管理层 | strategy-engine, portfolio-engine | 策略与组合控制 |
| AI研究层 | ai-lab | Strategy Generator / Optuna / RL |
| 量化交易层 | strategy-engine, risk-engine, execution-engine | 执行与风控 |
| 数据层 | data-engine, feature-engine | 行情 + 因子 |
| 进化控制层 | evolution-engine, ai-fund-manager | Alpha 评分、策略池、达尔文淘汰、AI 基金经理 |
| 支撑 | backtest-engine, scheduler, core | 回测、调度、共享类型 |

---

## A股数据管道（Data Pipeline）

生产级 A 股数据流：**AkShare → 采集 → ETL → DuckDB（market.duckdb）→ API → 前端**。

- **库**：`data/market.duckdb`（与 quant.duckdb 分离），表：a_stock_basic, a_stock_daily, a_stock_realtime, a_stock_fundflow, a_stock_limitup, a_stock_longhubang。
- **采集**：data-pipeline/collectors（stock_list, daily_kline, realtime_quotes, fund_flow, limit_up, longhubang）。
- **调度**：`scripts/run_pipeline_daily.py`（每日 18:00 建议）、`scripts/run_pipeline_realtime.py`（交易时间每 30 秒）。
- **API**：`/api/market/realtime`、`/api/market/limitup`、`/api/market/fundflow`。

原则：数据可回测、实时可扫描、AI 可训练、策略可复盘。

---

## A股 AI 交易终端（完整方案）

详见 **docs/AI_TRADING_TERMINAL.md**：六大能力（数据/扫描/分析/策略/回测/交易）、数据流、模块映射、表结构、API、运行流程与自进化。统一实现：data-pipeline、market-scanner、ai-models、strategy-engine、backtest-engine、execution-engine、gateway、frontend。

---

## MVP 数据桥（DuckDB → API → 前端）

最小可用数据展示：**数据库 → Data Service → API Gateway → Frontend** 稳定通道。

```
DuckDB (data/quant.duckdb)
   ↓
Data Service Layer (core/data_service)
   db.py, market_service.py, strategy_service.py, portfolio_service.py
   ↓
API Gateway (gateway)  prefix=/api
   /api/stocks   /api/market/summary   /api/dashboard   /api/strategies   /api/portfolio
   ↓
Frontend (Next.js)
   /stocks 股票列表页   /  Dashboard   /market  行情
```

- **Data Service**：统一连接 DuckDB，不向 Gateway 暴露 SQL；标的列表、市场概览由 `market_service` 提供。
- **前端**：`/stocks` 使用 `api.stocks()` 展示 A 股表格（ts_code, name, industry）；Dashboard 使用 `api.dashboard()`、`api.dataStatus()` 展示标的数、日线范围。

---

## 下一步关键升级（建议）

1. **LLM Alpha Factory** — AI 策略自动生成系统设计  
2. **Alpha Score 模型** — 策略评分算法  
3. **Darwin Strategy Evolution** — 策略进化/淘汰算法  

这三块落地后，系统即成为 **真正的 AI Alpha 工厂**。
