# 现有代码检查报告：数据拉取与数据分析基础

从 **数据拉取（含最新 A 股）** 与 **数据分析** 等层面梳理现有基础与缺口。

---

## 一、数据拉取层 (data-engine)

### 1.1 已有数据源

| 数据源 | 模块/文件 | 说明 |
|--------|-----------|------|
| **Binance** | `connector_binance.py` | 加密货币 K 线，`fetch_klines(symbol, interval, limit)`，归一化为 `OHLCV`，支持 1m/5m/1h/1d |
| **Yahoo Finance** | `connector_yahoo.py` | 依赖 `yfinance`，`fetch_klines_yahoo(symbol, interval, limit, period/start/end)`，归一化为 `OHLCV` |

- **存储**：`clickhouse_storage.py`（建表、插入、查询）、`data_pipeline.py`（Binance → ClickHouse 批量/单标的）。
- **实时流**：`realtime_stream.py`（Binance WebSocket 拉流，回调 `on_bar`）。

### 1.2 A 股（最新 A 股交易数据）现状

- **akshare 连接器（已实现）**：`connector_akshare.py`
  - **日线**：`fetch_klines_akshare(symbol, start_date, end_date, period="daily"|"weekly"|"monthly", adjust="qfq"|"hfq"|"")`，输出 `List[OHLCV]`，symbol 归一化为 `600519.SH` / `000001.SZ` / **830799.BSE（北交所）**。优先东方财富接口（支持沪深京/北交所）。
  - **北交所**：支持 4/8/9 开头或 8 位代码，`get_stock_list_akshare(include_bse=True)` 可拉取 A 股 + 北交所股票列表。
  - **分钟线**：`fetch_klines_akshare_minute(symbol, start_date, end_date, period="1"|"5"|"15"|"30"|"60")`。
  - **管道**：`run_pipeline_ashare(symbols, start_date, end_date, period, adjust)` 批量拉取并写入 ClickHouse。
- **数据完整性**：`scripts/ensure_ashare_data_completeness.py` 检测本地 DuckDB 缺失区间，从 akshare/北交所 等自动拉取并写入，保证分析数据完整；已接入 OpenClaw 进化循环（每轮进化前执行）。
- **前端展示（借鉴 astock）**：Dashboard 展示数据状态（标的数、日线数、日期范围）；新增「Data」页（数据状态与更新说明）；Market 页支持「行情 / 列表」双视图、K 线 Tooltip 展示 OHLC；News 页支持按股票代码筛选、情感汇总（条数、均值、正面占比）。API：`GET /api/data/status`、`GET /api/news` 返回 `sentiment`。
- **前端双语**：默认中文，可切换英文。`frontend/src/lib/i18n.ts` 维护 zh/en 文案，`LangContext` + `useLang()` 提供 `t('key')`；导航栏有语言切换按钮。详见 `docs/FRONTEND_I18N_AND_OPENCLAW.md`；遇问题参照该文档与 OpenClaw 持续修改完善。
- **配置**：`OPENCLAW_DATA_PIPELINE.yaml` 的 `sources.market` 已包含 `akshare`，任务 `collect_ashare_data` 对应 `run_pipeline_ashare`。
- **A 股本地 DuckDB（与 astock 独立）**：数据来自「从 astock 复制」到 newhigh 本地的 `data/quant.duckdb`，运行 `python scripts/copy_astock_duckdb_to_newhigh.py` 即可把 astock 的 daily_bars、stocks、news_items 拷入 newhigh。`connector_astock_duckdb.py` 只读 **newhigh 本仓库** 的 `data/quant.duckdb`（或 `NEWHIGH_DUCKDB_PATH`），不读 astock 目录。两套目录、两套操作完全独立。
- **Yahoo**：仍可用 `fetch_klines_yahoo("600519.SS", "1d")` 作为补充；akshare 为 A 股网络拉取。

**结论**：  
- **有基础**：通用 OHLCV 拉取（Binance + Yahoo + **akshare**）、存储、管道、实时流均已存在。  
- **A 股**：已通过 **akshare** 实现专用拉取与 pipeline 接入；可按需配置 A 股标的列表与定时任务。

---

## 二、数据分析层

### 2.1 特征计算 (feature-engine)

