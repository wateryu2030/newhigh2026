# 项目现状与数据总结

> 供团队或外部分析后继续改进。包含**程序/代码现状**与**数据现状**，便于制定后续改进方案。  
> 文档日期：2026-03-08。

---

## 一、项目定位与目标

- **一句话**：A 股量化 + 情绪/游资/主线 AI 分析 + 统一调度 + 回测/策略市场/资金曲线/决策解释的前后端一体平台；目标演进为「AI 生成策略 → 回测评估 → 自动交易，人只做监督」的 AI 基金经理系统。
- **愿景**：AI 基金经理（自动策略生成、评估、优化）；全链路可运行、可监控；Dashboard、策略市场、资金曲线、AI 决策解释；远期多 Agent、移动端核心视图。

---

## 二、程序与代码现状

### 2.1 目录与模块

| 目录/模块 | 说明 |
|-----------|------|
| **core/** | 配置中心（config.py、pydantic-settings）、日志（logging_config.py JSON）、统一 DB 路径 |
| **data-pipeline/** | 数据采集（stock_list、daily_kline、realtime、fund_flow、limit_up、longhubang）、DuckDB 存储（duckdb_manager）、数据源抽象（data_sources/ashare_daily_kline、ashare_longhubang）与增量 run_incremental |
| **data-engine/** | 与 data-pipeline 共用 quant_system.duckdb；含 ClickHouse 存储（可选）、connector_astock_duckdb |
| **feature-engine/** | 特征计算（与日K/策略/回测对接） |
| **market-scanner/** | 涨停/资金流/量能/趋势/游资狙击 → market_signals、sniper_candidates |
| **ai-models/** | emotion_cycle、hotmoney_detector、sector_rotation_ai → market_emotion、top_hotmoney_seats、main_themes |
| **strategy-engine/** | ai_fusion_strategy、trade_signal_aggregator → trade_signals |
| **backtest-engine/** | 从 quant_system.duckdb 读日K与信号；多标的、滑点/手续费；资金曲线、Sharpe/回撤等；回测结果可写 strategy_market |
| **portfolio-engine/** | 组合与资金配置 |
| **risk-engine/** | 可配置规则（risk_rules 表）、evaluate、与 execution step_simulated(risk_check) 联动 |
| **execution-engine/** | 模拟盘（sim_positions/sim_orders/sim_account_snapshots）、brokers（BaseBroker、SimulatedBroker、LiveBroker）、EXECUTION_MODE、/api/execution/mode |
| **openclaw_engine/** | 策略基因、遗传操作、多目标适应度、RL 占位；evolution_orchestrator、Celery run_evolution_task |
| **system_core/** | 统一调度：data_orchestrator → scan → ai → strategy → system_monitor；可异步化（Celery） |
| **scheduler/** | 定时任务（Celery Beat 等） |
| **gateway/** | FastAPI：/api/market、/api/strategies、/api/backtest、/api/simulated、/api/risk、/api/evolution、/api/execution/mode、/api/auth、/api/audit、/api/data/sources、/api/data/incremental、/health 等 |
| **frontend/** | Next.js App Router、Tailwind、Zustand、Recharts；Dashboard/行情/策略/alpha-lab/evolution/portfolio/risk/trade/reports/settings；移动端底部导航、PWA；React Query、LoadingSpinner/ErrorMessage/EmptyState |
| **infra/** | Docker、docker-compose（api/frontend/redis/prometheus）、monitoring（Prometheus、Grafana 示例） |
| **scripts/** | ensure_market_data、run_full_cycle、copy_astock_duckdb_to_newhigh、openclaw_evolution_cycle、restart_and_check、openclaw_check_design、run_tests 等 |

### 2.2 技术栈

- **后端**：Python 3.x、FastAPI、DuckDB、Celery+Redis、pydantic-settings、akshare（数据采集）。
- **前端**：Next.js、React、TypeScript、Tailwind、Zustand、Recharts；NEXT_PUBLIC_API_TARGET 指向 Gateway（默认 http://127.0.0.1:8000）。
- **运维**：uvicorn（Gateway :8000）、npm run dev（前端 :3000）、Docker/docker-compose、Prometheus、JSON 日志、mkdocs。

### 2.3 已实现功能概览

- **数据**：统一库 quant_system.duckdb；数据源插件与增量更新；管道 collectors 写入 a_stock_* 等表。
- **调度**：system_core 全链路 data→scan→ai→strategy→monitor；可选 Celery 异步。
- **回测**：多标的、滑点/手续费、回测结果写 strategy_market；POST /api/backtest/run、GET /api/backtest/result。
- **策略与 OpenClaw**：策略市场表与 API；OpenClaw 基因/遗传/多目标/进化调度；POST /api/evolution/run。
- **执行与风控**：模拟盘三表、brokers 抽象、EXECUTION_MODE；risk_rules 与 /api/risk/*、执行前风控检查。
- **API**：market、strategies、backtest、simulated、risk、evolution、execution/mode、auth/login、audit/logs、data/sources、data/incremental 等。
- **前端**：上述页面齐全；移动适配、PWA、React Query 与通用状态组件。
- **测试与 CI**：pytest（gateway、openclaw_engine、tests/test_smoke 等）、Playwright E2E（e2e/smoke.spec.ts）、.github/workflows/test（含 e2e job）。
- **OpenClaw 设计检查**：scripts/restart_and_check.sh 与 openclaw_check_design.sh；最近一次 34 项全通过。

### 2.4 已知缺口（程序侧）

- 部分 API 仍返回示例/stub 数据：如 portfolio/weights、evolution（GET）、trades、alpha-lab 等。
- RL Trader：仅占位，LSTM/RL 环境与训练未实现。
- 多策略回测资金分配、策略自动入库（生成→回测→通过则写入）可深化。
- 实盘：LiveBroker 已抽象，具体券商对接（如 Binance）与对账/审计可深化。
- 单机单进程：无分布式与高可用设计。

---

## 三、数据现状

### 3.1 统一存储

- **路径**：`data/quant_system.duckdb`（默认）；可通过环境变量 `QUANT_SYSTEM_DUCKDB_PATH` 或 `NEWHIGH_MARKET_DUCKDB_PATH` 覆盖。
- **管理入口**：`data_pipeline.storage.duckdb_manager`（get_db_path、get_conn、ensure_tables）；core/config 与 core/data_service/db 对齐同一路径。
- **使用方**：data-pipeline、market-scanner、ai-models、strategy-engine、backtest-engine、execution-engine、risk-engine、openclaw_engine、gateway、system_core 等均读写该库。

### 3.2 表结构（ensure_tables 创建）

**行情与基础**

| 表名 | 用途 |
|------|------|
| a_stock_basic | 股票池（code PK, name, sector 可选） |
| a_stock_daily | 日 K 线（code, date PK, open/high/low/close/volume/amount） |
| a_stock_realtime | 实时行情 |
| a_stock_fundflow | 资金流 |
| a_stock_limitup | 涨停池 |
| a_stock_longhubang | 龙虎榜（含 seat_name、buy_amount 等可选列） |

**与 astock 兼容的通用结构**

| 表名 | 用途 |
|------|------|
| daily_bars | 日 K（order_book_id, trade_date, adjust_type PK；复权等） |
| stocks | 标的列表（order_book_id PK, symbol, name, market, ...） |
| news_items | 新闻（symbol, title, content, sentiment_score 等） |

**扫描与 AI 输出**

| 表名 | 用途 |
|------|------|
| market_signals | 扫描信号（code, signal_type, score） |
| market_emotion_state / market_emotion | 情绪状态与每日指标 |
| hotmoney_signals / top_hotmoney_seats | 游资信号与席位胜率 |
| sector_strength / main_themes | 板块强度与主线题材 |
| trade_signals | 交易信号（code, signal, confidence, strategy_id, signal_score 等） |
| sniper_candidates | 游资狙击候选 |

**策略与系统**

| 表名 | 用途 |
|------|------|
| strategy_market | 策略市场（strategy_id PK, name, return_pct, sharpe_ratio, max_drawdown, status） |
| system_status | 系统运行状态（data/scanner/ai/strategy status） |
| risk_rules | 风控规则（rule_type, value, enabled） |
| audit_log | API 审计日志 |

**模拟盘**

| 表名 | 用途 |
|------|------|
| sim_positions | 模拟持仓（code, side, qty, avg_price） |
| sim_orders | 模拟订单（id, code, side, qty, price, status） |
| sim_account_snapshots | 资金快照（snapshot_time PK, cash, equity, total_assets） |

### 3.3 数据源与增量

- **数据源抽象**：`data_pipeline.data_sources` 提供 BaseDataSource、get_source、list_sources；当前注册：ashare_daily_kline、ashare_longhubang。
- **增量更新**：`data_pipeline.run_incremental(source_id, force_full=False)` 按数据源执行增量；Gateway 暴露 `/api/data/sources`、`/api/data/incremental`。
- **采集依赖**：管道主要依赖 akshare；限流或失败时管道可能静默返回，需监控与重试策略。
- **A 股数据从 astock 复制**：`scripts/copy_astock_duckdb_to_newhigh.py` 可将 astock 的 DuckDB 复制到 `data/quant_system.duckdb`，用于日K/标的/新闻等；目标库可与现有 ensure_tables 表并存（daily_bars/stocks/news_items 已定义）。

### 3.4 数据流简述

```
外部（AkShare 等）→ data-pipeline collectors → quant_system.duckdb（a_stock_* / daily_bars 等）
       ↓
market-scanner / ai-models → market_signals、market_emotion、trade_signals 等
       ↓
strategy-engine / backtest-engine / execution-engine / openclaw_engine 读写同一库
       ↓
Gateway 读库提供 /api/* → 前端消费
```

### 3.5 数据侧已知缺口

- 无数据时多数 API 返回空或默认值；需明确「无数据」的展示与引导。
- a_stock_* 与 daily_bars/stocks 两套结构长期并存，复制脚本与 API 映射需统一约定（如 order_book_id ↔ symbol）。
- 数据缓存、时效性、备份与迁移策略未成文；增量仅部分数据源接入。
- features_daily 等扩展表由其他脚本（如 init_newhigh_duckdb_extensions、compute_features_to_duckdb）创建/写入，未在 ensure_tables 中统一列出，需与数据管线文档对齐。

---

## 四、改进建议维度（供外部分析后落地方案）

可从以下维度分析并产出可执行、可排期的改进项（每项建议包含：问题简述、方案、优先级、涉及目录/文件）。

1. **架构**：单库单进程边界与扩展点；是否引入消息队列/任务队列；多环境与配置管理。
2. **数据**：数据源扩展、缓存与时效、一致性、备份与迁移；两套表结构长期策略；增量覆盖范围。
3. **回测与策略**：多策略资金分配、策略市场与真实收益/回测指标打通、AI 生成→回测→入库闭环。
4. **执行与风控**：实盘/模拟盘配置、风控硬约束、订单与成交落库、对账与审计。
5. **前端与体验**：移动端核心视图、无数据引导、可访问性与性能。
6. **可维护与运维**：统一日志、链路追踪、健康检查、告警、部署与发布、任务文档可持续更新。
7. **安全与合规**：认证/鉴权、敏感配置、审计日志、合规留痕。
8. **测试与文档**：单测/集成/E2E 覆盖、文档与注释、依赖与版本锁定。

---

## 五、参考文档与入口

| 文档 | 说明 |
|------|------|
| docs/PROJECT_HANDOFF_FOR_AI.md | 项目交接与建议维度 |
| PROJECT_STATUS.md | 详细状态与架构图 |
| docs/OPENCLAW_IMPROVEMENT_PLAN.md | 阶段 0–3 任务分解与验收 |
| docs/vision.md、docs/roadmap.md、docs/ARCHITECTURE.md | 愿景、路线图、架构 |
| tasks/current_task.md、tasks/backlog.md | 当前任务与待办 |
| docs/DUCKDB_SCHEMA.md | DuckDB 表结构说明（部分路径/表名以实际代码为准） |
| **docs/IMPROVEMENT_PLAN_EXECUTABLE.md** | **可直接交给 AI/自动开发执行的改进方案**（8 维度、任务与目录） |
| README.md | 运行与构建（venv、Gateway、前端、数据脚本、Docker） |

**运行入口**：  
- Gateway：`uvicorn gateway.app:app --host 0.0.0.0 --port 8000`  
- 前端：`cd frontend && npm run dev`  
- 一轮数据与信号：`python -m system_core.system_runner --once` 或 `python scripts/ensure_market_data.py` + `python scripts/run_full_cycle.py`  
- 设计检查：`bash scripts/restart_and_check.sh`

---

*本文档汇总当前程序与数据现状，便于通过其他方式分析后继续改进方案。*
