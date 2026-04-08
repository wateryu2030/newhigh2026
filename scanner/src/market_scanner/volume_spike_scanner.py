"""量能异动扫描：从 a_stock_realtime 按成交额排序生成 volume 类 market_signals。"""

from __future__ import annotations


def run_volume_spike_scanner() -> int:
    from ._storage import _get_conn, write_signals

    conn = _get_conn()
    if not conn:
        return write_signals([], "volume")
    try:
        df = conn.execute(
            "SELECT code, name, amount FROM a_stock_realtime ORDER BY amount DESC NULLS LAST LIMIT 100"
        ).fetchdf()
    except Exception:
        df = None
    finally:
        conn.close()
    if df is None or df.empty:
        return write_signals([], "volume")
    signals = []
    for i, (_, row) in enumerate(df.iterrows()):
        code = str(row.get("code", ""))
        score = max(0.0, 80.0 - i * 0.5)
        signals.append((code, "volume", score))
    return write_signals(signals, "volume")
