# 迭代速度与数据采集时效

## 本地迭代（缩短反馈环）

- `make dev-check`：跑 `scripts/restart_and_check.sh`，快速确认网关与健康检查。
- `make gateway-restart`：仅重启网关与前端（改 API 时常用）。
- `make pipeline-editable`：可编辑安装 `data-pipeline`，保证 `tushare` 等与 `pyproject.toml` 一致。
- 全市场日 K 回补（非每日调度）：`python scripts/backfill_a_stock_daily.py --source tushare_daily --all-market`（见脚本 `--help`）。

## 每日采集（Launchd / `start_schedulers`）

- 配置 `TUSHARE_TOKEN` 后，每日任务**默认仅用 Tushare** 拉近 `TUSHARE_DAILY_DAYS_BACK` 天（默认 7）的全市场日 K，**不再**默认跑 akshare 前 100 只，避免系统代理下东财请求拖死整轮调度。
- **深度历史、全市场缺口**：请**按需**跑 `scripts/backfill_a_stock_daily.py`（或 Gateway `/api/data/incremental`），**不要**把 `TUSHARE_DAILY_DAYS_BACK` 拉到很大来「代替回补」——会拖长每日窗口、多耗积分，且与增量回补脚本的批策略重复。
- 需要东财补边时：在 `.env` 设置 `DAILY_AKSHARE_KLINE_LIMIT=50`（或更大）。
- 股东与数据质量：`start_schedulers` 内已含晚间巡检与质量脚本入口；告警可配 `DATA_QUALITY_WEBHOOK_URL`（见 `.env.example`）。

## 建议节奏

| 任务 | 频率 | 说明 |
|------|------|------|
| 日 K 增量 | 每日 18:00 | 调度器 + Tushare |
| 深度回补 / 缺口 | 每周或按需 | `backfill_a_stock_daily.py` |
| 数据质量报告 | 每日（与调度同机） | `run_data_quality_checks.py` |
