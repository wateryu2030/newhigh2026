# 量化交易平台架构评估：数据挂接与前后端连接

**评估范围**：仓库 `newhigh` 全栈（`data-engine`、`data-pipeline`、`gateway`、`frontend`、`lib`、`scripts`）  
**评估日期**：2026-03-15（基于当前代码结构）  
**方法**：静态代码扫描 + 文档交叉验证；未在生产环境压测。

---

## 1. 总体评估摘要

| 维度 | 评级 | 摘要 |
|------|------|------|
| **数据挂接** | **良好 / 部分待改进** | 多源（AkShare、Tushare、Binance、Yahoo、本地 DuckDB）覆盖行情/新闻/股东/财报等；主存 DuckDB + 部分 ClickHouse；定时与脚本并存。完整性依赖本地库状态与外部 API 稳定性；股东多期覆盖仍不均衡（见 `docs/SHAREHOLDER_DATA_GAP_REPORT.md` 与 `scripts/check_top10_shareholders_coverage.py`）。 |
| **前后端连接** | **良好 / 安全待加强** | FastAPI 统一 `/api` 前缀，前端 `apiGet` + Next `rewrites` 同源代理；JSON 为主。全局状态以 React Context（语言）为主，无 Redux。错误多为 `throw` + 页面提示。**CORS 为 `*`，JWT 默认关闭**，生产需收紧。无统一 OpenAPI 消费层；部分端点返回 `{ok, error}` 与 HTTP 状态混用。 |

---

## 2. 数据挂接详细评估

### 2.1 数据源清单与接入方式

| 数据源 | 类型（实时/历史/基本面） | 接入方式 | 典型代码位置 |
|--------|--------------------------|----------|--------------|
| **东方财富 / AkShare** | 历史 K 线、分钟、情绪、龙虎榜、十大股东等 | Python API → 落 DuckDB / 直读 | `data-engine/connector_akshare.py`；`data-pipeline/collectors/*.py`（如 `daily_kline.py`、`longhubang.py`）；`data/collectors/financial_report.py`（股东） |
| **Tushare** | 日线、财新新闻等（需 token） | Python API | `data-engine/connector_tushare.py`；`data-pipeline/collectors/tushare_daily.py`、`caixin_news.py` |
| **Binance** | 实时/历史加密行情 | REST / WebSocket → ClickHouse 等 | `data-engine/connector_binance.py`、`realtime_stream.py`、`clickhouse_storage.py` |
| **Yahoo Finance** | 历史（含部分 A 股代码） | `yfinance` | `data-engine/connector_yahoo.py` |
| **本地 DuckDB（newhigh）** | 历史行情、股东、新闻、实时快照等 | Gateway / lib 只读连接 | `lib/database.py`（`QUANT_DB_PATH` / `data/quant_system.duckdb`）；`data_pipeline/storage/duckdb_manager.py`；`connector_astock_duckdb.py`（`quant.duckdb` 路径可配） |
| **热点/东财摘要（新闻条）** | 准实时文案 | Gateway 聚合读库或占位 | `gateway/.../endpoints.py`：`/news/hot-ticker` 等 |

**说明**：Gateway 大量端点优先读 **本地 DuckDB**（如 `GET /api/market/klines` 对 A 股日线走 `fetch_klines_from_astock_duckdb`），库空则返回空数组而非保证拉网补数（`endpoints.py` 约 L29–69）。

### 2.2 完整性检查

| 机制 | 位置 | 评价 |
|------|------|------|
| 数据状态 API | `GET /api/data/status` → `get_duckdb_data_status()` | 前端「数据」页可用；**不校验单标的时间断点细节** |
| A 股补全脚本 | `scripts/ensure_ashare_data_completeness.py`、`ensure_market_data.py` | **手动/流水线触发**；与 OpenClaw 文档中「进化前补数」描述一致 |
| 股东覆盖检查 | `scripts/check_top10_shareholders_coverage.py` | **可量化**：标的覆盖率、每股报告期分布、最新期是否满 10 条 |
| 文档化缺口 | `docs/SHAREHOLDER_DATA_GAP_REPORT.md` | 历史问题已部分缓解（采集器多期写入），**单期股票仍大量存在**时需持续补采 |
| 字段/异常值 | 各 ETL 分散 try/except | **无统一数据质量框架**（如 Great Expectations） |

**典型问题（证据导向）**：

1. **K 线**：A 股 DuckDB 不可用时 `get_klines` 返回 `data: []`（`endpoints.py`），前端易误判为「无数据」而非「后端未接库」。
2. **股东**：约 **96.8%** 标的曾有数据、**~5k 股仍仅 1 个报告期**（以本机一次脚本跑数为例，随库变化）。
3. **多库路径**：`quant_system.duckdb` vs `quant.duckdb`、环境变量并存，**运维需明确单一事实来源**。

### 2.3 更新机制

