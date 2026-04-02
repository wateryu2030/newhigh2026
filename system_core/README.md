# system_core — 统一系统运行核心

将数据管道、扫描器、AI 模型、策略引擎统一调度，并提供系统监控与状态落库。

## 目录结构

```
system_core/
├── __init__.py
├── system_runner.py      # 启动入口与主循环
├── data_orchestrator.py  # 数据调度
├── scan_orchestrator.py  # 市场扫描调度
├── ai_orchestrator.py    # AI 分析调度
├── strategy_orchestrator.py  # 策略调度
├── system_monitor.py     # 系统监控，写 system_status
└── README.md
```

## 运行方式

**从仓库根目录执行：**

```bash
# 主循环（默认每 60 秒一轮）
python -m system_core.system_runner

# 只跑一轮后退出
python -m system_core.system_runner --once

# 自定义间隔（秒）
python -m system_core.system_runner --interval 120

# 跳过某阶段
python -m system_core.system_runner --no-data --once
python -m system_core.system_runner --no-scan --no-ai --once

# 单轮中包含日 K 批量更新（慢）
python -m system_core.system_runner --once --daily-kline --daily-kline-limit 100
```

或直接运行脚本（需在 newhigh 根目录）：

```bash
python system_core/system_runner.py
python system_core/system_runner.py --once
```

## 主循环逻辑

```
while True:
    data_orchestrator.update()   # 股票池、实时、资金流、涨停、龙虎榜（可选日 K）
    scan_orchestrator.run()      # limit_up / fund_flow / volume / trend / sniper
    ai_orchestrator.run()        # emotion_cycle / hotmoney_detector / sector_rotation_ai
    strategy_orchestrator.run()  # ai_fusion_strategy → trade_signals
    system_monitor.record(...)   # 写入 system_status
    sleep(interval_seconds)
```

## 各编排器职责

| 模块 | 调用 | 输出 |
|------|------|------|
| data_orchestrator | update_stock_list, update_daily_kline, update_realtime_quotes, update_fundflow, update_limitup, update_longhubang | a_stock_* 表 |
| scan_orchestrator | run_limit_up_scanner, run_fund_flow_scanner, run_volume_spike_scanner, run_trend_scanner, run_sniper | market_signals, sniper_candidates |
| ai_orchestrator | run_emotion_cycle, run_hotmoney_detector, run_sector_rotation_ai | market_emotion, top_hotmoney_seats, main_themes, hotmoney_signals, sector_strength |
| strategy_orchestrator | run_ai_fusion（回退 aggregate_market_signals_to_trade_signals） | trade_signals |
| system_monitor | collect_status + write_status | system_status 表 |

## 系统状态表

**system_status**（在 market.duckdb 中）：

- data_status
- scanner_status
- ai_status
- strategy_status
- snapshot_time

API：`GET /api/system/status` 可查询最近若干条状态。

## Celery 异步任务（可选）

使用 Celery + Redis 可将 data/scan/ai/strategy 作为异步任务执行，并由 Beat 定时触发全周期。

**安装**：根目录 `pip install -r requirements.txt`（含 `celery`、`redis`）。需先启动 Redis（如 `redis-server`）。

**环境变量**（可选）：
- `CELERY_BROKER_URL`：默认 `redis://127.0.0.1:6379/0`
- `CELERY_RESULT_BACKEND`：默认 `redis://127.0.0.1:6379/0`

**启动 Worker**（在仓库根目录）：

```bash
celery -A system_core.celery_app worker -l info
```

**启动 Beat 定时调度**（另开终端，根目录）：

```bash
celery -A system_core.celery_app beat -l info
```

仅启动 worker 时可手动提交任务；同时启动 worker + beat 时，每 60 秒自动执行一次全周期（data → scan → ai → strategy）。

**任务名**：`run_data_task`、`run_scan_task`、`run_ai_task`、`run_strategy_task`、`run_full_cycle_task`、`run_strategy_backtest_task`（JSON：`symbol`、`start_date`、`end_date`、`strategy_id`、可选 `persist`）、`run_parallel_backtests_group_task`（可选并行：`CELERY_BACKTEST_USE_PARALLEL_GROUP`）、`dispatch_parallel_backtests_async_task`（仅派发 group，不等待结果）。

---

## 依赖

- data_pipeline（collectors + storage）
- market_scanner（含 hotmoney_sniper）
- ai_models
- strategy_engine
- core（可选）

安装：在仓库根目录 `pip install -r requirements.txt` 或安装各子包（-e ./data-pipeline 等）。

## 统一数据库（quant_system.duckdb）

全系统共用 **data/quant_system.duckdb**。环境变量 `QUANT_SYSTEM_DUCKDB_PATH` 可覆盖路径。若此前使用 market.duckdb / quant.duckdb，可临时设置 `QUANT_SYSTEM_DUCKDB_PATH` 指向其一，或新建 quant_system.duckdb 后运行 pipeline 与 `copy_astock_duckdb_to_newhigh.py` 重新写入。
