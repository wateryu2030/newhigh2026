"""趋势扫描：从 a_stock_realtime 按涨跌幅生成 trend 类 market_signals。"""

from __future__ import annotations


def run_trend_scanner() -> int:
    from ._storage import _get_conn, write_signals

    conn = _get_conn()
    try:
        df = conn.execute(
            "SELECT code, name, change_pct FROM a_stock_realtime WHERE change_pct > 0 ORDER BY change_pct DESC NULLS LAST LIMIT 100"
        ).fetchdf()
    except Exception:
        df = None
    conn.close()
    if df is None or df.empty:
        return write_signals([], "trend")
    signals = []
    for _, row in df.iterrows():
        code = str(row.get("code", ""))
        pct = float(row.get("change_pct") or 0)
        score = min(100.0, 50.0 + pct)
        signals.append((code, "trend", score))
    return write_signals(signals, "trend")
