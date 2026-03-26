# Backlog

> Cursor 可从本列表取任务，或由 planner 拆解后写入 `current_task.md`。完成一项后勾选并视情况更新。  
> **大计划**：`docs/OPENCLAW_IMPROVEMENT_PLAN.md`（阶段 0–3，OpenClaw 自我进化）。

---

## 数据系统

- [x] 每日调度：有 `TUSHARE_TOKEN` 时默认 Tushare 日 K + 跳过 akshare 批量（`TUSHARE_DAILY_DAYS_BACK` / `DAILY_AKSHARE_KLINE_LIMIT`，见 `docs/ITERATION_AND_DATA_SLA.md`）
- [ ] 接入更多数据源（如 Binance / Yahoo 等，与现有 A 股管道并列）
- [ ] 数据缓存与时效性策略（避免重复拉取、支持 T+0 延迟）
- [x] 统一数据库 quant_system.duckdb（已完成）
- [x] system_core 统一调度 data → scan → ai → strategy（已完成）

---

## 回测系统

- [ ] 多策略回测：支持多策略并行/串行、资金分配
- [x] 回测输出：资金曲线（equity curve）、按日（run_backtest_from_db + POST /api/backtest/run）
- [x] 风险指标：Sharpe、最大回撤、胜率、Calmar 等（backtest_engine.metrics + run_with_db）
- [x] 回测与 strategy-engine / trade_signals 对接（用现有信号跑回测，signal_source=trade_signals|market_signals）

---

## 策略与 AI

- [ ] LSTM / 其他价格预测模型（与现有 emotion/hotmoney/sector 并列）
- [ ] RL Trader：状态/动作/奖励设计，与 backtest-engine、execution-engine 对接
- [ ] 自进化策略池与 OpenClaw 循环联动

---

## 策略市场（Strategy Store）

- [x] 策略列表 API：GET /api/strategies/market（id、name、return_pct、sharpe_ratio、max_drawdown、status）
- [x] 前端策略市场页：/strategies 表格展示，按收益/Sharpe/回撤排序
- [ ] AI 生成策略入库流程：生成 → 回测 → 通过则写入策略池

---

## UI 与展示

- [x] 实时资金曲线图（GET /api/backtest/result、策略页回测表单 + EquityCurve dataPoints）
- [x] 策略排名页（与策略市场可合并或联动）
- [x] AI 决策解释区块：GET /api/ai/decision，AI 交易页展示信号 + 理由 + 因子标签
- [ ] 移动端核心视图（资金曲线、策略排名、AI 决策）

---

## 执行与风控

- [ ] 实盘/模拟盘开关与配置
- [ ] 风控硬约束（最大仓位、单日亏损上限等）与 execution-engine 联动
- [ ] 交易记录与对账（执行结果落库、与信号对照）

---

## 阶段 0–3（OpenClaw 改进计划）

- [x] 0.1 Celery 任务队列（system_core 异步化）
- [x] 0.2 配置中心化（core/config.py + pydantic-settings）
- [x] 0.3 模拟盘引擎基础（execution-engine 模拟订单与持仓）
- [x] 0.4 数据源抽象与增量更新
- [x] 0.5 健康检查与基础监控（/health 增强 + 可选 /metrics）
- [x] 1.1 回测引擎增强（多标的、滑点/手续费）
- [x] 1.2 策略市场数据闭环（回测结果写入、前端真实数据）
- [x] 1.3 风控模块（可配置规则）
- [x] 1.4 OpenClaw 进化引擎 V1（基因表示、遗传、评估）
- [x] 1.5 进化调度与集成
- [x] 1.6 认证与审计
- [x] 2.1 前端移动适配（Tailwind 响应式、底部导航、PWA manifest）
- [x] 2.2 数据获取层优化（React Query、LoadingSpinner/ErrorMessage/EmptyState、useApi hooks）
- [x] 2.3 容器化部署（frontend Dockerfile Next standalone、docker-compose api/frontend/redis/prometheus）
- [x] 2.4 监控告警（monitoring/prometheus.yml、README、alert_rules.example.yml）
- [x] 2.5 日志集中化（core/logging_config.py JSON、LOG_LEVEL/LOG_JSON、system_core 集成）
- [x] 3.1 OpenClaw 进化增强（multi_objective、rl/agent 占位）
- [x] 3.2 实盘接口封装（brokers/base、SimulatedBroker、LiveBroker、GET/POST /api/execution/mode）
- [x] 3.3 测试体系（pytest gateway/openclaw_engine/tests、.github/workflows/test.yml）
- [x] 3.4 文档自动化（mkdocs.yml、docs/index、monitoring、PROJECT_HANDOFF 同步）
- [x] E2E：Playwright 前端冒烟（e2e/smoke.spec.ts、CI e2e job）
- [x] Grafana：示例看板 JSON（monitoring/grafana-dashboard-example.json）

---

## 说明

- 优先级大致按阶段 1 → 2 → 3 → 4（见 `docs/roadmap.md`）；阶段 0–3 见 `docs/OPENCLAW_IMPROVEMENT_PLAN.md`。
- 代码目录见各模块：`backtest-engine/`、`strategy-engine/`、`frontend/`、`gateway/`、`system_core/` 等（见 `PROJECT_STATUS.md`）。
