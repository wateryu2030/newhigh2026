#!/usr/bin/env python3
"""
初始化 newhigh 本地 DuckDB 扩展表，用于持续训练与实体化交易。
在 copy_astock_duckdb_to_newhigh.py 之后执行；不修改 daily_bars/stocks/news_items。

新增表：
- features_daily：日线特征（RSI/MACD/ATR 等），供策略与回测使用
- backtest_runs：回测结果落库，供 Alpha 评分与实盘前验证
"""
from __future__ import annotations

import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DEFAULT_NEWHIGH_DUCKDB_PATH = os.path.join(ROOT, "data", "quant.duckdb")


def _duckdb_path() -> str:
    return os.environ.get("NEWHIGH_DUCKDB_PATH", "").strip() or DEFAULT_NEWHIGH_DUCKDB_PATH


def main() -> int:
    path = _duckdb_path()
    if not path or not os.path.isfile(path):
        print(f"DuckDB not found: {path}. Run copy_astock_duckdb_to_newhigh.py first.", file=sys.stderr)
        return 1
    try:
        import duckdb
    except ImportError:
        print("Need duckdb: pip install duckdb", file=sys.stderr)
        return 1

    conn = duckdb.connect(path)
    # 日线特征表：按标的+日期存储，供策略/回测读取
    conn.execute("""
        CREATE TABLE IF NOT EXISTS features_daily (
            symbol VARCHAR NOT NULL,
            trade_date DATE NOT NULL,
            open DOUBLE,
            high DOUBLE,
            low DOUBLE,
            close DOUBLE,
            volume DOUBLE,
            rsi DOUBLE,
            macd DOUBLE,
            macd_signal DOUBLE,
            macd_hist DOUBLE,
            vwap DOUBLE,
            atr DOUBLE,
            momentum DOUBLE,
            volatility DOUBLE,
            PRIMARY KEY (symbol, trade_date)
        )
    """)
    # 回测结果表：供 Alpha 评分与进化、未来实盘前验证
    conn.execute("""
        CREATE TABLE IF NOT EXISTS backtest_runs (
            run_id VARCHAR PRIMARY KEY,
            strategy_id VARCHAR NOT NULL,
            symbol VARCHAR NOT NULL,
            start_date DATE,
            end_date DATE,
            sharpe_ratio DOUBLE,
            return_pct DOUBLE,
            max_drawdown_pct DOUBLE,
            win_rate_pct DOUBLE,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    conn.close()
    print(f"Extensions created: features_daily, backtest_runs @ {path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
