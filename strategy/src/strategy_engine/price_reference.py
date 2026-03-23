"""从统一 DuckDB 取最近价，用于填写 trade_signals 的 target_price / stop_loss（估算参考）。"""

from __future__ import annotations

import os
from typing import Optional, Tuple


def get_last_price(code: str) -> Optional[float]:
    """
    优先 a_stock_realtime.latest_price，否则 a_stock_daily 最近一日 close。
    """
    c = (code or "").strip()
    if not c:
        return None
    try:
        from data_pipeline.storage.duckdb_manager import get_conn, get_db_path

        path = get_db_path()
        if not path or not os.path.isfile(path):
            return None
        conn = get_conn(read_only=False)
        try:
            r = conn.execute(
                "SELECT latest_price FROM a_stock_realtime WHERE code = ? LIMIT 1",
                [c],
            ).fetchone()
            if r and r[0] is not None:
                px = float(r[0])
                if px > 0:
                    return px
            r2 = conn.execute(
                "SELECT close FROM a_stock_daily WHERE code = ? ORDER BY date DESC LIMIT 1",
                [c],
            ).fetchone()
            if r2 and r2[0] is not None:
                px = float(r2[0])
                if px > 0:
                    return px
        finally:
            try:
                conn.close()
            except Exception:
                pass
    except Exception:
        return None
    return None


def buy_target_stop_from_last(last: float) -> Tuple[float, float]:
    """BUY 参考：目标约 +5%，止损约 -4%（无行情时返回 0,0）。"""
    if last is None or last <= 0:
        return 0.0, 0.0
    return round(last * 1.05, 3), round(last * 0.96, 3)
