# Cursor + OpenClaw 自动化提示词模板（newhigh / RedMountain）

本文档供在 Cursor Agent 中**整段复制**使用。每条含：任务目标、输入、执行步骤、期望输出、异常处理、涉及路径（与当前仓库一致）。

**仓库已对齐的实现**（持续迭代）：Celery `backtest_tasks`（含并行 `group` / `dispatch_parallel_backtests_async`）、`strategy_market_writer`、`pipeline_meta` / `backtest_task_errors`、`GET /api/system/health-detail` 与 **`GET /api/system/backtest-errors`**、可选 `redis_cache`、`POST /api/simulated/step` 默认风控、OpenClaw 入库门槛（`test_evolution_gate`）、首页 **HealthDetailStrip**、`AsyncState` 覆盖 **策略市场 `/strategies`、进化 `/evolution`、Alpha 工坊 `/alpha-lab`**（加载/错误/空态 + 移动端 `pb-24`）、**策略流水线** `POST /api/strategies/pipeline/*` 与前端 `api.pipeline*`（`frontend/src/api/client.ts`）。

**交叉索引**：根目录 `cursor_auto_improve_plan.yaml`、`OPENCLAW_TASK_TREE.yaml`、`OPENCLAW_EVOLUTION.yaml`、`tasks/backlog.md`。

**约定**：小步提交；`.env` 与密钥不入库；改 API 时同步 `frontend/src/api/client.ts`；前端可点击对外链接用 `https://htma.newhigh.com.cn/...`。

---

## 1️⃣ 并行策略回测调度

**任务目标**  
监控 backlog 中待回测策略，派发 Celery 任务，实现多策略、多标的并行回测（在现有 `system_core` + `backtest-engine` 上扩展，而非另起调度器）。

**输入**  
- 待回测列表：`strategy_id`、参数 JSON、标的列表、资金权重（可与 `tasks/backlog.md` 或后续 `strategy_backlog` 表对齐）  
- `system_status` / DuckDB 可用性

**执行步骤**  
1. 阅读 `tasks/backlog.md` 与 `system_core/celery_app.py`、`system_core/tasks/*.py`，确认是否已有可复用的 pipeline 任务形态。  
2. 若无专用回测任务：在 `system_core/tasks/` 新增 `backtest_tasks.py`（或等价模块），`include` 进 `celery_app.py`。  
3. 单任务签名包含：`strategy_id`、标的、滑点/手续费（对齐 `BACKTEST_FEE_RATE` / `backtest-engine` 默认）、可选 `init_cash`。  
4. 任务内调用 `backtest-engine` 已有入口（如 `run_backtest_from_db` / Gateway 等价逻辑），结果写入 DuckDB：优先复用 `strategy_market` 与 Gateway `_save_backtest_to_strategy_market` 的字段契约；若需独立历史表，在 `data_pipeline/storage/duckdb_manager.py` 的 `ensure_tables` 中新增并与 Gateway 对齐。  
5. 派发至 worker；可选：`group`/`chord` 并行多标的。  
6. 将任务 id / 状态写入可查询位置（`system_status` 扩展字段或新表），供 `/api` 或监控页读取。

**期望输出**  
- Celery 可调用的新任务名与参数文档（`system_core/README.md` 补充一行即可）  
- 回测结果持久化（`strategy_market` 或约定表）

**异常处理**  
- 派发失败：使用 Celery `autoretry_for` + `max_retries=3`；仍失败写入 DuckDB 错误表或 `logs/` 结构化日志  
- 回测异常：捕获后写入单行 `error` 字段或专用 `backtest_task_errors`（按需建表），避免 worker 静默崩溃

**涉及目录**  
`system_core/system_runner.py`、`system_core/celery_app.py`、`system_core/tasks/`、`backtest-engine/src/`、`gateway/src/gateway/endpoints.py`（若新增查询接口）、`tasks/backlog.md`  

**优先级**：高

---

## 2️⃣ 数据增量更新与缓存

