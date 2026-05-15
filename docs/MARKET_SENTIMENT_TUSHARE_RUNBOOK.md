# 全市场 7 维情绪与日 K 增量 — 运维说明

## 1. 同一套 DuckDB

- 路径由 **`QUANT_SYSTEM_DUCKDB_PATH`**（或兼容名，见 `data_pipeline.storage.duckdb_manager.get_db_path`）决定，默认 **`data/quant_system.duckdb`**（相对仓库根）。
- **Gateway、Tushare 增量、`run_market_sentiment_7d.py`、实时采集** 必须指向**同一文件**，否则会出现「库里有数据但 API 读不到」或口径不一致。
- **「DuckDB 文件正被其他进程占用」**：同一文件不能多进程同时写。处理：**只保留一个**写库进程；常见做法是跑增量/Tushare 前 **停掉多余的 uvicorn Gateway**，或错开任务时间。

## 2. 保持 `a_stock_daily` 最新

在仓库根执行（需 **`TUSHARE_TOKEN`**）：

```bash
python scripts/run_tushare_incremental.py
```

- 内部为 `run_incremental("tushare_daily")`，按各股票已有 **`MAX(date)`** 续拉到最近交易日，避免日 K 滞后导致情绪「日 K 快路径」失真。
- 全量：`python scripts/run_tushare_incremental.py --full`
- 与坏本机代理冲突时，Tushare 脚本默认 **strip 代理**（见 **`TUSHARE_STRIP_PROXY`**，`.env.example`）。

## 3. 盘中：先写东财快照再算情绪

与 `a_stock_realtime` 对齐时，在算分前先拉一次东财快照：

```bash
UPDATE_REALTIME_FIRST=1 python scripts/run_market_sentiment_7d.py
```

- `UPDATE_REALTIME_FIRST=1` 会调用 `update_realtime_quotes()`，再执行 `get_market_sentiment_7d()`。
- 逻辑顺序见 `data_pipeline/sentiment_7d.py`（库内实时 → 可选日 K → 可选 AkShare 东财全市场等）。

## 4. 环境变量速查（`all_sources_exhausted` / 东财失败）

| 变量 | 建议 |
|------|------|
| **`SENTIMENT_7D_STRIP_PROXY`** | 默认 **`1`**：拉东财前去掉 `HTTP(S)_PROXY`，避免本机错误代理导致 AkShare 失败。 |
| **`SENTIMENT_7D_AKSHARE_ENABLE`** | 默认 **`0`**（避免 `spot_em` 全市场过慢）。需盘中强依赖东财全市场现货时设 **`1`**，可配合 **`SENTIMENT_7D_DAILY_BEFORE_SPOT=0`** 优先现货。 |
| **`SENTIMENT_7D_DAILY_BEFORE_SPOT`** | 默认 **`1`**：先走日 K 快路径再尝试现货，减轻接口超时。 |
| **`SENTIMENT_7D_USE_SINA_SPOT`** | 境外仅东财不通时可设 **`1`** 走新浪现货（更慢、口径不同，非默认）。 |
| **`UPDATE_REALTIME_FIRST`** | 仅 **`run_market_sentiment_7d.py`**：先写实时表再算分（见上节）。 |

完整列表见 **`.env.example`** 中 `SENTIMENT_7D_*` 注释。

## 5. 推荐自检顺序

1. 确认 **`.env`** 中 **`QUANT_SYSTEM_DUCKDB_PATH`** 与运行 Gateway 的进程一致。  
2. 无锁时跑 **`python scripts/run_tushare_incremental.py`**，保证 **`a_stock_daily`** 足够新。  
3. 盘中需要快照时：**`UPDATE_REALTIME_FIRST=1 python scripts/run_market_sentiment_7d.py`**。  
4. 仍报 **`all_sources_exhausted`**：看 JSON 里 **`detail`** 中的「尝试记录」；按上表调整代理/东财/新浪开关。
