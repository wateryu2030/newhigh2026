# 可直接交给 AI / 自动开发系统执行的改进方案

> 目标：从 **「能跑的平台」** 升级为 **「可持续进化的 AI 基金经理系统」**。  
> 结构按 8 个维度，每项含：问题、解决方案、优先级、实施任务（Cursor/自动开发可执行）、涉及目录。  
> 文档日期：2026-03-08。

---

## 一、架构改进

### 1.1 单机架构扩展能力不足

**问题**：当前 `system_runner` → 单进程 orchestrator，无并行、无任务隔离、无高可用；虽已引入 Celery，编排仍集中。

**解决方案**：改为事件驱动：Data Pipeline → Message Queue → Scanner Workers → AI Workers → Strategy Workers → Execution Workers；使用 Celery + Redis + worker pool。

**优先级**：P0

**实施任务**：
```
将 data/scan/ai/strategy 拆分为独立 Celery 任务模块，celery_app 统一 include。
- system_core/tasks/data_tasks.py   → run_data_task
- system_core/tasks/scan_tasks.py   → run_scan_task
- system_core/tasks/ai_tasks.py     → run_ai_task
- system_core/tasks/strategy_tasks.py → run_strategy_task
- system_core/tasks/pipeline_tasks.py → run_full_cycle_task（链式调用上述 4 个）
- system_core/celery_app.py → include 上述所有 tasks
```

**涉及目录**：`system_core/`、`system_core/tasks/`

---

### 1.2 多环境配置

**问题**：仅 `.env`，缺少 dev / staging / prod 分离。

**解决方案**：新增 `config/dev.yaml`、`staging.yaml`、`prod.yaml`；通过 `APP_ENV=dev` 加载对应配置。

**实施任务**：
```
- config/config_loader.py：按 APP_ENV 加载 yaml，与 core.config 合并
- config/dev.yaml、config/staging.yaml、config/prod.yaml：各环境差异项（api_port、celery_broker、execution_simulated 等）
```

**涉及目录**：`config/`、`core/src/core/config.py`

---

## 二、数据系统改进

### 2.1 单 DuckDB 限制

**问题**：DuckDB 单文件、写并发有限。

**解决方案**：DuckDB 做分析/回测；PostgreSQL 做交易（订单/持仓/策略）；Redis 做实时行情缓存。新增存储抽象层，便于后续切换。

**优先级**：P1

**实施任务**：
```
- storage/duckdb_adapter.py：封装 get_conn、ensure_tables、读写的统一接口
- storage/postgres_adapter.py：占位接口（connect、orders/positions 表），可选安装 psycopg2
- storage/redis_cache.py：封装 get_client、get/set 行情缓存，可选安装 redis
- storage/__init__.py：导出 get_analysis_store、get_trade_store、get_cache（按配置返回 duckdb/postgres/redis）
```

**涉及目录**：`core/` 或新建 `storage/`（与 core 同级）

---

### 2.2 数据源扩展

**问题**：当前仅 akshare。

**解决方案**：A 股增加 Tushare、同花顺/东财适配器；加密 Binance/OKX；宏观 FRED。通过 data_pipeline.data_sources 插件注册。

**实施任务**：
```
- data-pipeline/src/data_pipeline/data_sources/tushare_source.py：注册 tushare_daily（需 TUSHARE_TOKEN）
- data-pipeline/src/data_pipeline/data_sources/binance_source.py：注册 binance_klines（可选）
- 在 data_sources/__init__.py 中 register_source 新源
```

**涉及目录**：`data-pipeline/src/data_pipeline/data_sources/`

---

## 三、回测与策略系统

### 3.1 多策略组合回测

**问题**：当前仅单策略回测。

**解决方案**：组合回测：strategies → portfolio allocator → multi-strategy backtest（按权重汇总资金曲线与指标）。

**实施任务**：
```
- backtest-engine/src/backtest_engine/strategy_allocator.py：输入策略列表与权重或等权，输出各策略资金分配比例
- backtest-engine/src/backtest_engine/portfolio_backtest.py：调用 run_backtest_from_db 对每个策略跑回测，再按权重汇总 equity_curve 与 sharpe/max_drawdown
- Gateway：POST /api/backtest/portfolio 接受 strategy_ids + weights，返回组合资金曲线与指标
```

**涉及目录**：`backtest-engine/`、`gateway/`

---

### 3.2 AI 策略生成闭环

**问题**：当前 AI → signals，缺少 AI → strategy → backtest → ranking 闭环。

**解决方案**：新增 strategy_lab 模块：strategy_generator（输入 market_emotion、hotmoney、themes → strategy_definition）、strategy_evaluator、strategy_registry。

**实施任务**：
```
- strategy-engine 或新建 strategy_lab/：strategy_generator.py（读 market_emotion、top_hotmoney_seats、main_themes，输出策略定义 JSON）
- strategy_evaluator.py：调用 backtest_engine 回测并返回得分
- strategy_registry.py：与 strategy_market 表对接，注册/更新策略
```

**涉及目录**：`strategy-engine/` 或 `strategy_lab/`、`backtest-engine/`、`gateway/`

---

## 四、执行与风控

### 4.1 交易执行追踪（订单生命周期）

**问题**：缺少订单状态流转（NEW → SUBMITTED → FILLED / CANCELLED）。

**解决方案**：统一状态：NEW、SUBMITTED、FILLED、CANCELLED；表 orders、trades、positions、portfolio_equity（或沿用 sim_* 并扩展 status 枚举）。