**任务目标**  
自动增量拉取日 K、龙虎榜、资金流等，写入 DuckDB；**可选**增加 Redis 热缓存与 TTL（主仓当前以 DuckDB 为事实源，Redis 非必选）。

**输入**  
- 上次增量键（各 `BaseDataSource` 的 `get_last_key`）  
- 数据源：`data_pipeline.data_sources`（akshare/tushare/binance/fred 等）  
- `QUANT_SYSTEM_DUCKDB_PATH` / `get_db_path()`

**执行步骤**  
1. 阅读 `data-pipeline/src/data_pipeline/__init__.py` 的 `run_incremental(source_id)` 与 `storage/duckdb_manager.py` 的 `ensure_tables`。  
2. 在 `data_orchestrator` / 调度脚本中统一调用增量逻辑；缺失数据用现有 collectors 补齐。  
3. **若需 Redis**：新增薄模块（如 `data-pipeline/src/data_pipeline/cache/redis_cache.py`），key 带 `source_id`+日期，TTL 可配置；写入失败不得阻塞 DuckDB 主路径。  
4. **last_update**：可复用 `system_status.snapshot_time` 或在 `ensure_tables` 增加 `pipeline_meta(key,value)` 小表。  
5. 更新 `.env.example`（Redis URL、TTL、开关）。

**期望输出**  
- DuckDB 表更新可验证（脚本或 `GET /api/data/status`）  
- 可选 Redis 命中说明

**异常处理**  
- 下载失败：重试 2 次（间隔可配置），记录 logger  
- Redis 失败：降级为仅 DuckDB，并记 `warning` 日志（不设即时飞书则省略「告警」）

**涉及目录**  
`data-pipeline/src/data_pipeline/storage/duckdb_manager.py`、`data-pipeline/src/data_pipeline/data_sources/`、`system_core/data_orchestrator.py`、`scripts/run_pipeline_*.py`

**优先级**：高

---

## 3️⃣ AI 策略生成与回测闭环

**任务目标**  
OpenClaw 生成策略 → 校验 → 回测 → 筛选 → 写入 `strategy_market`，与现有进化 API 一致。

**输入**  
- `openclaw_engine.run_evolution_cycle` 或等价生成结果  
- DuckDB：`a_stock_daily`、信号表、`strategy_market`  
- 阈值：Sharpe、最大回撤（环境变量或配置常量）

**执行步骤**  
1. 读 `openclaw_engine/`、`evolution-engine/`、`OPENCLAW_EVOLUTION.yaml`。  
2. 生成物落临时结构（内存 + 可选 JSON 列），校验仓位/参数上下界。  
3. 调用 `backtest-engine` 与现有 Gateway 回测路由契约（`/api/backtest/` 相关）。  
4. 过滤：未过阈值则写日志，不入 `strategy_market`。  
5. 通过则调用与 `gateway/endpoints.py` 中 `_save_backtest_to_strategy_market` 一致的字段。  
6. 保证 `GET /api/strategies` / 策略榜与前端策略页仍兼容。

**期望输出**  
- 可重复执行的一轮闭环（脚本或 Celery 任务）  
- `strategy_market` 新增/更新行可查询

**异常处理**  
- 回测失败：结果写入进化任务 `evolution_tasks.result` 或错误字段，不覆盖优质历史记录  
- 非法参数：丢弃并记 OpenClaw / 应用日志

**涉及目录**  
`openclaw_engine/`、`evolution-engine/`、`strategy-engine/`、`backtest-engine/`、`gateway/src/gateway/endpoints.py`

**优先级**：高

---

## 4️⃣ 模拟盘 / 实盘执行与风控

**任务目标**  
按 `EXECUTION_MODE` 选择 `SimulatedBroker` / `LiveBroker`，执行前走 `risk-engine` 规则，写入审计与持仓相关表。

**输入**  
- `execution_engine.brokers.registry.execution_mode()`  
- `risk_rules` / `risk-engine` 配置  
- 订单参数：`code`、`side`、`qty`、`price`

