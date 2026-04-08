"""写入 market_signals 表，使用统一 lib 模块。"""

from __future__ import annotations

from lib.database import get_connection, ensure_core_tables


def _get_conn():
    """兼容各 scanner 的 `from ._storage import _get_conn`；与 write_signals 共用统一连接。"""
    return get_connection(read_only=False)


def write_signals(signals: list[tuple[str, str, float]], signal_type: str) -> int:
    """写入 market_signals (code, signal_type, score)，先删该 type 再插入。"""
    conn = get_connection(read_only=False)
    if not conn:
        return 0

    ensure_core_tables(conn)
    conn.execute("DELETE FROM market_signals WHERE signal_type = ?", [signal_type])
    for code, st, score in signals:
        conn.execute(
            "INSERT INTO market_signals (code, signal_type, score) VALUES (?, ?, ?)",
            [code, st, float(score)],
        )
    n = conn.execute(
        "SELECT COUNT(*) FROM market_signals WHERE signal_type = ?", [signal_type]
    ).fetchone()[0]
    conn.close()
    return int(n)
