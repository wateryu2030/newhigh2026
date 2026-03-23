# 市场扫描器 (Market Scanner)

读 data-pipeline 的 market.duckdb（a_stock_limitup、a_stock_fundflow、a_stock_realtime），写 **market_signals** 表。

## 扫描器

| 模块 | signal_type | 数据源 |
|------|-------------|--------|
| limit_up_scanner | limitup | a_stock_limitup |
| fund_flow_scanner | fundflow | a_stock_fundflow |
| volume_spike_scanner | volume | a_stock_realtime（按成交额） |
| trend_scanner | trend | a_stock_realtime（按涨跌幅） |
| sector_rotation_scanner | sector | 占位 |

## 使用

依赖：`data-pipeline`（同库）、DuckDB。先跑 pipeline 写入 a_stock_*，再跑扫描。

```bash
python -c "from market_scanner import run_limit_up_scanner, run_fund_flow_scanner; run_limit_up_scanner(); run_fund_flow_scanner()"
```

或通过 `scripts/run_terminal_loop.py` 一次性执行扫描 + AI + 策略聚合。
