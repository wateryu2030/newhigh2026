# 前后端 API 对齐说明

前端统一通过 `frontend/src/api/client.ts` 的 `api.*` 访问 Gateway（默认前缀 `/api`）。本文档列出**数据相关**高频接口与响应约定，避免「页面有数、接口换形状」类问题。

## 信封响应（unwrap）

| 方法 | 路径 | 说明 |
|------|------|------|
| `api.market()` | `GET /market/klines` | 使用 `unwrapEnvelope: true`，成功体在 `data` 字段 |
| `api.dataQuality()` | `GET /data/quality` | 使用 `unwrapEnvelope: true`，取最新一条巡检的 `data` |

其余多数 `apiGet` 为**直接 JSON**，与后端返回结构一致。

## 数据口径：`GET /data/status` vs `GET /system/data-overview`

同一 DuckDB 文件（如 `quant_system.duckdb`）可能同时存在：

- **管道表**：`a_stock_basic`、`a_stock_daily` 等 — `system/data-overview` 与各 pipeline 写入逻辑使用。
- **Astock 命名表**：`stocks`、`daily_bars` — `data_engine.get_duckdb_data_status()` 使用。

二者**行数/区间不必一致**。后端 `GET /data/status` 已合并两套统计，并返回：

- 顶层 `stocks` / `daily_bars` / `date_*`：**主展示**（优先与概览一致的 pipeline 口径，若有日线数据）。
- `source`：`duckdb_pipeline` | `duckdb_astock`。
- `breakdown.astock_schema` / `breakdown.pipeline_schema`：并列对照。

前端 **`/data` 页**（`app/data/page.tsx`）与 Dashboard 应优先信任上述说明，避免与「系统数据概览」卡片简单逐项相等校验。

## `api.*` → Gateway 路径速查（节选）

| `api` 方法 | HTTP | 备注 |
|------------|------|------|
| `dataStatus` | `GET /data/status` | 含 `breakdown` |
| `dataDailyCoverage` | `GET /data/daily-coverage?limit_codes=` | 日线覆盖 TopN，解释「池大线少」 |
| `dataQuality` | `GET /data/quality` | 信封 unwrap |
| `marketLimitup` | `GET /market/limitup` | 涨停池（按 code 去重 + 名称/现价/涨跌/`updated_at`） |
| `sniperCandidates` | `GET /market/sniper-candidates` | 狙击候选（按 code 去重 + 同上） |
| `marketLonghubangRows` | `GET /market/longhubang` | 龙虎榜（仅 `lhb_date` 非空；按 code+日期去重） |
| `marketFundflow` | `GET /market/fundflow` | 资金流（按 code 最新一条 + 同上） |
| `marketHotmoney` | `GET /market/hotmoney` | 游资席位（`updated_at`，无微秒 timestamp） |
| `marketMainThemes` | `GET /market/main-themes` | 主线题材（`updated_at`） |
| `systemDataOverview` | `GET /system/data-overview` | `counts` / `summary` |
| `marketSummary` | `GET /market/summary` | core 行情摘要，可能与上表不同源 |
| `stocks` | `GET /stocks` | 列表 |
| `ashareStocks` | `GET /market/ashare/stocks` | A 股列表通道 |
| `market` | `GET /market/klines` | 信封 unwrap |

完整列表以 `client.ts` 中 `apiGet` 调用为准。

## 维护建议

1. 新增 Gateway 路由时：同步 `client.ts` 类型与页面调用；若使用 `{ ok, data }` 信封，务必在 `apiGet` 上加 `unwrapEnvelope: true`。
2. 修改 `GET /data/status` 字段时：同步 `DataStatusResponse` 与 `/data` 页。
3. 部署后若 DuckDB 报错「同一文件不同配置」：全进程统一 `read_only=False` 或统一只读，并重启 Gateway（见 `SystemDataOverview` 内提示）。
4. **龙虎榜**：若历史写入过 `lhb_date` 为空的行，下钻会出现同代码重复、日期 `NaT`。可执行 `python scripts/cleanup_longhubang_invalid.py` 清理；新采集已在 `longhubang` 采集器与 `ashare_longhubang` 源中 `dropna(subset=[..., "lhb_date"])`。
