# data-engine

采集行情（Binance / Yahoo / **akshare A 股**），归一化 OHLCV，写入 ClickHouse（market_1m/5m/1h/1d），支持实时流。

- **Binance**：`fetch_klines`，加密货币 K 线。
- **Yahoo**：`fetch_klines_yahoo`，美股/指数等。
- **akshare**：`fetch_klines_akshare`（A 股日/周/月线）、`fetch_klines_akshare_minute`（分钟线），`run_pipeline_ashare(symbols, start_date, end_date)` 批量落库。
- **A 股本地 DuckDB（与 astock 独立）**：先运行 `python scripts/copy_astock_duckdb_to_newhigh.py` 将 astock 的 DuckDB 复制到 newhigh 的 `data/quant.duckdb`，之后本模块只读 **newhigh 本仓库** 的该文件。`fetch_klines_from_astock_duckdb`、`get_stocks_from_astock_duckdb`、`get_news_from_astock_duckdb`。
