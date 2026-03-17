"""涨停行为识别：早盘快速封板偏好。当前表无 first_limit_time，用连板数作为确认度代理。"""

from __future__ import annotations

import pandas as pd


class LimitUpBehaviorDetector:
    def __init__(self, conn=None):
        self._conn = conn

    def _get_conn(self):
        if self._conn is not None:
            return self._conn
        try:
            from data_pipeline.storage.duckdb_manager import get_conn, ensure_tables

            c = get_conn(read_only=False)
            ensure_tables(c)
            return c
        except Exception:
            import os
            import duckdb

            # Go up 5 levels: hotmoney_sniper → market_scanner → market-scanner → src → newhigh
            root = os.path.dirname(
                os.path.dirname(
                    os.path.dirname(
                        os.path.dirname(
                            os.path.dirname(os.path.abspath(__file__))
                        )
                    )
                )
            )
            path = (
                os.environ.get("QUANT_SYSTEM_DUCKDB_PATH", "")
                or os.environ.get("NEWHIGH_MARKET_DUCKDB_PATH", "")
                or os.path.join(root, "data", "quant_system.duckdb")
            )
            os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
            return duckdb.connect(path)

    def detect_limit_behavior(self) -> pd.DataFrame:
        """
        返回涨停池中标的；连板数越高越视为「确认」行为。
        若表有 first_limit_time 可筛 early_limit；当前用 limit_up_times 作为强度。
        """
        conn = self._get_conn()
        try:
            df = conn.execute("""
                SELECT code, name, limit_up_times, change_pct, snapshot_time
                FROM a_stock_limitup
            """).fetchdf()
        except Exception:
            return pd.DataFrame(columns=["code", "name", "limit_up_times"])
        if df is None or df.empty:
            return pd.DataFrame(columns=["code", "name", "limit_up_times"])
        df["limit_up_times"] = df["limit_up_times"].fillna(1).astype(int)
        return df