| 能力 | 文件/函数 | 说明 |
|------|-----------|------|
| RSI | `rsi.py` | `rsi(ohlcv_list, period=14)`、`rsi_from_prices(closes, period)` |
| MACD | `macd.py` | `macd(ohlcv_list, fast/slow/signal)`、`macd_from_prices` |
| VWAP | `vwap.py` | `vwap(ohlcv_list)`、`vwap_from_ohlc` |
| ATR | `atr.py` | `atr(ohlcv_list, period=14)`、`atr_from_prices` |
| Momentum | `pipeline.py` | `momentum_returns(closes, period=10)` |
| Volatility | `pipeline.py` | `volatility_returns(closes, period=20)` |
| 特征矩阵 | `pipeline.py` | `build_feature_matrix(ohlcv_list, ...)` → DataFrame（timestamp, open/high/low/close/volume, rsi, macd, macd_signal, macd_hist, vwap, atr, momentum, volatility） |

- 输入均为 `List[OHLCV]` 或价格序列，**与标的类型无关**；  
- 一旦有 A 股 OHLCV（来自 Yahoo 或未来 A 股 connector），**无需改代码** 即可做 A 股特征分析。

### 2.2 回测 (backtest-engine)

- `runner.py`：`run_backtest(close, entries, exits, ...)`、`run_backtest_from_ohlcv(ohlcv_list, entries, exits, ...)`，基于 vectorbt。
- `metrics.py`：`compute_metrics(portfolio)`（Sharpe、Sortino、最大回撤、胜率等）。
- 输入为价格/信号或 `List[OHLCV]`，**与市场/标的无关**，A 股数据进来即可回测。

### 2.3 策略 (strategy-engine)

- 趋势、均值回归、突破等信号基于 OHLCV/特征，**标的无关**。
- 与 feature-engine、backtest-engine 一致：**有 A 股 OHLCV 即有分析基础**。

### 2.4 组合与风控 (portfolio-engine, risk-engine)

- 权重、回撤、敞口等计算基于头寸与净值，**不依赖数据源类型**。  
- 数据层只需提供正确的持仓/成交与行情（含 A 股），即可复用现有逻辑。

---

## 三、整体结论表

| 层面 | 是否有基础 | 说明 |
|------|------------|------|
| 数据拉取（通用） | ✅ 有 | Binance + Yahoo，OHLCV 归一化，ClickHouse，pipeline，实时流 |
| 数据拉取（**最新 A 股**） | ✅ 有 | 已通过 **akshare** 实现：`fetch_klines_akshare` / `fetch_klines_akshare_minute`、`run_pipeline_ashare`，并接入 OPENCLAW_DATA_PIPELINE |
| 特征/指标分析 | ✅ 有 | RSI、MACD、VWAP、ATR、动量、波动率、`build_feature_matrix` |
| 回测与指标 | ✅ 有 | vectorbt 回测、Sharpe/Sortino/回撤/胜率等 |
| 策略信号 | ✅ 有 | 趋势/均值回归/突破等，标的无关 |
| 组合与风控 | ✅ 有 | 权重、回撤、敞口等，标的无关 |

---

## 四、A 股已接入后的可选下一步

1. **调度与标的列表**：在 scheduler 或 cron 中定时调用 `run_pipeline_ashare(symbols=["600519", "000001", ...], start_date=..., end_date=...)`，标的列表可配置到配置文件或数据库。

2. **Gateway 与前端**：`/api/market/klines` 已支持任意 symbol；前端 Market 页可增加 A 股标的选择（如 `600519.SH`）；可选增加“A 股列表”接口（可调用 akshare 的股票列表接口）。

3. **分钟线**：需要分钟级 A 股时，使用 `fetch_klines_akshare_minute(symbol, start_date, end_date, period="1"|"5"|...)` 并写入 ClickHouse，与日线共用 `insert_ohlcv`。

---

**报告结论**：  
- **数据分析**（特征、回测、策略、组合、风控）已有完整基础，且与标的类型解耦。  
- **数据拉取** 有通用基础；**最新 A 股交易数据** 尚缺专用连接器与 pipeline 配置，建议按上面四步补齐并优先接入一种 A 股数据源（如 akshare）。