**执行步骤**  
1. 读 `execution-engine/src/execution_engine/`、`risk-engine/`、`gateway` 中 `/api/simulated`、`/api/execution` 路由。  
2. 下单前跑风控：仓位上限、单日亏损、相关性（若已有接口则扩写，无则增量实现）。  
3. `simulated`：走 `SimulatedBroker`；`live`：仅在有明确 broker 配置时启用，默认禁止误切生产。  
4. 审计：扩展沿用 Gateway `audit_log`（DuckDB）与中间件；敏感操作可额外记 `user_sub`。  
5. 持仓：`sim_orders` / `sim_positions` 已有表结构时对齐更新。

**期望输出**  
- 一致的订单生命周期（pending → filled / cancelled）  
- 可查询的风控拒绝原因

**异常处理**  
- 风控不通过：HTTP 4xx + 不落 executable 单  
- 下单失败：有限重试；错误写入响应体 + 日志（避免泄露密钥）

**涉及目录**  
`execution-engine/src/execution_engine/`、`risk-engine/src/risk_engine/`、`gateway/src/gateway/endpoints.py`、`gateway/src/gateway/app.py`

**优先级**：高

---

## 5️⃣ 移动端策略展示与空状态

**任务目标**  
优化策略池相关页在移动端的加载、错误与空状态；与 `strategy_market` 数据一致。

**输入**  
- `GET /api/strategies` 或策略榜接口返回  
- 设备宽度 / `MobileBottomNav` 布局

**执行步骤**  
1. 使用 **Next App Router**：页面在 `frontend/src/app/`（非 `pages/strategy`）。定位策略市场、Alpha 工坊等相关 `page.tsx`。  
2. 复用 `frontend/src/components/AsyncState.tsx`、`PageLoading`、`PageError`、`EmptyState`。  
3. API 经 `frontend/src/api/client.ts`，超时与 502 提示与运维文档一致。  
4. **PWA**：若已有 `manifest`/SW 则迭代；无则仅评估，避免大范围重写。  
5. 资金曲线 / AI 说明块：对接已有组件（如 `EquityCurve`）与接口字段。

**期望输出**  
- 策略列表有空/错/载三种明确 UI  
- 核心移动路径可点击验收

**异常处理**  
- fetch 失败：用户可见错误 + 可选重试  
- 不引入第二套全局请求层（避免与现有 fetch 重复）

**涉及目录**  
`frontend/src/app/`、`frontend/src/components/`、`frontend/src/api/client.ts`

**优先级**：中

---

## 6️⃣ 健康检查与运维

**任务目标**  
汇总 Gateway、DuckDB、可选 Celery、Prometheus 指标，生成可读健康报告与告警钩子。

**输入**  
- `GET /health`、`GET /api/health`（`gateway/endpoints_health.py`）  
- `system_status`、`CELERY_*` 环境变量  
- `GET /metrics`（需 `prometheus_client`）

**执行步骤**  
1. 扩展 `build_health_payload` 或新增只读 `/api/system/health-detail`（遵循 `json_ok`/`json_fail` 惯例）。  
2. Celery：**可选** ping broker / inspect active（无 Redis 时返回 `skipped`）。  
3. 汇总输出 JSON，供脚本与 OpenClaw 定时读。  
4. 告警：邮件/Slack/Webhook 用环境变量 URL，失败写入日志；**不**硬编码密钥。  
5. Grafana：参考 `monitoring/grafana_gateway_dashboard.json`。

**期望输出**  
- 单次 CLI 或 HTTP 可拉取的健康摘要  
- 文档化环境变量

**异常处理**  
- 单项检查失败：整体 `degraded` 而非进程崩溃  
- 重试健康检查 1 次（可针对 DB 连接）

**涉及目录**  
`gateway/src/gateway/endpoints_health.py`、`gateway/src/gateway/endpoints.py`、`gateway/src/gateway/metrics.py`、`system_core/`、`monitoring/`

**优先级**：中

---

## 7️⃣ 安全与合规

**任务目标**  
JWT 签发与校验、请求审计、敏感配置仅环境变量。

