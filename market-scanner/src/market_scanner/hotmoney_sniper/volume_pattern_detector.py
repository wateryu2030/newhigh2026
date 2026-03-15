"""量能结构识别：缩量→放量，当日量 / vol_ma5 > 1.8。"""

from __future__ import annotations

import pandas as pd


class VolumePatternDetector:
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

    def detect_pattern(self, ratio_min: float = 1.8) -> pd.DataFrame:
        """按 code 取最近日线，计算 vol_ma5、ratio = volume/vol_ma5，筛选 ratio > ratio_min。"""
        conn = self._get_conn()
        try:
            df = conn.execute("""
                WITH daily AS (
                    SELECT code, date, volume,
                           AVG(volume) OVER (
                               PARTITION BY code
                               ORDER BY date
                               ROWS BETWEEN 5 PRECEDING AND 1 PRECEDING
                           ) AS vol_ma5
                    FROM a_stock_daily
                    WHERE volume IS NOT NULL AND volume > 0
                )
                SELECT code, date, volume, vol_ma5,
                       volume / NULLIF(vol_ma5, 0) AS ratio
                FROM daily
                WHERE vol_ma5 IS NOT NULL AND vol_ma5 > 0
            """).fetchdf()
        except Exception:
            return pd.DataFrame(columns=["code", "date", "volume", "vol_ma5", "ratio"])
        if df is None or df.empty:
            return pd.DataFrame(columns=["code", "date", "volume", "vol_ma5", "ratio"])
        pattern = df[df["ratio"] >= ratio_min].copy()
        return pattern
