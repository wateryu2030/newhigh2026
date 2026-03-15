"""资金异动检测：成交额相对 5 日均值突然放大（volume_ratio > 2）。"""

from __future__ import annotations

import pandas as pd


class FundSpikeDetector:
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

            root = os.path.dirname(
                os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
            )
            path = (
                os.environ.get("QUANT_SYSTEM_DUCKDB_PATH", "")
                or os.environ.get("NEWHIGH_MARKET_DUCKDB_PATH", "")
                or os.path.join(root, "data", "quant_system.duckdb")
            )
            os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
            return duckdb.connect(path)

    def detect_spikes(self, volume_ratio_min: float = 2.0) -> pd.DataFrame:
        """成交额 > 前 5 日均值 * volume_ratio_min 的标的。"""
        conn = self._get_conn()
        try:
            df = conn.execute("""
                WITH base AS (
                    SELECT
                        code,
                        date,
                        amount,
                        AVG(amount) OVER (
                            PARTITION BY code
                            ORDER BY date
                            ROWS BETWEEN 5 PRECEDING AND 1 PRECEDING
                        ) AS avg_amount_5
                    FROM a_stock_daily
                    WHERE amount IS NOT NULL AND amount > 0
                )
                SELECT code, date, amount,
                       amount / NULLIF(avg_amount_5, 0) AS volume_ratio
                FROM base
                WHERE avg_amount_5 IS NOT NULL AND avg_amount_5 > 0
            """).fetchdf()
        except Exception:
            return pd.DataFrame(columns=["code", "date", "amount", "volume_ratio"])
        if df is None or df.empty:
            return pd.DataFrame(columns=["code", "date", "amount", "volume_ratio"])
        spikes = df[df["volume_ratio"] >= volume_ratio_min].copy()
        return spikes
