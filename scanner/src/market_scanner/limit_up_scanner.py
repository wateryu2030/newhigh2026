"""涨停扫描：从 a_stock_limitup 生成 limitup 类 market_signals。"""

from __future__ import annotations


def run_limit_up_scanner() -> int:
    from ._storage import _get_conn, write_signals

    conn = _get_conn()
    try:
        df = conn.execute(
            "SELECT code, name, limit_up_times FROM a_stock_limitup ORDER BY limit_up_times DESC NULLS LAST LIMIT 200"
        ).fetchdf()
    except Exception:
        df = None
    conn.close()
    if df is None or df.empty:
        return write_signals([], "limitup")
    signals = []
    for _, row in df.iterrows():
        code = str(row.get("code", ""))
        times = int(row.get("limit_up_times") or 0)
        score = min(100.0, 50.0 + times * 10.0)
        signals.append((code, "limitup", score))
    return write_signals(signals, "limitup")
