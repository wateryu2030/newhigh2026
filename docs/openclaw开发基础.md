# OpenClaw 开发基础

> 红山量化平台项目现状总览：项目构成、运行逻辑、下步开发计划、数据库与数据情况。供 OpenClaw/Cursor 及新成员快速上手。

---

## 一、项目构成

### 1.1 项目定位

**一句话**：A 股量化 + 情绪/游资/主线 AI 分析 + 统一调度 + 回测/策略市场/资金曲线/决策解释的前后端一体平台；目标演进为「AI 生成策略 → 回测评估 → 自动交易，人只监督」的 AI 基金经理系统。

**愿景**：AI 基金经理（自动策略生成、评估、优化）；全链路可运行、可监控；Dashboard、策略市场、资金曲线、AI 决策解释；远期多 Agent、移动端核心视图。

### 1.2 目录与模块

| 目录/模块 | 说明 |
|-----------|------|
| **core/** | 配置中心（config、pydantic-settings）、日志（logging_config JSON）、统一 DB 路径 |
| **data-pipeline/** | 数据采集（stock_list、daily_kline、realtime、fund_flow、limit_up、longhubang）、DuckDB 存储（duckdb_manager）、数据源抽象（ashare_daily_kline、ashare_longhubang、tushare_daily 等）与增量 run_incremental |
| **data-engine/** | 与 data-pipeline 共用 quant_system.duckdb；astock_duckdb 连接器、行情获取 |
| **feature-engine/** | 特征计算（与日 K/策略/回测对接） |
| **market-scanner/** | 涨停/资金流/量能/趋势/游资狙击 → market_signals、sniper_candidates |
| **ai-models/** | emotion_cycle、hotmoney_detector、sector_rotation_ai → market_emotion、top_hotmoney_seats、main_themes |
| **strategy-engine/** | ai_fusion_strategy、trade_signal_aggregator → trade_signals |
| **backtest-engine/** | 从 quant_system.duckdb 读日 K 与信号；多标的、滑点/手续费；资金曲线、Sharpe/回撤；回测结果可写 strategy_market |
| **portfolio-engine/** | 组合与资金配置 |
| **risk-engine/** | 可配置规则（risk_rules 表）、evaluate、与 execution step_simulated(risk_check) 联动 |
| **execution-engine/** | 模拟盘（sim_positions/sim_orders/sim_account_snapshots）、brokers（SimulatedBroker/LiveBroker）、EXECUTION_MODE |
| **openclaw_engine/** | 策略基因、遗传操作、多目标适应度、RL 占位；evolution_orchestrator、Celery run_evolution_task |
| **system_core/** | 统一调度：data_orchestrator → scan → ai → strategy → system_monitor |
| **scheduler/** | 定时任务（Celery Beat 等） |
| **gateway/** | FastAPI：/api/market、/api/strategies、/api/backtest、/api/simulated、/api/risk、/api/evolution、/api/execution/mode、/api/data/*、/api/skill/ashare/*、/health 等 |
| **frontend/** | Next.js App Router、Tailwind、Zustand、Recharts；Dashboard/行情/股票/策略/AI 交易/组合/风控/交易/报告/设置；移动端底部导航、PWA |
| **skills/** | OpenClaw A 股 Skill（Tushare：行情、基本面、技术指标）；load_skill、Gateway /api/skill/ashare/* |
| **infra/** | Docker、docker-compose、monitoring（Prometheus、Grafana 示例） |
| **scripts/** | ensure_market_data、run_full_cycle、run_automated、openclaw_evolution_cycle、check_frontend_backend、openclaw_check_design、run_tests、schedule（launchd/cron）等 |

### 1.3 技术栈

- **后端**：Python 3.x、FastAPI、DuckDB、Celery+Redis、pydantic-settings、akshare、tushare（Skill 与 tushare_daily 数据源）。
- **前端**：Next.js、React、TypeScript、Tailwind、Zustand、Recharts；`NEXT_PUBLIC_API_TARGET` 默认 `http://127.0.0.1:8000`。
- **运维**：uvicorn（Gateway :8000）、npm run dev（前端 :3000）、Docker/docker-compose、Prometheus、JSON 日志、mkdocs。
- **LLM（百练）**：策略生成 / AI 开发代理可使用阿里云百炼；`.env` 中 `BAILIAN_API_KEY` 或 `DASHSCOPE_API_KEY`（dashscope SDK）；见 `OPENCLAW_AUTONOMOUS_DEV.yaml` 的 `llm` 段。

---

## 二、运行逻辑

### 2.1 数据流

```
外部（AkShare / Tushare 等）
    ↓
data-pipeline collectors / data_sources.run_incremental
    ↓
quant_system.duckdb（a_stock_* / daily_bars / strategy_market 等）
    ↓
market-scanner + ai-models + strategy-engine
    ↓
backtest-engine / execution-engine / openclaw_engine 读写同一库
    ↓
Gateway 读库提供 /api/*
    ↓
前端（Next.js）消费
```

### 2.2 调度逻辑

- **system_core**：`python -m system_core.system_runner`（或 `--once`）执行一轮：data_orchestrator → scan_orchestrator → ai_orchestrator → strategy_orchestrator → system_monitor，结果写 `system_status`。
- **定时**：launchd（`scripts/schedule/install_scheduled_run.sh`，周一至五 18:30）或 cron 执行 `run_full_cycle.py` / `run_automated.py`；方式二可含 Tushare 增量 + 全周期。
- **数据补全**：`scripts/ensure_market_data.py` 填充股票池、日 K、涨停、龙虎榜等；`POST /api/data/ensure-stocks` 用 akshare 拉取股票池写入 `a_stock_basic`；`POST /api/data/incremental` 按数据源做增量。

### 2.3 启动与验证

| 步骤 | 命令 | 说明 |
|------|------|------|
| 1. 环境 | `source .venv/bin/activate`，`pip install -r requirements.txt` | 项目根目录 |
| 2. Gateway | `uvicorn gateway.app:app --host 127.0.0.1 --port 8000` | API 与 /health、/docs |
| 3. 前端 | `cd frontend && npm run dev` | http://localhost:3000 |
| 4. 一轮数据与信号 | `python -m system_core.system_runner --once` 或 `python scripts/ensure_market_data.py` + `python scripts/run_full_cycle.py` | 可选，无数据时多数 API 返回空或默认值 |
| 5. 前后端联调检查 | `bash scripts/check_frontend_backend.sh` | 需 Gateway 已启动；验证 37 项 API 与结构 |
| 6. OpenClaw 设计检查 | `bash scripts/openclaw_check_design.sh` 或 `bash scripts/restart_and_check.sh` | 编译、测试、页面、API、Live 健康 |
| 7. **打开本机 OpenClaw** | 先 `cd` 到项目根，再 `bash scripts/open_openclaw.sh` | 加载 .env（含百炼 API Key）并检查/启动 Gateway；详见下方 |

**打开本机 OpenClaw**：**必须先进入项目根目录**（例如 `cd /Users/apple/Ahope/newhigh`），再执行 `bash scripts/open_openclaw.sh`。脚本会加载该目录下的 `.env`（含 `BAILIAN_API_KEY` / `DASHSCOPE_API_KEY`），若 Gateway 未运行则尝试启动。本机 Cursor 使用 OpenClaw 时，百炼 API Key 从 `.env` 读取；项目内已配置 `.cursor/rules/openclaw-bailian.mdc`，约定所有 LLM 调用通过环境变量读取 key，勿硬编码。

### 2.4 前后端配合

- 前端 `frontend/src/api/client.ts` 调用 Gateway `/api/*`，默认 base `http://127.0.0.1:8000`。
- 关键接口：`/dashboard`、`/data/status`、`/stocks`、`/portfolio/weights`、`/execution/equity_curve`、`/execution/mode`、`/simulated/orders`、`/simulated/positions`、`/market/*`、`/strategies/market`、`/backtest/result` 等；股票页空数据时会调用 `POST /api/data/ensure-stocks` 尝试拉取股票池。
- 详见 `scripts/check_frontend_backend.sh` 与 `docs/PROJECT_HANDOFF_FOR_AI.md`。

---

## 三、下步开发计划

### 3.1 待办（backlog 未完成）

- **数据**：接入更多数据源（与 A 股并列）；数据缓存与时效性策略。
- **回测**：多策略回测（多策略并行/串行、资金分配）。
- **策略与 AI**：LSTM/价格预测模型；RL Trader（状态/动作/奖励与 backtest、execution 对接）；自进化策略池与 OpenClaw 循环联动。
- **策略市场**：AI 生成策略入库流程（生成 → 回测 → 通过则写入策略池）。
- **UI**：移动端核心视图（资金曲线、策略排名、AI 决策）。
- **执行与风控**：实盘/模拟盘开关与配置；风控硬约束与 execution-engine 联动；交易记录与对账。

### 3.2 改进计划（OPENCLAW_IMPROVEMENT_PLAN 阶段 0–3 已实施部分）

阶段 0–3 中多数任务已勾选完成（Celery、配置中心、模拟盘、数据源抽象、健康检查、回测增强、策略市场、风控、OpenClaw V1、进化调度、认证审计、前端移动适配、容器化、监控日志、OpenClaw 增强、实盘接口封装、测试与文档等）。后续可在此基础上：

- 深化多策略回测与资金分配；
- 打通 AI 生成 → 回测 → 自动入库策略市场；
- 实现 RL Trader 或 LSTM 预测与回测/执行对接；
- 完善实盘对接、对账与审计；
- 移动端核心视图与无数据引导体验。

详见 `docs/OPENCLAW_IMPROVEMENT_PLAN.md`、`tasks/backlog.md`、`docs/IMPROVEMENT_PLAN_EXECUTABLE.md`。

---

## 四、数据库与数据情况

### 4.1 统一存储

- **路径**：`data/quant_system.duckdb`（默认）；环境变量 `QUANT_SYSTEM_DUCKDB_PATH` 可覆盖。
- **管理入口**：`data_pipeline.storage.duckdb_manager`（get_db_path、get_conn、ensure_tables）；core 与各引擎对齐同一路径。
- **使用方**：data-pipeline、market-scanner、ai-models、strategy-engine、backtest-engine、execution-engine、risk-engine、openclaw_engine、gateway、system_core 等均读写该库。

### 4.2 表结构概览（ensure_tables）

**行情与基础**

| 表名 | 用途 |
|------|------|
| a_stock_basic | 股票池（code, name；akshare 或 POST /api/data/ensure-stocks） |
| a_stock_daily | 日 K（code, date, open/high/low/close/volume/amount） |
| a_stock_realtime | 实时行情 |
| a_stock_fundflow | 资金流 |
| a_stock_limitup | 涨停池 |
| a_stock_longhubang | 龙虎榜 |

**通用结构（与 astock 兼容）**

| 表名 | 用途 |
|------|------|
| daily_bars | 日 K（order_book_id, trade_date, adjust_type, open/high/low/close/volume…） |
| stocks | 标的（order_book_id, symbol, name, market…） |
| news_items | 新闻（symbol, title, content, sentiment_score…） |

**扫描与 AI**

| 表名 | 用途 |
|------|------|
| market_signals | 扫描信号 |
| market_emotion / market_emotion_state | 情绪状态与每日指标 |
| top_hotmoney_seats / hotmoney_signals | 游资席位与信号 |
| main_themes / sector_strength | 主线题材与板块强度 |
| trade_signals | 交易信号（code, signal, strategy_id, signal_score…） |
| sniper_candidates | 游资狙击候选 |

**策略与系统**

| 表名 | 用途 |
|------|------|
| strategy_market | 策略市场（strategy_id, name, return_pct, sharpe_ratio, max_drawdown, status） |
| system_status | 系统运行状态 |
| risk_rules | 风控规则 |
| audit_log | API 审计日志 |

**模拟盘**

| 表名 | 用途 |
|------|------|
| sim_positions | 模拟持仓 |
| sim_orders | 模拟订单 |
| sim_account_snapshots | 资金快照 |

### 4.3 数据源与增量

- **数据源**：`data_pipeline.data_sources` 注册如 ashare_daily_kline、ashare_longhubang、tushare_daily 等；Gateway `GET /api/data/sources` 列出，`POST /api/data/incremental` 执行指定 source_id 增量。
- **采集**：管道主要依赖 akshare；Tushare 需 `.env` 中 `TUSHARE_TOKEN`。限流或失败时管道可能静默返回，需监控与重试策略。
- **数据量**：取决于是否执行 `ensure_market_data.py`、`run_full_cycle.py`、`run_automated.py` 或 `copy_astock_duckdb_to_newhigh.py`。未跑前多为空或仅表结构；可通过 `scripts/.openclaw_state.json` 的 data_health 或各表 COUNT 查看条数。

### 4.4 数据侧已知缺口

- 无数据时多数 API 返回空或默认值；前端需无数据引导（部分页已做超时、空态、ensure-stocks）。
- a_stock_* 与 daily_bars/stocks 两套结构并存，复制脚本与 API 映射需统一约定（如 symbol ↔ order_book_id）。
- 数据缓存、时效性、备份与迁移策略未成文；增量仅部分数据源接入。
- features_daily 等扩展表由其他脚本创建，未在 ensure_tables 中统一列出。

---

## 五、参考文档与入口

| 文档 | 说明 |
|------|------|
| docs/PROJECT_HANDOFF_FOR_AI.md | 项目交接与建议维度 |
| PROJECT_STATUS.md | 详细状态与架构图 |
| docs/PROJECT_STATUS_AND_DATA_SUMMARY.md | 项目与数据现状总结 |
| docs/OPENCLAW_IMPROVEMENT_PLAN.md | 阶段 0–3 任务分解与验收 |
| docs/OPENCLAW_SKILLS.md | A 股 Skill（Tushare）集成与使用 |
| OPENCLAW_AUTONOMOUS_DEV.yaml | OpenClaw 代理与 skills 配置 |
| tasks/backlog.md、tasks/current_task.md | 待办与当前任务 |
| README.md | 运行与构建说明 |

**本机 OpenClaw 正常运转**：修改配置后需**重启 Gateway**并**新开 Chat 会话**才能用上百炼；要让 agent 读 newhigh 的 .md 请用绝对路径 `/Users/apple/Ahope/newhigh`。详见 [OPENCLAW_运行说明.md](OPENCLAW_运行说明.md)。

**常用命令**：  
- Gateway：`uvicorn gateway.app:app --host 127.0.0.1 --port 8000`  
- 前端：`cd frontend && npm run dev`  
- 前后端检查：`bash scripts/check_frontend_backend.sh`  
- OpenClaw 设计检查：`bash scripts/openclaw_check_design.sh`  
- **Cursor 进化循环**：`bash scripts/cursor_evolution_cycle.sh`（触发进化 → 轮询 → 代码检查 → 前后端验证）；详见 `docs/CURSOR_OPENCLAW_TASKS.md`。

**系统监控页**（`/system-monitor`）：展示 data/scanner/ai/strategy 状态、OpenClaw 进化任务列表、Skill 调用统计；可点击「触发策略进化」与「刷新」。
