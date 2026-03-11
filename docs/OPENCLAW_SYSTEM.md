# OpenClaw 系统规范 — 长期自主运行与进化

本系统不是「量化系统」，而是 **AI Hedge Fund Operating System**：自己发现 Alpha、自己交易、自己升级。

---

## 一、控制文件清单

| 文件 | 作用 |
|------|------|
| **OPENCLAW_MASTER_SYSTEM.yaml** | 系统总控：四循环、模块列表、自主开发开关 |
| **OPENCLAW_DATA_PIPELINE.yaml** | 数据自动生成：行情源、存储、更新频率、任务→模块映射 |
| **OPENCLAW_ALPHA_FACTORY.yaml** | 策略进化：生成方法、种群、筛选、进化参数、上线数量 |
| **OPENCLAW_META_FUND.yaml** | AI 基金经理：策略选择、资金配置、监控、止损、换仓 |
| **OPENCLAW_AI_DEV_AGENT.yaml** | AI 开发代理：能力、开发周期、约束、提交策略 |
| **FRONTEND_DATA_BINDING.yaml** | 前端数据绑定：页面 ↔ API 映射、REST/WebSocket 规范 |

---

## 二、四个核心循环

### 数据循环 (data_loop)

```
行情 (Binance / Yahoo) → 指标 (feature-engine) → 存储 (DB) → API → Frontend
```

- 步骤: `collect_market_data` → `update_features` → `store_database`
- 调度: scheduler 或 cron 按 OPENCLAW_DATA_PIPELINE 频率执行

### 策略循环 (strategy_loop)

```
生成策略 (alpha-factory) → 回测 (backtest-engine) → 评分 (alpha-scoring) → 进化 (strategy-evolution)
```

- 步骤: `generate_strategies` → `run_backtests` → `score_alpha` → `evolve_strategies`
- 调度: `scheduler.run_evolution_pipeline()`

### 交易循环 (trading_loop)

```
选择策略 (meta-fund-manager) → 资金配置 (portfolio-engine) → 执行 (execution-engine) → 绩效反馈
```

- 步骤: `select_strategies` → `allocate_capital` → `execute_trades` → `update_performance`
- 调度: 与 strategy_loop 衔接，部署后的策略进入交易循环

### AI 开发循环 (dev_loop)

```
分析系统 → 提出改进 → 生成代码 → 跑测试 → 部署/提交
```

- 步骤: `analyze_system` → `propose_improvements` → `generate_code` → `run_tests` → `deploy_updates`
- 执行: Cursor/OpenClaw 读取 OPENCLAW_AI_DEV_AGENT.yaml 与各 OPENCLAW_*.yaml 后自主执行

---

## 三、前后端连接标准

### REST API（已实现）

```
GET /api/dashboard      # 总资产、收益、Sharpe、回撤、曲线、策略排行、AI 统计
GET /api/market/klines # K 线
GET /api/strategies    # 策略列表
GET /api/portfolio/weights
GET /api/risk/status
GET /api/positions
GET /api/trades
GET /api/evolution
GET /api/alpha-lab
```

### WebSocket（预留）

```
/ws/market   # 行情推送
/ws/trades   # 成交推送
/ws/portfolio # 仓位/净值推送
```

### 数据流

```
Database (ClickHouse / Postgres)
    ↓
Gateway (FastAPI)
    ↓
Frontend (Next.js, 按 FRONTEND_DATA_BINDING.yaml 绑定)
```

---

## 四、让 Cursor 开始自动开发

将以下指令交给 Cursor（并确保已打开本仓库）：

```
Read all OPENCLAW configuration files.

Initialize autonomous development mode.

Implement missing modules.

Connect database, backend APIs, and frontend data bindings.

Ensure the system generates real data automatically.

Start autonomous strategy evolution loop.

Enable AI development agent for continuous improvement.
```

---

## 五、系统启动后自动运行形态

- **数据循环**: 定时拉行情、算指标、落库；Gateway 从库/缓存读数据供前端。
- **策略循环**: 定时或触发执行 evolution pipeline：生成 → 回测 → 评分 → 进化 → 部署。
- **交易循环**: 对已部署策略做资金分配与执行，绩效回写。
- **AI 开发循环**: 由 Cursor/OpenClaw 按配置与触发指令，分析代码、提出改进、生成代码、跑测、提交。

最终形态：**AI Alpha Factory** — 每天生成策略、筛选、进化、交易、并持续优化系统自身。

---

## 六、调度与四循环对应

| 循环 | 调度入口 | 步骤映射 |
|------|----------|----------|
| data_loop | `scheduler.run_pipeline(from_step="data_update", to_step="feature_generation")` 或 cron | data_update≈collect_market_data+store, feature_generation=update_features |
| strategy_loop | `scheduler.run_evolution_pipeline()` | generate_strategies → backtest_strategies → score_alpha → evolve_population → deploy_top_strategies |
| trading_loop | 在 deploy_top_strategies 之后由 meta-fund-manager 执行 | select_strategies, allocate_capital, execute_trades, update_performance |
| dev_loop | Cursor/OpenClaw 按 OPENCLAW_AI_DEV_AGENT.yaml 执行 | 分析 → 改进 → 写码 → 测试 → 提交 |

**启动数据+策略循环（一次）：**

```bash
source .venv/bin/activate
python -c "
from scheduler import connect_pipeline
s = connect_pipeline()
s.run_pipeline('data_update','feature_generation')  # 数据循环
s.run_evolution_pipeline()                          # 策略循环
"
```

**启动完整服务：**

```bash
# 1) Gateway
uvicorn gateway.app:app --host 0.0.0.0 --port 8000

# 2) Frontend
cd frontend && npm run dev

# 3) 定时任务（可选）用 cron 或 APScheduler 调用上述 Python 片段
```

---

## 七、自我进化单轮执行（OpenClaw）

按 **OPENCLAW_AUTONOMOUS_DEV.yaml** 与 **OPENCLAW_MASTER_SYSTEM.yaml** 执行一轮「dev_loop + strategy_loop」：

```bash
source .venv/bin/activate
python scripts/openclaw_evolution_cycle.py
```

- **流程**：读取控制文件摘要 → 跑全量测试（必须通过）→ 执行策略循环（generate_strategies → backtest → score_alpha → evolve → deploy）→ 将结果写入 `scripts/.openclaw_state.json`。
- **选项**：`--skip-tests` 跳过测试（不推荐）；`--data-loop` 在策略循环后再跑一次 data_update → feature_generation。
- **续跑**：可由 cron 或 Cursor 定期执行上述命令；下一轮或 AI 开发代理可读取 `.openclaw_state.json` 了解上次运行结果。

**数据完整性（缺数据自动拉取）**：每轮进化前会执行 `ensure_ashare_data_completeness.py`，从 **akshare/东方财富/北交所** 等平台检测 DuckDB 缺失区间并自动拉取写入，保证分析数据完整。可加 `--no-ensure-data` 跳过。详见 `OPENCLAW_DATA_PIPELINE.yaml` 与 `scripts/ensure_ashare_data_completeness.py`。