| 机制 | 说明 | 位置 |
|------|------|------|
| 定时调度 | 每日 18:00 任务、**02:00 十大股东**、实时约 30s | `scripts/start_schedulers.py`（注意其中 `project_root` 曾硬编码路径，部署时需与环境一致） |
| 手动/一次性 | 股东全量、`run_shareholder_collect.py` | `scripts/run_shareholder_collect.py` |
| Gateway 触发 | `POST /api/data/ensure-stocks`、`POST /api/data/incremental` 等 | `gateway/.../endpoints.py` |
| 事件驱动 | 较弱；以轮询 + 脚本为主 | — |

**时效性**：实时行情依赖调度频率与数据源；**前端默认 `cache: 'no-store'`**，减轻浏览器缓存导致的不一致。

### 2.4 存储设计

- **主表**：DuckDB（`top_10_shareholders`、`a_stock_basic`、`news_items`、`market_ohlcv` / 日线等，以实际 `ensure_tables` 为准）。
- **增量**：股东等多用 `INSERT`/`REPLACE` 按主键；具体见 `FinancialReportCollector` 与 pipeline。
- **索引**：DuckDB 侧以查询模式为主；**未见统一归档/分层（冷数据）策略文档化**。
- **ClickHouse**：加密与部分行情管线使用（`data-engine`）；与 Dashboard 主路径可能不完全一致，需按部署确认。

### 2.5 依赖与密钥

- **TUSHARE_TOKEN**、**JWT_SECRET** 等：经 `gateway/app.py` 加载根目录 `.env`。
- **网络**：AkShare/东财、Tushare、Binance 均依赖外网；**无内置熔断/降级开关**（除代码内 try/except 返回空）。
- **监控**：`gateway/metrics.py` + 审计中间件写 `audit_log`（`app.py`）；**外部数据源可用性未单独探针化**。

### 2.6 数据域风险与改进建议

| 优先级 | 风险 | 建议 |
|--------|------|------|
| **高** | 生产 CORS 与鉴权宽松（见 §3） | 分环境配置；敏感写操作必鉴权 |
| **中** | 空数据与错误语义混淆 | API 统一 `ok` + `reason` / HTTP 503；前端区分「未配置库」与「真无 K 线」 |
| **中** | 股东多期覆盖不均 | 定期跑 `check_top10_shareholders_coverage.py` 进 CI 或监控大盘 |
| **低** | 双 DuckDB 路径 | 文档与 `.env.example` 明确默认库；Gateway 与 pipeline 对齐 `get_db_path` |

---

## 3. 前后端连接详细评估

### 3.1 API 设计

| 项 | 现状 | 证据 |
|----|------|------|
| 风格 | 以 **GET + 少量 POST** 为主的 JSON API，**非严格 REST 资源命名**（如 `/market/klines`、`/system/data-overview`） | `gateway/endpoints.py` |
| 前缀 | 统一 `/api` | `app.py`：`include_router(router, prefix="/api")` |
| 版本 | **无 `/v1`** | — |
| 响应体 | 混用「纯 JSON 对象」与「`{ ok: bool, error?: str }`」 | 如 `financial.py` 股东接口 vs FastAPI 默认 |

**建议**：新接口统一 `{ "ok": boolean, "data"?, "error"? }`；文档生成可用 FastAPI 自带 `/openapi.json`（需前端或 CI 拉取固化）。

### 3.2 数据传输与前端调用

| 项 | 现状 | 证据 |
|----|------|------|
| 基址 | 浏览器：`/api/...` 同源；服务端渲染可走 `NEXT_PUBLIC_API_TARGET` | `frontend/src/api/client.ts`；`frontend/next.config.js` `rewrites` |
| 方法 | `apiGet`：`fetch` + `!res.ok` 抛错 | `client.ts` L30–39 |
| 分页/排序 | **部分列表接口带 `limit` query**；非全局规范 | 如 `stocks?limit=`、`news?limit=` |
| 认证头 | **未在 `apiGet` 中默认附加 `Authorization`** | `client.ts`；若启用 `JWT_AUTH_REQUIRED`，前端需补 Bearer |

### 3.3 状态管理

| 层级 | 实现 |
|------|------|
| 全局 | `LangProvider` + `useLang()`（`frontend/src/context/LangContext.tsx`） |
| 服务端状态 | **无 React Query/SWR**；各页 `useState` + `useEffect` 拉取 |
| 后端 Session | **无传统 session**；可选 JWT 中间件 |

### 3.4 错误处理

| 层级 | 现状 |
|------|------|
| 前端 | `apiGet` 抛 `Error`，页面 `catch` 或 `.catch` 展示文案（如 AI 交易页提示启动 Gateway） |
| 后端 | 多 try/except 返回字典 `ok: False`；部分 `HTTPException` |
| 重试 | **无统一指数退避**；热点等依赖定时刷新 |

### 3.5 安全性

| 项 | 现状 | 风险 |
|----|------|------|
| CORS | `allow_origins=["*"]` | `gateway/app.py` L41–46：**任意源可带凭证浏览器请求** |
| JWT | `JWT_AUTH_REQUIRED` 非 1 时**全局放行** | `auth_middleware.py` |
| SQL | ORM/参数化为主（DuckDB `execute` 带参数） | 需防动态拼接 SQL 的新增代码 |
| 敏感数据 | API 返回业务数据；**未见响应级字段脱敏规范** | — |

