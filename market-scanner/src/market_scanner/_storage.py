"""写入 market_signals 表，复用 data_pipeline 的 DuckDB。"""
from __future__ import annotations

import os
import sys

def _get_conn():
    # 与 data_pipeline 同库
    try:
        from data_pipeline.storage.duckdb_manager import get_conn as _c, ensure_tables
        conn = _c(read_only=False)
        ensure_tables(conn)
        return conn
    except ImportError:
        pass
    # 回退：按 newhigh 根路径算
    root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    path = os.environ.get("QUANT_SYSTEM_DUCKDB_PATH", "").strip() or os.environ.get("NEWHIGH_MARKET_DUCKDB_PATH", "").strip() or os.path.join(root, "data", "quant_system.duckdb")
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    import duckdb
    return duckdb.connect(path)


def write_signals(signals: list[tuple[str, str, float]], signal_type: str) -> int:
    """写入 market_signals (code, signal_type, score)，先删该 type 再插入。"""
    conn = _get_conn()
    conn.execute("DELETE FROM market_signals WHERE signal_type = ?", [signal_type])
    for code, st, score in signals:
        conn.execute(
            "INSERT INTO market_signals (code, signal_type, score) VALUES (?, ?, ?)",
            [code, st, float(score)],
        )
    n = conn.execute("SELECT COUNT(*) FROM market_signals WHERE signal_type = ?", [signal_type]).fetchone()[0]
    conn.close()
    return int(n)
