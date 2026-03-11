#!/usr/bin/env python3
"""
从 DuckDB daily_bars 计算日线特征（RSI/MACD/ATR 等）并写入 features_daily。
供 OpenClaw 持续训练与策略回测使用；进化循环中在数据补全后执行。

用法（仓库根目录，已激活 .venv）：
  python scripts/compute_features_to_duckdb.py
  python scripts/compute_features_to_duckdb.py --symbols 600519,000001 --limit 200
"""
from __future__ import annotations

import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
for d in ["data-engine/src", "core/src", "feature-engine/src"]:
    p = os.path.join(ROOT, d)
    if os.path.isdir(p) and p not in sys.path:
        sys.path.insert(0, p)


def _duckdb_path() -> str:
    from data_engine.connector_astock_duckdb import DEFAULT_NEWHIGH_DUCKDB_PATH
    return os.environ.get("NEWHIGH_DUCKDB_PATH", "").strip() or DEFAULT_NEWHIGH_DUCKDB_PATH


def _safe_float(v) -> float | None:
    """Convert to float for DuckDB; None for NaN/None."""
    if v is None:
        return None
    try:
        f = float(v)
        if f != f:  # NaN
            return None
        return f
    except (TypeError, ValueError):
        return None


def run(symbols: list[str] | None = None, limit_per_symbol: int = 500, max_symbols: int = 200) -> dict:
    """计算特征并写入 features_daily。返回 { written: int, symbols_processed: int, errors: int }。"""
    import duckdb
    from data_engine.connector_astock_duckdb import (
        _order_book_id_to_symbol,
        get_astock_duckdb_available,
        fetch_klines_from_astock_duckdb,
    )
    from feature_engine.pipeline import build_feature_matrix

    path = _duckdb_path()
    if not path or not os.path.isfile(path):
        return {"written": 0, "symbols_processed": 0, "errors": 1}

    # 使用单一只读连接完成所有读取，再单独开写连接写入，避免多连接锁冲突与读不到数据
    try:
        conn_read = duckdb.connect(path, read_only=True)
    except Exception as e:
        if os.environ.get("DEBUG_FEATURES") == "1":
            sys.stderr.write(f"[DEBUG] DuckDB open failed (e.g. locked by another process): {e}\n")
        return {"written": 0, "symbols_processed": 0, "errors": 1}

    symbol_list = symbols
    if not symbol_list:
        try:
            df = conn_read.execute(
                """
                SELECT order_book_id FROM daily_bars
                GROUP BY order_book_id HAVING COUNT(*) >= 30
                ORDER BY order_book_id
                LIMIT ?
                """,
                [max_symbols],
            ).fetchdf()
            if df is not None and not df.empty:
                symbol_list = [_order_book_id_to_symbol(ob) for ob in df["order_book_id"].astype(str).tolist()]
            if not symbol_list:
                df = conn_read.execute(
                    "SELECT DISTINCT order_book_id FROM daily_bars ORDER BY order_book_id LIMIT ?",
                    [max_symbols],
                ).fetchdf()
                if df is not None and not df.empty:
                    symbol_list = [_order_book_id_to_symbol(ob) for ob in df["order_book_id"].astype(str).tolist()]
        except Exception:
            pass
    if not symbol_list:
        try:
            conn_read.close()
        except Exception:
            pass
        return {"written": 0, "symbols_processed": 0, "errors": 0}

    errors = 0
    pending: list[tuple[str, "pd.DataFrame"]] = []
    for sym in symbol_list:
        try:
            bars = fetch_klines_from_astock_duckdb(
                sym, limit=limit_per_symbol, recent_first=True, conn=conn_read
            )
            if len(bars) < 30:
                continue
            df = build_feature_matrix(bars)
            if df is None or df.empty:
                continue
            sym_code = sym.split(".")[0] if "." in sym else sym
            pending.append((sym_code, df))
        except Exception:
            errors += 1

    if conn_read is not None:
        try:
            conn_read.close()
        except Exception:
            pass

    written = 0
    try:
        conn = duckdb.connect(path)
    except Exception:
        return {"written": written, "symbols_processed": len(symbol_list), "errors": errors + 1}
    try:
        for sym_code, df in pending:
            for _, row in df.iterrows():
                ts = row.get("timestamp")
                if ts is None or (hasattr(ts, "__bool__") and getattr(ts, "year", 1) == 1 and str(ts).startswith("NaT")):
                    continue
                if hasattr(ts, "strftime"):
                    trade_date = ts.strftime("%Y-%m-%d")
                else:
                    trade_date = str(ts)[:10]
                if trade_date.startswith("NaT") or len(trade_date) < 10:
                    continue
                try:
                    conn.execute(
                        """
                        INSERT INTO features_daily
                        (symbol, trade_date, open, high, low, close, volume, rsi, macd, macd_signal, macd_hist, vwap, atr, momentum, volatility)
                        VALUES (?, ?::DATE, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                        ON CONFLICT (symbol, trade_date) DO UPDATE SET
                        open=EXCLUDED.open, high=EXCLUDED.high, low=EXCLUDED.low, close=EXCLUDED.close, volume=EXCLUDED.volume,
                        rsi=EXCLUDED.rsi, macd=EXCLUDED.macd, macd_signal=EXCLUDED.macd_signal, macd_hist=EXCLUDED.macd_hist,
                        vwap=EXCLUDED.vwap, atr=EXCLUDED.atr, momentum=EXCLUDED.momentum, volatility=EXCLUDED.volatility
                        """,
                        [
                            sym_code,
                            trade_date,
                            _safe_float(row.get("open")),
                            _safe_float(row.get("high")),
                            _safe_float(row.get("low")),
                            _safe_float(row.get("close")),
                            _safe_float(row.get("volume")),
                            _safe_float(row.get("rsi")),
                            _safe_float(row.get("macd")),
                            _safe_float(row.get("macd_signal")),
                            _safe_float(row.get("macd_hist")),
                            _safe_float(row.get("vwap")),
                            _safe_float(row.get("atr")),
                            _safe_float(row.get("momentum")),
                            _safe_float(row.get("volatility")),
                        ],
                    )
                    written += 1
                except Exception:
                    errors += 1
    finally:
        conn.close()
    return {"written": written, "symbols_processed": len(symbol_list), "errors": errors}


def main() -> int:
    import argparse
    parser = argparse.ArgumentParser(description="Compute features from daily_bars -> features_daily")
    parser.add_argument("--symbols", type=str, default=None, help="Comma-separated symbols (default: from DuckDB)")
    parser.add_argument("--limit", type=int, default=500, help="Bars per symbol")
    parser.add_argument("--max-symbols", type=int, default=200, help="Max symbols when loading from DB")
    args = parser.parse_args()
    symbols = args.symbols.split(",") if args.symbols else None
    out = run(symbols=symbols, limit_per_symbol=args.limit, max_symbols=args.max_symbols)
    print("Written:", out["written"], "Symbols:", out["symbols_processed"], "Errors:", out["errors"])
    if out["errors"] > 0 and out["symbols_processed"] == 0:
        sys.stderr.write("Hint: if DuckDB is locked, close other processes using data/quant.duckdb and retry.\n")
    return 0 if out["errors"] == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
