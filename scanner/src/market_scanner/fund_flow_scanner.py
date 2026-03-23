"""资金流扫描：从 a_stock_fundflow 生成 fundflow 类 market_signals。"""

from __future__ import annotations


def run_fund_flow_scanner() -> int:
    from ._storage import _get_conn, write_signals

    conn = _get_conn()
    try:
        df = conn.execute(
            "SELECT code, name, main_net_inflow FROM a_stock_fundflow ORDER BY main_net_inflow DESC NULLS LAST LIMIT 200"
        ).fetchdf()
    except Exception:
        df = None
    conn.close()
    if df is None or df.empty:
        return write_signals([], "fundflow")
    signals = []
    for _, row in df.iterrows():
        code = str(row.get("code", ""))
        inflow = float(row.get("main_net_inflow") or 0)
        score = min(100.0, max(0.0, 50.0 + inflow / 1e8))
        signals.append((code, "fundflow", score))
    return write_signals(signals, "fundflow")