**输入**  
- `JWT_SECRET` / `JWT_AUTH_REQUIRED`  
- `Authorization: Bearer` 头  
- 登录与敏感写路由列表

**执行步骤**  
1. 使用现有 `gateway/src/gateway/auth/jwt_auth.py`、`auth_middleware.py`，**避免**复制第二套校验逻辑。  
2. 扩展审计：在 `app.py` 中间件或路由装饰器中记录 `user_sub`、path、method（已与 `audit_log` 对齐的继续复用）。  
3. 策略/回测/下单等写操作：确认不在 JWT 白名单裸奔（只读行情可保持白名单）。  
4. 密钥：**禁止**写入 DuckDB 明文；仅 `os.environ` / `.env` 本地加载。

**期望输出**  
- 登录颁发 token；受保护路由 401 行为符合预期  
- `GET /api/audit/logs`（若已存在）可列出含 `user_sub` 的记录

**异常处理**  
- `pyjwt` 缺失时保持当前降级行为并打日志  
- 审计写入失败：降级为应用日志，不影响主响应

**涉及目录**  
`gateway/src/gateway/auth/`、`gateway/src/gateway/app.py`、`data-pipeline/src/data_pipeline/storage/duckdb_manager.py`（`audit_log`）

**优先级**：中

---

## 8️⃣ 自动测试与文档更新

**任务目标**  
为新增或关键路径补充 pytest /（可选）Playwright；文档以仓库内已有 `docs/`、`README` 为准（**主仓无 mkdocs 时勿强行引入**）。

**输入**  
- 新 API、新表字段、新 Celery 任务名

**执行步骤**  
1. `gateway/tests/`、`openclaw_engine/tests/`、`tests/test_smoke.py` 按需增量。  
2. 前端：`frontend` 下现有 Playwright 配置，按需加用例，保持 CI 时间可控。  
3. `.github/workflows/test.yml` 与依赖（如 `gateway[dev]` 含 `httpx`）对齐。  
4. 文档：更新与功能直接对应的 `docs/*.md` 或模块 README；**不**主动新建大型文档站点。

**期望输出**  
- CI 绿灯或明确 `xfail` 理由  
- 至少一条可复制的本地命令（与 CI 一致）

**异常处理**  
- 需 DuckDB 文件的测试：CI 中使用 mock / 跳过 / 内存库

**涉及目录**  
`gateway/tests/`、`tests/`、`openclaw_engine/tests/`、`frontend/`、`.github/workflows/`、`docs/`

**优先级**：中

---

## 一键复制块（Cursor Agent 系统前缀，可选）

在以上内容前追加：

```
你是 newhigh2026 仓库内的开发助手。优先阅读本任务「涉及目录」下现有实现，小步修改；
不引入与现有 Gateway + DuckDB + Next App Router 冲突的第二套框架。
完成任务后列出改动的文件路径与如何本地验证。
```

---

*文档版本随仓库迭代更新；与 `cursor_auto_improve_plan.yaml` 任务 id 可逐项对照执行。*

---

## 附录：与本文档相关的本地验证（摘录）

| 场景 | 命令或说明 |
|------|------------|
| Gateway 测试 | `pip install pytest httpx && pip install -e ./core -e ./gateway` 后：`pytest gateway/tests -v --tb=short`（与 `.github/workflows/test.yml` 一致） |
| 策略流水线闭环（HTTP） | `export GATEWAY=... JWT=... && bash scripts/strategy_pipeline_example.sh`；admin 审批见脚本末尾打印的 `curl` |
| AI 生成 → 可上架 | 流水线 `evolve_*` / `backtest_only` 产出 **staged**，仅 **`POST .../approve`（admin）** 写入 `strategy_market`；与 §3「闭环」一致 |
| 进化摘要 | `GET /api/evolution`：有 DuckDB 且 `evolution_tasks` 存在 **`success` + 非空 `result`** 时返回 `source: duckdb`（含 `staged` 最优 Sharpe）；否则 `source: demo` |
