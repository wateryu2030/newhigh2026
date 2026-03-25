"""读写 quant_system.duckdb 的 AI 输出表，使用统一 lib 模块。"""

from __future__ import annotations

from lib.database import get_connection, ensure_core_tables  # pylint: disable=import-error


def _get_conn():
    """获取数据库连接（兼容旧代码）。"""
    conn = get_connection(read_only=False)
    if conn:
        ensure_core_tables(conn)
    return conn


def write_emotion_state(state: str, stage: str, limit_up_count: int, score: float) -> None:
    conn = get_connection(read_only=False)
    if not conn:
        return
    ensure_core_tables(conn)
    conn.execute(
        "INSERT INTO market_emotion (emotion_state, emotion_stage, limit_up_count, score) VALUES (?, ?, ?, ?)",
        [state, stage, limit_up_count, score],
    )
    conn.close()


def write_hotmoney_signals(signals: list[tuple[str, str, float]]) -> None:
    conn = get_connection(read_only=False)
    if not conn:
        return
    ensure_core_tables(conn)
    conn.execute("DELETE FROM hotmoney_signals")
    for code, seat_type, win_rate in signals:
        conn.execute(
            "INSERT INTO hotmoney_signals (code, seat_type, win_rate) VALUES (?, ?, ?)",
            [code, seat_type, float(win_rate)],
        )
    conn.close()


def write_sector_strength(rows: list[tuple[str, float, int]]) -> None:
    conn = get_connection(read_only=False)
    if not conn:
        return
    ensure_core_tables(conn)
    conn.execute("DELETE FROM sector_strength")
    for sector, strength, rank in rows:
        conn.execute(
            "INSERT INTO sector_strength (sector, strength, rank) VALUES (?, ?, ?)",
            [sector, float(strength), int(rank)],
        )
    conn.close()
