# backtest-engine

基于 vectorbt 向量化回测，输出 Sharpe、Sortino、MaxDrawdown、WinRate、ProfitFactor 等 JSON 结果。

## 从数据库跑回测（资金曲线 + 风险指标）

- **run_backtest_from_db(symbol, start_date, end_date, signal_source='trade_signals', init_cash=10000, fees=0.001)**  
  从 quant_system.duckdb 读 a_stock_daily 日 K 与 trade_signals/market_signals 信号，跑回测，返回：
  - **equity_curve**: `[{"date": "YYYY-MM-DD", "value": float}, ...]`
  - **sharpe_ratio**, **max_drawdown**, **total_return**, **win_rate_pct**, **profit_factor**, **total_profit**, **trade_count**
  - **error**: 异常时带错误信息
- 数据与信号通过 `data_loader.load_ohlcv_from_db`、`load_signals_from_db` 读取；需 `data_pipeline.storage.duckdb_manager` 可用。

## API

- **POST /api/backtest/run**（Gateway）  
  参数：symbol, start_date, end_date, signal_source, init_cash, fees。返回同上结构，供前端资金曲线图、策略市场调用。
