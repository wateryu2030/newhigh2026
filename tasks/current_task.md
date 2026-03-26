# Current Task

> Cursor 打开项目后优先读本文件，直接继续本任务。完成或切换任务时更新本文并同步 `backlog.md`。  
> **执行计划**：见 `docs/OPENCLAW_IMPROVEMENT_PLAN.md`（阶段 0–3，OpenClaw 自我进化集成）。

---

## 任务名称

阶段 0–1 已完成；下一阶段：2.x 前端与运维

---

## 目标

- 阶段 2：前端移动适配、React Query、Docker、监控告警、日志集中化。
- 阶段 3：OpenClaw 增强（RL）、实盘接口、测试、文档。

---

## 备注

- **阶段 0–1**：已完成（见 backlog）。
- **阶段 2**：2.1–2.5 均已完成。
- **阶段 3**：3.1–3.4 均已完成。
- **继续执行**：Playwright E2E 已接入（frontend/e2e/smoke.spec.ts、playwright.config.ts、npm run test:e2e）；Grafana 示例看板（monitoring/grafana-dashboard-example.json）；CI 新增 e2e job（Node + Playwright chromium）。
- **OpenClaw 设计检查（2026-03-08）**：`scripts/restart_and_check.sh` 全通过 — 34 项 PASS、0 FAIL。
- **可执行改进方案（2026-03-08）**：已按 `docs/IMPROVEMENT_PLAN_EXECUTABLE.md` 实施一批改进：
  - 架构：Celery 任务拆分为 data_tasks/scan_tasks/ai_tasks/strategy_tasks，celery_app 全量 include；多环境 config_loader + dev/staging/prod.yaml。
  - 数据：storage 抽象层（duckdb_adapter、postgres_adapter、redis_cache）。
  - 回测：strategy_allocator、portfolio_backtest（多策略组合回测）；data_loader 支持 strategy_id 过滤；POST /api/backtest/portfolio。
  - 执行与风控：order_lifecycle（NEW/SUBMITTED/FILLED/CANCELLED）；risk_monitor、risk_actions；GET /api/execution/equity_curve。
  - 运维：Gateway 启动时 init_app_env()；logging_config 增加 service、trace_id。
- **本轮改进（按 IMPROVEMENT_PLAN_EXECUTABLE）**：① 数据源扩展：tushare_source.py、binance_source.py 已注册（TUSHARE_TOKEN / BINANCE_KLINES_SYMBOL）；② JWT 认证：gateway/auth/jwt_auth.py、auth_middleware.py，登录返回 JWT，JWT_AUTH_REQUIRED=1 时校验 /api/*；③ 前端移动三页：底部导航改为 Dashboard/Market/AI Trading/Strategies/Portfolio，trade/strategies/portfolio/ai-trading 增加 min-h-screen pb-24，Portfolio 页接入 executionEquityCurve；④ Grafana 指标：gateway/metrics.py 记录 pipeline_stage_latency_seconds、gateway_requests_total，Grafana 示例看板增加 latency 与 requests 面板；⑤ E2E：smoke 增加 portfolio、ai-trading 导航用例，tests 增加 test_data_pipeline、test_strategy_engine、test_execution_engine。
- 后续可深化：RL 环境与训练、更多券商对接、策略市场仅真实数据（去 stub）。
- **迭代与数据时效**：`Makefile`（`make dev-check` / `gateway-restart` / `pipeline-editable`）；每日采集策略见 `docs/ITERATION_AND_DATA_SLA.md`（Tushare 优先、可调 `TUSHARE_DAILY_DAYS_BACK`）。
