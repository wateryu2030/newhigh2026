# 十大股东多期历史采集

## 改动摘要

1. **采集逻辑**：`ak.stock_main_stock_holder` 单次返回该股全部历史期（约 100+ 期），按 `截至日期` 分组逐期写入。
2. **成功率优化**：失败时自动重试 3 次（1.5s / 2.5s / 4.5s 退避）；间隔 0.6s + 0~0.3s 随机抖动，降低 No tables found。

## 全量回补（一次性）

```bash
# 前台执行（约 35 分钟）
python scripts/start_schedulers.py backfill-shareholder

# 后台执行
nohup python scripts/start_schedulers.py backfill-shareholder > logs/shareholder_backfill.log 2>&1 &
```

## 手动执行

```bash
# 全量采集（约 5000 股，delay 0.4s 时约 35 分钟）
python scripts/run_shareholder_collect.py --shareholders-only

# 测试 10 只
python scripts/run_shareholder_collect.py --limit 10 --shareholders-only

# 财报+股东一起采（默认）
python scripts/run_shareholder_collect.py --limit 50
```

## 自动定时采集（已写入调度心跳）

`scripts/start_schedulers.py` 每日 **02:00** 自动执行十大股东采集，与 18:00 每日任务同属心跳逻辑。

```bash
# 启动调度（含 02:00 股东采集）
python scripts/start_schedulers.py monitor
```

如需单独用 LaunchAgent 定时（不依赖调度进程）：

```bash
cp config/com.newhigh.shareholder-collect.plist ~/Library/LaunchAgents/
launchctl load ~/Library/LaunchAgents/com.newhigh.shareholder-collect.plist
```

## 使用 financial_report_job（可选）

```bash
cd /Users/apple/Ahope/newhigh
PYTHONPATH=".:data/src:lib" python -m data.scheduler.financial_report_job --mode full --limit 100 --delay 0.4
```

## 依赖

- akshare：`pip install akshare`
- DuckDB：项目默认使用 `data/quant_system.duckdb`
