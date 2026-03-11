# 项目交接文档（供其他 AI 提出改进与建议）

> 本文档描述「红山量化 / AI 基金经理」项目当前状态，供后续 AI 或人类开发者快速了解全貌并提出**改进建议与落地方案**。请从文末「建议维度」出发，给出可执行、可排期的改进项。

---

## 一、项目一句话

**A 股量化 + 情绪/游资/主线 AI 分析 + 统一调度 + 回测/策略市场/资金曲线/决策解释的前后端一体平台**；目标演进为「AI 生成策略 → 回测评估 → 自动交易，人只做监督」的 AI 基金经理系统。

---

## 二、愿景与目标（docs/vision.md）

- **AI 基金经理**：自动策略生成、评估、优化；远期多 Agent（Macro / Quant / PM / Trader）。
- **交易系统**：数据 → 扫描 → AI → 策略信号 → 回测 → 风控 → 执行，全链路可运行、可监控。
- **可视化**：Dashboard、系统监控、策略市场、资金曲线、AI 决策解释；远期移动端核心视图。

---

## 三、当前已实现（能跑通的部分）

| 模块 | 说明 |
|------|------|
| **统一数据库** | 单库 `data/quant_system.duckdb`，管道 + 扫描 + AI + 策略 + 日K/标的/新闻 共用；环境变量 `QUANT_SYSTEM_DUCKDB_PATH` 可覆盖。 |
| **统一调度 system_core** | `python -m system_core.system_runner`（或 `--once`）：data_orchestrator → scan_orchestrator → ai_orchestrator → strategy_orchestrator → system_monitor 写 `system_status`。 |
| **数据管道** | 股票池、日K、实时、资金流、涨停、龙虎榜（data-pipeline + duckdb_manager）；依赖 akshare。 |
| **市场扫描** | limit_up / fund_flow / volume_spike / trend / hotmoney_sniper → market_signals、sniper_candidates。 |
| **AI 模型** | emotion_cycle、hotmoney_detector、sector_rotation_ai → market_emotion、top_hotmoney_seats、main_themes 等。 |
| **策略引擎** | ai_fusion_strategy + trade_signal_aggregator → trade_signals。 |
| **回测** | backtest_engine：run_backtest_from_db（读日K+信号）、资金曲线、Sharpe/回撤等；POST /api/backtest/run、GET /api/backtest/result。 |
| **Gateway API** | /api/market/*、/api/strategy/signals、/api/system/status、/api/strategies/market、/api/ai/decision、/api/backtest/run（多标的、滑点、strategy_id 写入策略市场）、/api/simulated/*、/api/risk/rules、/api/risk/check、/api/evolution/run、/api/execution/mode（模拟/实盘开关）、/api/auth/login、/api/audit/logs、/api/data/sources、/api/data/incremental 等。 |
| **前端** | Next.js App Router：Dashboard、行情、策略池、AI 交易、系统监控等；移动端底部导航、PWA manifest；React Query + 通用加载/错误/空状态组件。 |
| **OpenClaw** | openclaw_engine：基因表示、遗传操作、多目标适应度（收益/回撤/换手）、RL 占位；Celery run_evolution_task、POST /api/evolution/run。 |
| **执行与风控** | execution-engine：模拟盘（sim_positions/orders/account_snapshots）、brokers 统一接口（SimulatedBroker/LiveBroker）、EXECUTION_MODE；risk-engine rules（risk_rules 表、evaluate、/api/risk/*）。 |
| **运维与文档** | Celery+Redis、配置中心化、Docker/docker-compose、Prometheus、JSON 日志（core/logging_config）；mkdocs、.github/workflows/test、pytest（gateway、openclaw_engine、smoke）。 |
| **Cursor 接力** | tasks/backlog.md、current_task.md；docs/OPENCLAW_IMPROVEMENT_PLAN.md（阶段 0–3 已实施）。 |

---

## 四、当前未完成 / 占位 / 薄弱点

| 类别 | 现状 |
|------|------|
| **回测** | 多标的组合回测、滑点/手续费已做；多策略并行资金分配仍可深化。 |
| **策略市场** | 回测结果可写入 strategy_market；GET /strategies/market 优先读该表；进化周期可自动写入新策略。 |
| **执行与风控** | 模拟盘+brokers 抽象+EXECUTION_MODE 已做；实盘对接 Binance；风控 rules 与 /api/risk/check 已做；对账与审计可深化。 |
| **数据** | 数据源抽象与增量更新（ashare_daily_kline、ashare_longhubang）已做；可扩展更多源与缓存。 |
| **AI/策略** | OpenClaw 遗传+多目标+RL 占位已做；LSTM/RL Trader 未做。 |
| **API** | 部分仍为 stub：portfolio/weights、evolution（GET）、trades、alpha-lab 等返回示例数据。 |
| **前端** | 移动端底部导航与 PWA 已做；部分页可进一步用 React Query hooks 与空状态组件。 |
| **运维** | 健康检查、Prometheus、JSON 日志、Docker 已做；Grafana 与告警规则为示例。 |
| **测试与文档** | pytest（gateway、openclaw、smoke）、CI 已做；mkdocs 已配置；前端 Playwright E2E（e2e/smoke.spec.ts）及 CI e2e job 已接入；Grafana 示例看板见 monitoring/grafana-dashboard-example.json。 |

---

## 五、技术栈与关键路径

- **语言**：Python（管道/扫描/AI/策略/回测/Gateway）、TypeScript/React（前端）。
- **数据**：DuckDB 单文件 `data/quant_system.duckdb`；入口 `data_pipeline.storage.duckdb_manager`（get_conn、get_db_path、ensure_tables）。
- **运行入口**：`python -m system_core.system_runner`（循环 60s 一轮）；Gateway：`uvicorn gateway.app:app --reload --host 0.0.0.0 --port 8000`；前端：`cd frontend && npm run dev`，默认请求 `http://127.0.0.1:8000/api`（`NEXT_PUBLIC_API_TARGET`）。
- **关键目录**：`system_core/`、`data-pipeline/`、`market-scanner/`、`ai-models/`、`strategy-engine/`、`backtest-engine/`、`gateway/`、`frontend/`；详见 `PROJECT_STATUS.md` 第二节。

---

## 六、如何跑通一次（最小步骤）

1. 创建并激活虚拟环境，安装依赖（含 akshare、duckdb、vectorbt、fastapi、next 等）。
2. **先启动 Gateway**：`uvicorn gateway.app:app --reload --port 8000`（在仓库根或 gateway 目录，视 PYTHONPATH 而定）。
3. 跑一轮数据与信号（二选一）：  
   - `python -m system_core.system_runner --once`  
   - 或 `python scripts/ensure_market_data.py` + `python scripts/run_full_cycle.py`
4. 若需日K/新闻：`python scripts/copy_astock_duckdb_to_newhigh.py`（目标默认 quant_system.duckdb）。
5. 启动前端：`cd frontend && npm run dev`，打开 http://localhost:3000；系统监控、AI 交易、策略池、回测与资金曲线、AI 决策解释 等页可验证。

---

## 七、已知风险与限制

- **数据与依赖**：无数据时多数 API 返回空或默认值；akshare 限流/失败时管道静默 return 0。
- **单机单进程**：system_core 单进程循环；Gateway 单实例；无分布式与高可用设计。
- **安全与合规**：无认证/鉴权；无审计日志；实盘未接，合规与风控流程未体现。
- **文档与代码一致性**：部分文档仍写 market.duckdb/quant.duckdb，实际已统一为 quant_system.duckdb；API 列表以 PROJECT_STATUS 与 gateway 代码为准。

---

## 八、请接盘 AI 从以下维度提出改进建议

请基于上文事实，从下列维度给出**具体、可落地**的改进建议（每项尽量包含：问题简述、建议方案、优先级或阶段、涉及目录/文件）。

1. **架构**  
   单库单进程的边界、扩展点；是否引入消息队列/任务队列；多环境（开发/预发/生产）与配置管理。

2. **数据**  
   数据源扩展、缓存与时效、一致性、备份与迁移；a_stock_* 与 daily_bars/stocks/news_items 两套表结构的长期策略。

3. **回测与策略**  
   多策略回测、资金分配、滑点/手续费建模；策略市场与真实收益/回测指标打通；AI 生成策略 → 回测 → 入库闭环。

4. **执行与风控**  
   实盘/模拟盘开关、风控硬约束、订单与成交落库、对账与审计。

5. **前端与体验**  
   移动端核心视图、加载与错误态、无数据引导、可访问性与性能。

6. **可维护性与运维**  
   统一日志、链路追踪、健康检查、告警、部署与发布流程、Cursor/任务文档的可持续更新。

7. **安全与合规**  
   认证/鉴权、敏感配置、审计日志、合规留痕。

8. **其他**  
   测试（单测/集成/ E2E）、文档与注释、依赖与版本锁定、开源与合规等。

---

**参考文档**：`PROJECT_STATUS.md`（详细状态）、`docs/PROJECT_STATUS_AND_DATA_SUMMARY.md`（**项目现状与数据总结**，含程序与数据情况，供外部分析后改进）、`docs/vision.md`、`docs/roadmap.md`、`docs/ARCHITECTURE.md`、`docs/CURSOR_RELAY.md`、`tasks/backlog.md`。  
**执行计划（OpenClaw 自我进化与架构升级）**：`docs/OPENCLAW_IMPROVEMENT_PLAN.md`（阶段 0–3 任务分解、技术决策、验收与风险）。  
**前后端联调检查**：先启动 Gateway（`uvicorn gateway.app:app --host 127.0.0.1 --port 8000`），再执行 `bash scripts/check_frontend_backend.sh`，可验证前端调用的所有 API 是否返回 200 且结构符合预期。
