"""读写 quant_system.duckdb 的 AI 输出表。"""

from __future__ import annotations

import os


def _get_conn():
    try:
        from data_pipeline.storage.duckdb_manager import get_conn as _c, ensure_tables

        conn = _c(read_only=False)
        ensure_tables(conn)
        return conn
    except ImportError:
        pass
    root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    path = (
        os.environ.get("QUANT_SYSTEM_DUCKDB_PATH", "").strip()
        or os.environ.get("NEWHIGH_MARKET_DUCKDB_PATH", "").strip()
        or os.path.join(root, "data", "quant_system.duckdb")
    )
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    import duckdb

    return duckdb.connect(path)


def write_emotion_state(state: str, stage: str, limit_up_count: int, score: float) -> None:
    conn = _get_conn()
    conn.execute(
        "INSERT INTO market_emotion_state (state, stage, limit_up_count, score) VALUES (?, ?, ?, ?)",
        [state, stage, limit_up_count, score],
    )
    conn.close()


def write_hotmoney_signals(signals: list[tuple[str, str, float]]) -> None:
    conn = _get_conn()
    conn.execute("DELETE FROM hotmoney_signals")
    for code, seat_type, win_rate in signals:
        conn.execute(
            "INSERT INTO hotmoney_signals (code, seat_type, win_rate) VALUES (?, ?, ?)",
            [code, seat_type, float(win_rate)],
        )
    conn.close()


def write_sector_strength(rows: list[tuple[str, float, int]]) -> None:
    conn = _get_conn()
    conn.execute("DELETE FROM sector_strength")
    for sector, strength, rank in rows:
        conn.execute(
            "INSERT INTO sector_strength (sector, strength, rank) VALUES (?, ?, ?)",
            [sector, float(strength), int(rank)],
        )
    conn.close()