### 3.6 性能

| 项 | 现状 |
|------|------|
| 缓存 | 前端 `cache: 'no-store'`；**服务端 HTTP 缓存头未系统设置** |
| 并发 | FastAPI/async；**未在文档中给出默认 worker 与连接池上限** |
| DB | DuckDB 只读连接多；高并发写需单写者模型 |
| 懒加载 | Next 按路由拆包；**无针对大列表的虚拟滚动统一方案** |

### 3.7 协作与文档

| 项 | 现状 |
|------|------|
| OpenAPI | FastAPI 自动生成；**未强制与前端类型同步**（手写 `client.ts` 接口） |
| Mock | **无统一 MSW**；部分页面依赖真实 API |
| 文档 | `docs/CODEBASE_DATA_AND_ANALYSIS_REPORT.md`、`OPENCLAW_DATA_PIPELINE.yaml` 等分散 |

---

## 4. 架构改进优先级

| 优先级 | 项 | 动作方向 |
|--------|----|----------|
| **高** | 生产安全 | 收窄 CORS；生产启用 JWT 或 API Key；前端 `apiGet` 带 Token；HTTPS 终止与 Cookie 策略 |
| **高** | 空数据可观测性 | Gateway 对关键读路径返回明确 `source`/`reason`；健康检查包含 DB 可达与表行数阈值 |
| **中** | API 契约 | 从 `openapi.json` 生成 TS 类型或 Zod；新端点统一 envelope |
| **中** | 数据质量 | 定时跑 `check_top10_shareholders_coverage.py` + `ensure_*` 结果上报 |
| **中** | 调度可移植性 | `start_schedulers.py` 使用 `Path(__file__)` 推导根目录，避免硬编码机器路径 |
| **低** | 前端数据层 | 引入 SWR/React Query，统一 loading/error/retry |
| **低** | 性能 | 对只读热点接口加短期缓存或 ETag；大表分页规范 |

### 4.1 DuckDB 与「数据挂接」（quant_system.duckdb）

- **同进程禁止混用 `read_only`**：DuckDB 对同一库文件若同时存在只读与读写连接会报错：`Can't open a connection to same database file with a different configuration...`。Gateway 内审计中间件使用 `data_pipeline.duckdb_manager.get_conn(read_only=False)`，因此 **财报接口（`lib.database`）、`core.data_service.db`、`data_engine.connector_astock_duckdb` 等凡访问同一文件的代码也须用 `read_only=False`（仅 SELECT 亦可）**。
- **路径对齐**：`lib.database.get_db_path()` 已与 `QUANT_SYSTEM_DUCKDB_PATH` / `NEWHIGH_MARKET_DUCKDB_PATH` 对齐，避免财报链路与 Pipeline 各连一个库导致「数据不全」假象。
- **全局修正范围**：已将 `read_only=True` 改为 `False` 的模块包括（但不限于）`core.analysis.financial_analyzer`、`data_pipeline.sentiment_7d`、`backtest_engine`、`risk_engine`、`execution_engine.signal_executor`、`strategy_engine.ai_fusion_strategy`、`openclaw_engine.population_manager`、`system_core` 编排器、`ai_optimizer` 及常用 `scripts/*`。**保留** `lib/tests/test_database.py` 中对只读连接的单元测试（独立临时库）。
- **一键重启**：`bash scripts/restart_gateway_frontend.sh`（杀 8000/3000 端口进程并后台拉起 uvicorn + `npm run dev`，日志在 `logs/gateway.out`、`logs/frontend.out`）。

---

## 5. 附录：关键路径索引

| 类别 | 路径 |
|------|------|
| Gateway 入口 | `gateway/src/gateway/app.py` |
| 路由聚合 | `gateway/src/gateway/endpoints.py` |
| 财报/股东 API | `gateway/src/gateway/endpoints_api/financial.py` |
| 系统数据概览 | `gateway/src/gateway/endpoints_system_data.py` |
| JWT / 中间件 | `gateway/src/gateway/auth/auth_middleware.py`、`jwt_auth.py` |
| 指标 | `gateway/src/gateway/metrics.py` |
| 前端 API | `frontend/src/api/client.ts` |
| Next 反代 | `frontend/next.config.js` |
| 全局语言状态 | `frontend/src/context/LangContext.tsx` |
| DB 路径 | `lib/database.py`（与 `QUANT_SYSTEM_DUCKDB_PATH` 对齐）、`data-pipeline/.../duckdb_manager.py` |
| 股东采集 | `scripts/run_shareholder_collect.py` |
| 股东覆盖检查 | `scripts/check_top10_shareholders_coverage.py` |
| 调度 | `scripts/start_schedulers.py` |
| 数据源连接器 | `data-engine/src/data_engine/connector_*.py` |
| Pipeline 采集 | `data-pipeline/src/data_pipeline/collectors/` |
| 数据架构说明 | `docs/CODEBASE_DATA_AND_ANALYSIS_REPORT.md` |

---

*本报告基于代码静态分析生成，实际负载与安全审计需结合部署环境与渗透测试补充。*
