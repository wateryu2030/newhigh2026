# 数据不全与 OpenClaw 自进化改进

## 一、数据不全时的现象与改进清单

| 现象 | 原因 | 改进动作 |
|------|------|----------|
| 新闻页为空或单薄 | quant_system.duckdb 无 news_items 或未复制 astock | 1) 运行 `copy_astock_duckdb_to_newhigh.py`（目标默认 quant_system.duckdb）；2) 网关已做 akshare 东方财富新闻 fallback |
| Dashboard 无「情绪/狙击候选」 | quant_system.duckdb 无数据或未跑终端单轮 | 运行 `python -m system_core.system_runner --once` 或 `ensure_market_data.py` + `run_full_cycle.py` |
| AI 交易页全部「暂无数据」 | quant_system.duckdb 表空或 Gateway 未启动 | 1) 运行 `python -m system_core.system_runner --once` 或 `ensure_market_data.py`；2) 启动 Gateway 8000 |
| 数据状态显示 0 标的/0 日线 | quant_system.duckdb 未就绪 | 运行 `copy_astock_duckdb_to_newhigh.py`（目标 quant_system.duckdb）或 `ensure_ashare_data_completeness.py` |

**推荐顺序（首次或数据不全时）：**

1. **统一运行核心（推荐）**：`python -m system_core.system_runner`（循环）或 `--once` — 数据 → 扫描 → AI → 策略 → 写 system_status
2. 若需日 K/新闻：`python scripts/copy_astock_duckdb_to_newhigh.py`（默认写入 `data/quant_system.duckdb`）或 `ensure_ashare_data_completeness.py`
3. 启动 Gateway：`uvicorn gateway.app:app --reload --port 8000`
4. 前端：`cd frontend && npm run dev`；**系统监控** 页可查看 data_pipeline / scanner / ai_models / strategy_engine 状态与 last_update

---

## 二、新闻内容增强

- **后端**：`GET /api/news` 优先返回 DuckDB `news_items`；**当无数据时自动从 akshare 东方财富拉取个股新闻**（需安装 akshare），并返回 `source: "akshare"`。
- **前端**：新闻页展示 keyword、tag，正文预览由 2 行改为 4 行；**无新闻时展示「数据不全」说明与「前往数据页」引导**。

---

## 三、OpenClaw 自进化与数据健康

**每轮进化会执行：**

1. **ensure_data_completeness** — 补全 quant.duckdb（A 股/北交所日线，akshare）
2. **ensure_market_data** — 填充 market.duckdb（股票池 + 涨停/龙虎榜/资金流，`--skip-kline` 快速）
3. **data_health_check** — 统计关键表条数（a_stock_basic、a_stock_daily、a_stock_limitup、market_emotion、sniper_candidates、trade_signals），写入 `scripts/.openclaw_state.json` 的 `data_health` 字段

**状态文件**：`scripts/.openclaw_state.json`

- `data_health`：各表条数，便于下一轮或 Cursor 判断哪些表需优先补全
- `market_data`：本次 ensure_market_data 执行结果
- `data_completeness`：本次 ensure_ashare_data_completeness 执行结果

**用法：**

```bash
python scripts/openclaw_evolution_cycle.py
python scripts/openclaw_evolution_cycle.py --no-ensure-data   # 跳过数据补全
python scripts/openclaw_evolution_cycle.py --data-loop        # 再跑 data_loop
```

自进化后可根据 `data_health` 决定是否单独再跑 `ensure_market_data.py`（带日 K）或 `run_full_cycle.py`，以丰富展示内容。

---

## 四、定期执行（锁屏/后台也能跑）

使用 **macOS launchd** 可把「数据+终端单轮」或「仅终端单轮」设成定时任务，**锁屏状态下也会按计划执行**（只要当前用户已登录）。

**一键安装定时任务（每周一至五 18:30）：**

```bash
# 在 newhigh 仓库根目录执行
bash scripts/schedule/install_scheduled_run.sh
```

- 默认执行：`run_full_cycle.py --skip-data`（只跑扫描 + AI + 信号，不拉数据）
- 日志：`logs/full_cycle.log`、`logs/launchd_stdout.log`、`logs/launchd_stderr.log`
- 卸载：`bash scripts/schedule/uninstall_scheduled_run.sh`

修改时间、改为「每天顺带拉数据」、休眠说明等见 **scripts/schedule/README.md**。