**实施任务**：
```
- execution-engine：sim_orders 表已有 status；在 simulated/engine 中明确状态机：pending → submitted → filled / cancelled
- execution-engine/src/execution_engine/order_lifecycle.py：OrderState 枚举，transition(order_id, event)，写回 sim_orders
- Gateway：GET /api/execution/orders、GET /api/execution/equity_curve（从 sim_account_snapshots 聚合）
```

**涉及目录**：`execution-engine/`、`gateway/`

---

### 4.2 风控升级

**问题**：需更多规则类型与违规后的动作。

**解决方案**：新增规则：max_position_size、max_daily_loss、max_drawdown、max_leverage；风控违规时执行动作（拒绝下单、减仓、告警）。

**实施任务**：
```
- risk-engine/src/risk_engine/risk_monitor.py：定时或按请求评估当前持仓与资金曲线，返回 violations 与建议动作
- risk-engine/src/risk_engine/risk_actions.py：execute_action(violation) → reject_order | reduce_position | alert；与 execution-engine 联动
- risk_rules 表或配置支持 rule_type：max_position_size、max_daily_loss、max_drawdown、max_leverage
```

**涉及目录**：`risk-engine/`、`execution-engine/`、`data-pipeline/`（risk_rules 表）

---

## 五、前端体验升级

### 5.1 移动端核心视图

**重点三页**：AI Trade（AI decision、confidence、reason）；Strategy Market（Strategy、Return、Sharpe、Drawdown）；Portfolio（持仓与资金曲线）。

**实施任务**：
```
- frontend：确保 /trade（AI Trade）、/strategies（Strategy Market）、/portfolio（Portfolio）在移动端有专用布局或底部导航高亮
- frontend/src/app/(mobile)/ 或响应式：ai-trade、strategy-market、portfolio 三大视图优先适配小屏
```

**涉及目录**：`frontend/src/app/`、`frontend/src/components/`

---

### 5.2 数据加载体验

**实施任务**：统一使用 LoadingState、ErrorState、EmptyState 组件；所有列表/详情页在 loading/error/empty 时展示对应态。

**涉及目录**：`frontend/src/components/`

---

## 六、可维护性与运维

### 6.1 统一日志

**问题**：日志分散。

**解决方案**：JSON logging，结构含 timestamp、service、level、message、trace_id。

**实施任务**：
```
- core/src/core/logging_config.py：在 JsonFormatter 的 log_obj 中增加 service（如 os.environ.get("SERVICE_NAME","newhigh")）、trace_id（从 contextvars 或请求头获取，可选）
```

**涉及目录**：`core/src/core/logging_config.py`、`gateway/`（请求中间件注入 trace_id）

---

### 6.2 可观测性

**实施任务**：新增指标 data_pipeline_latency、scan_latency、ai_latency、trade_latency；Prometheus 暴露；Grafana 示例看板已存在可补充上述指标。

**涉及目录**：`gateway/`、`monitoring/`、`system_core/`

---

## 七、安全与合规

### 7.1 API 认证

**问题**：当前无认证。

**解决方案**：JWT 认证；登录接口签发 token，受保护路由校验。

**实施任务**：
```
- gateway/src/gateway/auth/jwt_auth.py：签发与校验 JWT（SECRET_KEY、过期时间）
- gateway/src/gateway/auth/auth_middleware.py：对 /api/* 除 /api/auth/login、/health 外校验 Authorization: Bearer <token>
```

**涉及目录**：`gateway/`

---

### 7.2 审计日志

**实施任务**：记录登录、交易、策略修改、系统配置变更；表 audit_log 已存在，扩展字段或新增 audit_logs 表（user_id、action、resource、old_value、new_value、created_at）。

**涉及目录**：`gateway/`、`data-pipeline/`（表结构）

---

## 八、测试体系

**实施任务**：单元测试 + 集成测试 + E2E；新增 tests/test_data_pipeline.py、test_strategy_engine.py、test_execution_engine.py；保持 tests/test_smoke.py 与 Playwright e2e。

**涉及目录**：`tests/`、`data-pipeline/tests/`、`strategy-engine/tests/`、`execution-engine/tests/`、`frontend/e2e/`

---

## 九、最关键升级：AI 进化引擎

**目标**：策略池 → 回测 → 评分 → 淘汰 → 变异 → 新策略，形成闭环。

**实施任务**：
```
- openclaw_engine/：已有 genetic、evaluation、population、evolution_orchestrator
- 确保 genetic_algorithm.py / strategy_mutator.py / fitness_function.py 与 backtest + strategy_market 打通：fitness 用回测 sharpe/收益/回撤，优胜写入 strategy_market
- Celery run_evolution_task 已存在；确保进化结果写回 strategy_market 并更新前端策略市场页数据源为真实表
```

**涉及目录**：`openclaw_engine/`、`backtest-engine/`、`gateway/`、`frontend/`

---

## 十、务实优先（建议先做）

1. **策略市场真实化**：GET /api/strategies/market 与前端策略页仅从 strategy_market 表与回测结果读取，去除 stub。
2. **组合回测**：实现 portfolio_backtest + strategy_allocator，并暴露 POST /api/backtest/portfolio。
3. **执行与资金曲线**：GET /api/execution/equity_curve 从 sim_account_snapshots 聚合；订单状态机在 simulated 中明确。

完成上述三项后，系统即成为 **可运行的 AI 基金经理平台**，再按本文档其余项分阶段实施。

---

*本文档可直接交给 Cursor 或自动开发系统按「实施任务」与「涉及目录」执行。*
